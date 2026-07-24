"""Save/load DQN checkpoints with epsilon (resume without exploration shock)."""

from __future__ import annotations



import json

import os

from dataclasses import dataclass

from pathlib import Path

from typing import Any



import torch

from torch import optim



from flowgrid.rl.dqn_agent import DQNAgent

from flowgrid.rl.policy_config import DEFAULT_TRAINING_LOG_PATH, FineTuneParams



CHECKPOINT_FORMAT = 1

POLICY_STATE_KEY = "policy_state"


def torch_load_checkpoint(path: str | os.PathLike, map_location: str | torch.device = "cpu") -> Any:
    try:
        return torch.load(path, map_location=map_location, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=map_location)
    except Exception:
        return torch.load(path, map_location=map_location, weights_only=False)


def policy_state_dict_cpu(agent: DQNAgent) -> dict[str, torch.Tensor]:
    return {key: tensor.detach().cpu() for key, tensor in agent.policy_net.state_dict().items()}


def read_checkpoint_training_episodes(policy_path: str | os.PathLike) -> int | None:
    from flowgrid.maps.policy_paths import resolve_policy_path

    resolved = resolve_policy_path(policy_path)
    if resolved is None:
        candidate = Path(policy_path)
        if not candidate.is_file():
            return None
        resolved = candidate
    try:
        raw = torch_load_checkpoint(resolved, map_location="cpu")
        meta = _checkpoint_meta_from_raw(raw)
        episodes = meta.get("episodes_done")
        if episodes is not None:
            return int(episodes)
    except Exception:
        return None
    return None


@dataclass

class CheckpointLoadResult:

    loaded: bool

    epsilon: float | None = None

    episode: int | None = None

    episodes_done: int | None = None

    steps_done: int | None = None

    legacy_weights_only: bool = False





def _checkpoint_meta_from_raw(loaded: Any) -> dict[str, Any]:

    if not isinstance(loaded, dict):

        return {}

    meta: dict[str, Any] = {}

    if loaded.get("epsilon") is not None:

        meta["epsilon"] = float(loaded["epsilon"])

    episodes_done = loaded.get("episodes_done")

    if episodes_done is None:

        episodes_done = loaded.get("episode")

    if episodes_done is not None:

        meta["episodes_done"] = int(episodes_done)

    if loaded.get("steps_done") is not None:

        meta["steps_done"] = int(loaded["steps_done"])

    if loaded.get("epsilon_decay") is not None:

        meta["epsilon_decay"] = float(loaded["epsilon_decay"])

    if loaded.get("phase_episodes_done") is not None:

        meta["phase_episodes_done"] = dict(loaded["phase_episodes_done"])

    return meta





def _unwrap_state_dict(loaded: Any) -> tuple[Any, float | None, int | None]:

    """Return (state_dict, epsilon, episode) from a .pth file payload."""

    if not isinstance(loaded, dict):

        return loaded, None, None

    if POLICY_STATE_KEY in loaded and isinstance(loaded[POLICY_STATE_KEY], dict):

        eps = loaded.get("epsilon")

        ep = loaded.get("episodes_done")

        if ep is None:

            ep = loaded.get("episode")

        return (

            loaded[POLICY_STATE_KEY],

            float(eps) if eps is not None else None,

            int(ep) if ep is not None else None,

        )

    if loaded.get("format") == CHECKPOINT_FORMAT and POLICY_STATE_KEY in loaded:

        eps = loaded.get("epsilon")

        ep = loaded.get("episodes_done")

        if ep is None:

            ep = loaded.get("episode")

        return (

            loaded[POLICY_STATE_KEY],

            float(eps) if eps is not None else None,

            int(ep) if ep is not None else None,

        )

    if any(str(k).startswith("net.") for k in loaded.keys()):

        return loaded, None, None

    return loaded, None, None





def read_last_epsilon_from_log(log_path: str | os.PathLike | None = None) -> float | None:

    path = DEFAULT_TRAINING_LOG_PATH if log_path is None else Path(log_path)

    if not path.is_file():

        return None

    last_eps: float | None = None

    try:

        with path.open(encoding="utf-8") as f:

            for line in f:

                line = line.strip()

                if not line:

                    continue

                rec = json.loads(line)

                if rec.get("event") == "episode" and rec.get("epsilon") is not None:

                    last_eps = float(rec["epsilon"])

    except (OSError, json.JSONDecodeError, TypeError, ValueError):

        return None

    return last_eps





def save_agent_checkpoint(

    agent: DQNAgent,

    policy_path: str,

    *,

    episode: int | None = None,

) -> None:

    os.makedirs(os.path.dirname(policy_path) or ".", exist_ok=True)

    meta = agent.export_checkpoint_meta()

    if episode is not None:

        meta["episodes_done"] = int(episode)

    state = policy_state_dict_cpu(agent)
    in_dim = int(state["net.0.weight"].shape[1])
    out_dim = int(state["net.4.weight"].shape[0])
    payload: dict[str, Any] = {

        "format": CHECKPOINT_FORMAT,

        POLICY_STATE_KEY: state,

        "input_dim": in_dim,

        "output_dim": out_dim,

        "epsilon": meta["epsilon"],

        "episodes_done": meta["episodes_done"],

        "steps_done": meta["steps_done"],

        "epsilon_decay": meta["epsilon_decay"],

        "phase_episodes_done": meta.get("phase_episodes_done"),

        "episode": meta["episodes_done"],

    }

    torch.save(payload, policy_path)





def apply_resume_hyperparams(

    agent: DQNAgent,

    *,

    fine_tune: FineTuneParams | None,

    checkpoint_epsilon: float | None,

    log_epsilon: float | None = None,

    checkpoint_meta: dict[str, Any] | None = None,

) -> float:

    meta = dict(checkpoint_meta or {})

    ft = fine_tune

    saved = checkpoint_epsilon if checkpoint_epsilon is not None else log_epsilon



    if ft is None or not ft.apply_on_resume:

        if checkpoint_epsilon is not None:

            agent.epsilon = max(agent.epsilon_end, float(checkpoint_epsilon))

        elif log_epsilon is not None:

            agent.epsilon = max(agent.epsilon_end, float(log_epsilon))

        else:

            agent.epsilon = max(agent.epsilon_end, agent.epsilon * 0.5)

    else:

        agent.optimizer = optim.Adam(agent.policy_net.parameters(), lr=float(ft.learning_rate))

        if ft.preserve_epsilon and saved is not None:

            agent.epsilon = max(

                agent.epsilon_end,

                min(1.0, float(saved) + float(ft.epsilon_resume_bump)),

            )

        else:

            agent.epsilon = max(agent.epsilon_end, float(ft.epsilon_start))



    if meta.get("epsilon_decay") is not None:

        agent.epsilon_decay = float(meta["epsilon_decay"])

    elif ft is not None and ft.apply_on_resume:

        agent.epsilon_decay = float(ft.epsilon_decay)



    progress = {
        k: meta[k]
        for k in ("episodes_done", "steps_done", "phase_episodes_done")
        if k in meta
    }

    if progress:

        agent.import_checkpoint_meta(progress)



    return agent.epsilon





def load_policy_weights_for_eval(agent: DQNAgent, policy_path: str) -> bool:

    """Load policy weights only; set epsilon=0 for Compare / eval."""

    if not policy_path or not os.path.isfile(policy_path):

        return False

    try:

        raw = torch_load_checkpoint(policy_path, map_location="cpu")

        state_dict, _, _ = _unwrap_state_dict(raw)

        agent.policy_net.load_state_dict(state_dict)

        agent.target_net.load_state_dict(state_dict)

        agent.policy_net.eval()

        agent.epsilon = 0.0

        return True

    except Exception:

        return False





def load_agent_checkpoint(

    agent: DQNAgent,

    policy_path: str,

    *,

    fine_tune: FineTuneParams | None = None,

    training_log_path: str | os.PathLike | None = None,

) -> CheckpointLoadResult:

    if not policy_path or not os.path.isfile(policy_path):

        return CheckpointLoadResult(loaded=False)

    try:

        raw = torch_load_checkpoint(policy_path, map_location="cpu")

        state_dict, ckpt_eps, ckpt_ep = _unwrap_state_dict(raw)

        agent.policy_net.load_state_dict(state_dict)

        agent.target_net.load_state_dict(state_dict)

        legacy = ckpt_eps is None and isinstance(raw, dict) and POLICY_STATE_KEY not in raw

        log_eps = read_last_epsilon_from_log(training_log_path) if legacy else None

        ckpt_meta = _checkpoint_meta_from_raw(raw)

        if "episodes_done" not in ckpt_meta and ckpt_ep is not None:

            ckpt_meta["episodes_done"] = ckpt_ep

        eps = apply_resume_hyperparams(

            agent,

            fine_tune=fine_tune,

            checkpoint_epsilon=ckpt_eps,

            log_epsilon=log_eps,

            checkpoint_meta=ckpt_meta,

        )

        episodes_done = ckpt_meta.get("episodes_done")

        steps_done = ckpt_meta.get("steps_done")

        return CheckpointLoadResult(

            loaded=True,

            epsilon=eps,

            episode=int(episodes_done) if episodes_done is not None else ckpt_ep,

            episodes_done=int(episodes_done) if episodes_done is not None else None,

            steps_done=int(steps_done) if steps_done is not None else None,

            legacy_weights_only=legacy,

        )

    except Exception:

        return CheckpointLoadResult(loaded=False)

