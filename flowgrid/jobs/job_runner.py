"""Background jobs for training and evaluation from the GUI."""
import contextlib
import os
import random
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

from flowgrid.eval.compare_metrics import (
    save_compare_summary_charts,
    save_emergency_comparison_charts,
    save_transit_comparison_charts,
)
from flowgrid.eval.evaluate import evaluate_compare_pair
from flowgrid.core.episode_limits import EpisodeLimits
from flowgrid.core.sumo_env import SumoEnv
from flowgrid.maps.map_builder import DEFAULT_FLOWS
from flowgrid.training.busy_snapshot import (
    busy_snapshot_path,
    ensure_busy_training_snapshot,
    reset_from_busy_snapshot,
)
from flowgrid.training.traffic_curriculum import (
    ensure_hard_warmup_routes,
    sample_traffic_episode,
)
from flowgrid.reports.comparison_history import append_comparison_record
from flowgrid.reports.curriculum import (
    CURRICULUM_LOG_PATH,
    CurriculumConfig,
    analyze_compare_result,
    log_curriculum_cycle,
)
from flowgrid.rl.dqn_agent import DQNAgent
from flowgrid.rl.policy_checkpoint import quarantine_incompatible
from flowgrid.rl.policy_config import PolicyConfig
from flowgrid.rl.episode_transparency import (
    append_episode_transparency_report,
    format_episode_transparency_report,
)
from flowgrid.rl.training_log import log_episode, log_training_session_start, write_objectives_text
from flowgrid.maps.policy_paths import (
    canonical_policy_path,
    policy_checkpoint_exists,
    promote_latest_checkpoint_to_canonical,
    resolve_policy_path,
)
from flowgrid.paths import DQN_TRAINING_LOG_PATH

from flowgrid.rl.policy_checkpoint_io import load_agent_checkpoint, save_agent_checkpoint
from flowgrid.rl.compare_guard import (
    best_policy_path,
    is_catastrophic_compare,
    is_valid_improvement,
    read_best_dqn_wait_all,
    restore_best_policy,
    save_best_policy,
)


@contextlib.contextmanager
def _silence_stdio():
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        old_out, old_err = sys.stdout, sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
        finally:
            sys.stdout = old_out
            sys.stderr = old_err


def _save_policy(agent: DQNAgent, policy_path: str, *, episode: int | None = None) -> None:
    save_agent_checkpoint(agent, policy_path, episode=episode)


def _load_policy_if_exists(
    agent: DQNAgent,
    policy_path: str,
    *,
    fine_tune: Any | None = None,
) -> bool:
    result = load_agent_checkpoint(agent, policy_path, fine_tune=fine_tune)
    return result.loaded


def _numbered_checkpoint_path(policy_path: str, episode: int) -> str:
    root, ext = os.path.splitext(policy_path)
    ext = ext or ".pth"
    return f"{root}_ep{episode:03d}{ext}"


def _maybe_checkpoint(
    agent: DQNAgent,
    policy_path: str,
    episode_1based: int,
    checkpoint_every: int,
) -> int | None:
    """Save policy when episode_1based is a checkpoint boundary. Returns episode saved or None."""
    every = max(1, int(checkpoint_every))
    if episode_1based % every != 0:
        return None
    _save_policy(agent, policy_path, episode=episode_1based)
    if every > 1:
        _save_policy(agent, _numbered_checkpoint_path(policy_path, episode_1based), episode=episode_1based)
    return episode_1based


@dataclass
class Job:
    id: str
    kind: str
    status: str = "queued"
    progress: float = 0.0
    message: str = ""
    result: dict = field(default_factory=dict)
    error: str | None = None


class JobRunner:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._cancel_jobs: set[str] = set()
        self._live_state: dict = {}
        self._live_lock = threading.Lock()

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def request_cancel(self, job_id: str) -> bool:
        with self._lock:
            if job_id not in self._jobs:
                return False
            self._cancel_jobs.add(job_id)
            return True

    def _is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._cancel_jobs

    def _clear_cancel(self, job_id: str) -> None:
        with self._lock:
            self._cancel_jobs.discard(job_id)

    def list_jobs(self) -> list[Job]:
        with self._lock:
            return list(self._jobs.values())

    def get_live_state(self) -> dict:
        with self._live_lock:
            return dict(self._live_state)

    def _set_live(self, snapshot: dict):
        with self._live_lock:
            self._live_state = snapshot

    def start(self, kind: str, fn: Callable[[Job], None]) -> str:
        job_id = str(uuid.uuid4())[:8]
        job = Job(id=job_id, kind=kind)
        with self._lock:
            self._jobs[job_id] = job

        def run():
            job.status = "running"
            try:
                fn(job)
                if job.status == "running":
                    job.status = "completed"
            except Exception as exc:
                job.status = "failed"
                job.error = str(exc)
                job.message = f"Failed: {exc}"
            finally:
                self._clear_cancel(job_id)

        threading.Thread(target=run, daemon=True).start()
        return job_id

    def start_train(
        self,
        sumocfg: str,
        episodes: int = 50,
        target_update_freq: int = 10,
        gui: bool = False,
        gui_delay: int = 80,
        policy_path: str = "dqn_policy.pth",
        learning_curve_path: str = "learning_curve.png",
        checkpoint_every: int = 1,
        min_green_seconds: float = 60,
        min_green_base_seconds: float = 5.0,
        switch_min_vehicles: int = 3,
        switch_min_wait_seconds: float = 25.0,
        max_green_seconds: float | None = None,
        map_name: str = "",
        map_id: str = "",
        resume: bool = False,
        train_seed: int | None = None,
        busy_fraction: float | None = None,
        quiet: bool = False,
        device: str | None = None,
        training_log_path: str | os.PathLike | None = None,
    ) -> str:
        checkpoint_every = max(1, int(checkpoint_every))

        def _train_progress_result(
            rewards_history: list[float],
            avg_wait_history: list[float],
            episodes_total: int,
            last_reward: float,
            epsilon: float,
            *,
            cancelled: bool = False,
            last_saved_episode: int | None = None,
        ) -> dict[str, Any]:
            n = len(rewards_history)
            wait_tail = avg_wait_history[-10:] if avg_wait_history else []
            avg_wait_last_10 = sum(wait_tail) / len(wait_tail) if wait_tail else 0.0
            avg_wait_running = sum(avg_wait_history) / len(avg_wait_history) if avg_wait_history else 0.0
            return {
                "rewards_history": list(rewards_history),
                "avg_wait_history": list(avg_wait_history),
                "episodes_done": n,
                "episodes_total": episodes_total,
                "last_reward": last_reward,
                "last_episode_wait": avg_wait_history[-1] if avg_wait_history else 0.0,
                "avg_wait_last_10": avg_wait_last_10,
                "avg_wait_running": avg_wait_running,
                "epsilon": epsilon,
                "cancelled": cancelled,
                "last_saved_episode": last_saved_episode,
                "checkpoint_episode": last_saved_episode,
            }

        def work(job: Job):
            cm = _silence_stdio() if quiet else contextlib.nullcontext()
            with cm:
                _train_work(job)

        def _train_work(job: Job):
            policy_cfg = PolicyConfig.load()
            train_params = policy_cfg.training
            max_green = float(max_green_seconds) if max_green_seconds and max_green_seconds > 0 else None
            log_path = Path(training_log_path) if training_log_path else DQN_TRAINING_LOG_PATH
            objectives_path = Path(policy_path).with_name("dqn_policy_objectives.txt")
            write_objectives_text(policy_cfg, objectives_path)

            from dataclasses import asdict

            from flowgrid.maps.map_env import sumo_env_extras
            from flowgrid.maps.map_registry import get_map

            preset = get_map(map_id) if map_id else None
            map_settings = asdict(preset) if preset else None
            env_extras = sumo_env_extras(map_settings) if map_settings else {}
            phase_ring = env_extras.pop("phase_ring", None)
            topology = env_extras.pop("topology", None)

            ep_cfg = policy_cfg.episode_training
            base_seed = int(train_seed) if train_seed is not None else int(ep_cfg.train_base_seed)
            busy_fraction_override = (
                max(0.0, min(1.0, float(busy_fraction))) if busy_fraction is not None else None
            )
            episode_limits = EpisodeLimits(
                min_sim_seconds=float(ep_cfg.min_sim_seconds),
                clear_streak_steps=int(ep_cfg.clear_streak_steps),
                max_steps=int(ep_cfg.max_steps),
                max_sim_seconds=float(ep_cfg.max_sim_seconds),
            )

            use_gui = bool(gui)
            env = SumoEnv(
                sumocfg_file=sumocfg,
                gui=use_gui,
                gui_delay=max(0, int(gui_delay)),
                on_step=None,
                live_updates=use_gui,
                step_length=train_params.step_length,
                min_green_seconds=float(min_green_seconds),
                min_green_base_seconds=float(min_green_base_seconds),
                switch_min_vehicles=int(switch_min_vehicles),
                switch_min_wait_seconds=float(switch_min_wait_seconds),
                max_green_seconds=max_green,
                quit_on_end=not use_gui,
                policy_config=policy_cfg,
                topology=topology,
                phase_ring=phase_ring,
                end_when_clear=True,
                episode_limits=episode_limits,
                **env_extras,
            )
            in_dim = env.observation_space.shape[0]
            out_dim = env.action_space.n
            quarantine_incompatible(policy_path, in_dim, out_dim)
            device_pref = str(device or train_params.device)
            agent = DQNAgent(
                in_dim,
                out_dim,
                policy_config=policy_cfg,
                device_preference=device_pref,
            )
            log_training_session_start(
                log_path,
                policy_cfg,
                map_name=map_name,
                episodes=episodes,
                policy_path=policy_path,
                training_device=str(agent.device),
                training_device_label=str(agent.device_label),
            )
            if not quiet:
                print(
                    f"Training device: {agent.device_label} ({agent.device})",
                    flush=True,
                )
            target_update_freq = train_params.target_update_freq
            canonical_policy = str(canonical_policy_path(policy_path))
            load_policy_path = canonical_policy
            if resume:
                resolved = resolve_policy_path(canonical_policy)
                if resolved is None:
                    try:
                        env.close()
                    except Exception:
                        pass
                    job.status = "failed"
                    job.error = (
                        f"Resume requested but no checkpoint found for map policy "
                        f"(looked under {canonical_policy_path(policy_path).parent})"
                    )
                    return
                load_policy_path = str(resolved)
                if resolved.resolve() != Path(canonical_policy).resolve():
                    promote_latest_checkpoint_to_canonical(canonical_policy)
                    load_policy_path = canonical_policy
                load_result = load_agent_checkpoint(
                    agent, load_policy_path, fine_tune=policy_cfg.fine_tune
                )
                if not load_result.loaded:
                    try:
                        env.close()
                    except Exception:
                        pass
                    job.status = "failed"
                    job.error = f"Resume requested but checkpoint load failed: {policy_path}"
                    return
                job.message = (
                    f"Resumed policy (eps={agent.epsilon:.3f}, episodes={agent.episodes_done}"
                    f"{', from log' if load_result.legacy_weights_only else ''})"
                )
                if policy_cfg.fine_tune.apply_on_resume:
                    target_update_freq = int(policy_cfg.fine_tune.target_update_freq)
            rewards_history: list[float] = []
            avg_wait_history: list[float] = []
            cancelled = False
            last_saved_episode: int | None = None

            snap_dir = os.path.join(tempfile.gettempdir(), "flowgrid")
            os.makedirs(snap_dir, exist_ok=True)
            map_key = map_id or "default"
            base_flows = dict(preset.flows) if preset else dict(DEFAULT_FLOWS)
            lanes_per_approach = int(preset.lanes_per_approach) if preset else 4
            random_traffic_cfg = policy_cfg.random_traffic_training
            warmup_routes = ensure_hard_warmup_routes(
                snap_dir,
                map_key,
                base_flows,
                lanes_per_approach,
                random_traffic_cfg,
            )
            busy_snap_path = busy_snapshot_path(snap_dir, map_key, base_seed)
            busy_snapshot_ready = os.path.isfile(busy_snap_path)

            try:
                for episode in range(episodes):
                    if self._is_cancelled(job.id):
                        cancelled = True
                        break

                    episode_seed = base_seed + agent.episodes_done
                    spec = sample_traffic_episode(
                        cache_dir=snap_dir,
                        map_key=map_key,
                        base_flows=base_flows,
                        lanes_per_approach=lanes_per_approach,
                        phase_counts=agent.phase_episodes_done,
                        episode_index=agent.episodes_done,
                        rng=random.Random(episode_seed),
                        busy_fraction_override=busy_fraction_override,
                        config=random_traffic_cfg,
                    )
                    if spec.busy_snapshot:
                        if not busy_snapshot_ready:
                            try:
                                ensure_busy_training_snapshot(
                                    env,
                                    busy_snap_path,
                                    seed=base_seed,
                                    warmup_sim_seconds=float(ep_cfg.busy_warmup_sim_seconds),
                                    route_files=warmup_routes,
                                )
                                busy_snapshot_ready = True
                            except Exception as exc:
                                try:
                                    env.close()
                                except Exception:
                                    pass
                                job.status = "failed"
                                job.error = f"Busy snapshot warmup failed: {exc}"
                                return
                        state, reset_info = reset_from_busy_snapshot(
                            env,
                            busy_snap_path,
                            seed=base_seed,
                            warmup_sim_seconds=float(ep_cfg.busy_warmup_sim_seconds),
                            route_files=warmup_routes,
                        )
                    else:
                        state, reset_info = env.reset(
                            seed=episode_seed,
                            options={"route_files": spec.route_path},
                        )
                    action_mask = reset_info.get("action_mask")
                    episode_start_kind = reset_info.get("episode_start_kind", "fresh")
                    done = False
                    truncated = False
                    episode_reward = 0.0
                    episode_wait_sum = 0.0
                    reward_parts: dict[str, float] = {}
                    action_counts = {"hold": 0, "advance": 0, "invalid": 0}
                    ended_reason = ""
                    sim_t = 0.0
                    step_count = 0

                    while not (done or truncated):
                        action = agent.select_action(state, action_mask)
                        next_state, reward, done, truncated, info = env.step(action)
                        episode_wait_sum += env.total_waiting_time()
                        next_mask = info.get("action_mask")
                        terminal = done or truncated
                        agent.memory.push(
                            state, action, reward, next_state, terminal, action_mask, next_mask
                        )
                        agent.optimize_model()
                        state = next_state
                        action_mask = next_mask
                        episode_reward += reward
                        step_count = int(info.get("step_count", step_count + 1))
                        sim_t = float(info.get("sim_time", env.sim_time))
                        if info.get("ended_reason"):
                            ended_reason = str(info["ended_reason"])
                        if info.get("invalid_action"):
                            action_counts["invalid"] += 1
                        if info.get("action_applied", action) == 0:
                            action_counts["hold"] += 1
                        else:
                            action_counts["advance"] += 1
                        for key, val in info.get("reward_components", {}).items():
                            reward_parts[key] = reward_parts.get(key, 0.0) + float(val)

                    if not ended_reason and truncated:
                        ended_reason = env._episode_tracker.state.ended_reason or "truncated"

                    agent.update_epsilon()
                    agent.episodes_done += 1
                    agent.phase_episodes_done[spec.phase] = (
                        int(agent.phase_episodes_done.get(spec.phase, 0)) + 1
                    )
                    agent.steps_done += step_count
                    if agent.episodes_done % target_update_freq == 0:
                        agent.update_target_network()

                    episode_wait = episode_wait_sum
                    rewards_history.append(episode_reward)
                    avg_wait_history.append(episode_wait)
                    log_episode(
                        log_path,
                        episode=agent.episodes_done,
                        reward_total=episode_reward,
                        total_wait=episode_wait,
                        epsilon=agent.epsilon,
                        reward_components=reward_parts,
                        actions=action_counts,
                        sim_time=sim_t,
                        steps=step_count,
                        ended_reason=ended_reason,
                        episode_start_kind=episode_start_kind,
                        episode_seed=episode_seed,
                        sampled_phase=spec.phase,
                        flow_scale=spec.flow_scale,
                        busy_snapshot=spec.busy_snapshot,
                        phase_episodes_done=dict(agent.phase_episodes_done),
                    )
                    transparency_report = format_episode_transparency_report(
                        episode=agent.episodes_done,
                        reward_total=episode_reward,
                        transparency=env.get_episode_transparency(),
                        sampled_phase=spec.phase,
                        flow_scale=spec.flow_scale,
                        busy_snapshot=spec.busy_snapshot,
                        sim_time=sim_t,
                        steps=step_count,
                        ended_reason=ended_reason,
                        epsilon=agent.epsilon,
                    )
                    append_episode_transparency_report(transparency_report, echo=not quiet)

                    ep_done = episode + 1
                    saved = _maybe_checkpoint(
                        agent, canonical_policy, agent.episodes_done, checkpoint_every
                    )
                    if saved is not None:
                        last_saved_episode = saved

                    job.progress = ep_done / episodes
                    mean_step_wait = episode_wait / max(1, step_count)
                    job.message = (
                        f"Episode {ep_done}/{episodes} (total {agent.episodes_done}) "
                        f"reward={episode_reward:.1f} "
                        f"wait={episode_wait:.0f} mean_step={mean_step_wait:.0f} "
                        f"sim_t={sim_t:.0f}s steps={step_count} "
                        f"end={ended_reason or '?'} start={episode_start_kind} "
                        f"phase={spec.phase}(scale={spec.flow_scale:.2f},busy={int(spec.busy_snapshot)}) "
                        f"counts=easy:{agent.phase_episodes_done.get('easy', 0)} "
                        f"med:{agent.phase_episodes_done.get('medium', 0)} "
                        f"hard:{agent.phase_episodes_done.get('hard', 0)} "
                        f"eps={agent.epsilon:.3f}"
                    )
                    job.result = _train_progress_result(
                        rewards_history,
                        avg_wait_history,
                        episodes,
                        episode_reward,
                        agent.epsilon,
                        last_saved_episode=last_saved_episode,
                    )
                    job.result["policy_config_path"] = policy_cfg.source_path
                    job.result["training_log_path"] = str(log_path)
                    job.result["objectives_path"] = str(objectives_path)
                    job.result["last_reward_components"] = dict(reward_parts)

                if rewards_history and not cancelled and last_saved_episode != agent.episodes_done:
                    _save_policy(agent, canonical_policy, episode=agent.episodes_done)
                    last_saved_episode = agent.episodes_done
                if rewards_history and not cancelled:
                    promote_latest_checkpoint_to_canonical(canonical_policy)
            finally:
                try:
                    env.close()
                except Exception:
                    pass
                if rewards_history and cancelled and last_saved_episode != agent.episodes_done:
                    _save_policy(agent, canonical_policy, episode=agent.episodes_done)
                    last_saved_episode = agent.episodes_done
                if rewards_history and cancelled:
                    promote_latest_checkpoint_to_canonical(canonical_policy)

            if not rewards_history:
                job.message = "Training stopped before any episode finished"
                job.result = {"cancelled": True, "episodes_done": 0, "episodes_total": episodes}
                return

            plt.figure(figsize=(10, 5))
            plt.plot(rewards_history, label="Episode Reward", color="#58a6ff")
            if avg_wait_history:
                ax2 = plt.gca().twinx()
                ax2.plot(avg_wait_history, label="Total wait", color="#f0883e", alpha=0.85)
                ax2.set_ylabel("Total wait (lower is better)", color="#f0883e")
                ax2.tick_params(axis="y", labelcolor="#f0883e")
            plt.xlabel("Episode")
            plt.ylabel("Cumulative Reward")
            plt.title("DQN Learning Curve")
            plt.legend(loc="upper left")
            plt.grid(alpha=0.3)
            plt.savefig(learning_curve_path, facecolor="#0d1117")
            plt.close()

            last_reward = rewards_history[-1]
            job.result = {
                **_train_progress_result(
                    rewards_history,
                    avg_wait_history,
                    episodes,
                    last_reward,
                    agent.epsilon,
                    cancelled=cancelled,
                    last_saved_episode=last_saved_episode,
                ),
                "episodes": len(rewards_history),
                "episodes_planned": episodes,
                "final_reward": last_reward,
                "model": policy_path,
                "chart": learning_curve_path,
                "checkpoint_every": checkpoint_every,
            }
            if cancelled:
                job.message = (
                    f"Stopped early after {len(rewards_history)} episode(s); "
                    f"policy saved to {policy_path}"
                )
            else:
                job.message = "Training complete"

        return self.start("train", work)

    def start_compare(
        self,
        sumocfg: str,
        baseline_green_seconds: float,
        seed: int = 42,
        policy_path: str = "dqn_policy.pth",
        gui: bool = False,
        gui_delay: int = 80,
        min_green_seconds: float = 60,
        min_green_base_seconds: float = 5.0,
        switch_min_vehicles: int = 3,
        switch_min_wait_seconds: float = 25.0,
        max_green_seconds: float | None = None,
        map_id: str = "",
        map_name: str = "",
        inject_seconds: float | None = None,
    ) -> str:
        def work(job: Job):
            from flowgrid.rl.policy_checkpoint import quarantine_incompatible as _quarantine

            use_gui = bool(gui)
            job.result = {"baseline_status": "waiting", "dqn_status": "waiting"}
            job.message = "Compare — starting baseline..."
            job.progress = 0.05

            from dataclasses import asdict

            from flowgrid.maps.map_env import sumo_env_extras
            from flowgrid.maps.map_registry import get_map

            preset = get_map(map_id) if map_id else None
            map_settings = asdict(preset) if preset else None
            env_extras = sumo_env_extras(map_settings) if map_settings else {}
            phase_ring = env_extras.pop("phase_ring", None)
            topology = env_extras.pop("topology", None)

            env_probe = SumoEnv(
                sumocfg_file=sumocfg,
                gui=False,
                quit_on_end=True,
                live_updates=False,
                topology=topology,
                phase_ring=phase_ring,
                **env_extras,
            )
            in_dim = env_probe.observation_space.shape[0]
            out_dim = env_probe.action_space.n
            env_probe.close()
            _quarantine(policy_path, in_dim, out_dim)

            def on_phase(phase: str, state: str, value: float | None = None):
                r = dict(job.result)
                r[f"{phase}_status"] = state
                if value is not None:
                    r[f"{phase}_wait"] = value
                if phase == "baseline" and state == "running":
                    r["dqn_status"] = "waiting"
                    job.message = "Compare 1/2 — baseline running..."
                    job.progress = 0.2
                elif phase == "baseline" and state == "done":
                    job.message = "Compare 2/2 — DQN running..."
                    job.progress = 0.55
                elif phase == "dqn" and state == "running":
                    r["dqn_status"] = "running"
                    job.message = "Compare 2/2 — DQN running..."
                    job.progress = 0.55
                elif phase == "dqn" and state == "done":
                    job.progress = 0.9
                job.result = r

            max_green = float(max_green_seconds) if max_green_seconds and max_green_seconds > 0 else None
            baseline_metrics, dqn_metrics, model_error = evaluate_compare_pair(
                sumocfg_file=sumocfg,
                policy_path=policy_path,
                baseline_green_seconds=baseline_green_seconds,
                seed=seed,
                gui=use_gui,
                gui_delay=max(0, int(gui_delay)),
                on_step=self._set_live if use_gui else None,
                on_phase=on_phase,
                min_green_seconds=float(min_green_seconds),
                min_green_base_seconds=float(min_green_base_seconds),
                switch_min_vehicles=int(switch_min_vehicles),
                switch_min_wait_seconds=float(switch_min_wait_seconds),
                max_green_seconds=max_green,
                map_settings=map_settings,
                inject_seconds=inject_seconds,
            )
            fixed_wait = baseline_metrics.priority_wait_sum
            dqn_wait = dqn_metrics.priority_wait_sum
            fixed_wait_all = baseline_metrics.total_wait
            dqn_wait_all = dqn_metrics.total_wait

            improvement = 0.0
            if dqn_wait > 0 and fixed_wait > 0:
                improvement = ((fixed_wait - dqn_wait) / fixed_wait) * 100

            improvement_all = 0.0
            if dqn_wait_all > 0 and fixed_wait_all > 0:
                improvement_all = ((fixed_wait_all - dqn_wait_all) / fixed_wait_all) * 100

            emg_improvement = 0.0
            if dqn_metrics.emergency_wait_sum > 0 and baseline_metrics.emergency_wait_sum > 0:
                emg_improvement = (
                    (baseline_metrics.emergency_wait_sum - dqn_metrics.emergency_wait_sum)
                    / baseline_metrics.emergency_wait_sum
                ) * 100
            elif baseline_metrics.emergency_wait_sum > 0 and dqn_metrics.emergency_wait_sum == 0:
                emg_improvement = 100.0

            transit_improvement = 0.0
            if dqn_metrics.transit_wait_sum > 0 and baseline_metrics.transit_wait_sum > 0:
                transit_improvement = (
                    (baseline_metrics.transit_wait_sum - dqn_metrics.transit_wait_sum)
                    / baseline_metrics.transit_wait_sum
                ) * 100
            elif baseline_metrics.transit_wait_sum > 0 and dqn_metrics.transit_wait_sum == 0:
                transit_improvement = 100.0

            chart_dir = os.path.dirname(policy_path) or "."
            chart_path = os.path.join(chart_dir, "comparison_bar.png")
            plt.figure(figsize=(8, 6))
            labels = ["Fixed-Time Baseline", "Trained DQN"]
            values = [fixed_wait, dqn_wait if dqn_wait > 0 else 0]
            colors = ["#f85149", "#3fb950" if dqn_wait > 0 else "#484f58"]
            plt.bar(labels, values, color=colors)
            plt.ylabel("Bus + emergency wait (lower is better)")
            plt.title(f"Priority vehicles — baseline {baseline_green_seconds}s vs DQN")
            ymax = max(values) if max(values) > 0 else 1
            for i, v in enumerate(values):
                plt.text(i, v + ymax * 0.02, str(int(v)), ha="center", fontweight="bold")
            plt.savefig(chart_path, facecolor="#0d1117")
            plt.close()

            emergency_charts = save_emergency_comparison_charts(
                baseline_metrics,
                dqn_metrics,
                chart_dir,
                title_suffix=f"seed {seed}",
            )
            transit_charts = save_transit_comparison_charts(
                baseline_metrics,
                dqn_metrics,
                chart_dir,
                title_suffix=f"seed {seed}",
            )
            summary_chart = save_compare_summary_charts(
                baseline_metrics,
                dqn_metrics,
                chart_dir,
                title_suffix=f"seed {seed}",
            )

            job.progress = 1.0
            job.result = {
                "baseline_green_seconds": baseline_green_seconds,
                "baseline_status": "done",
                "baseline_wait": fixed_wait,
                "baseline_wait_all": float(fixed_wait_all),
                "dqn_status": (
                    "done"
                    if dqn_wait > 0
                    else ("failed" if model_error else "done")
                ),
                "dqn_wait": dqn_wait,
                "dqn_wait_all": float(dqn_wait_all),
                "fixed_wait": fixed_wait,
                "fixed_wait_all": float(fixed_wait_all),
                "improvement_percent": improvement,
                "improvement_percent_all": float(improvement_all),
                "chart": chart_path,
                "summary_chart": summary_chart,
                "emergency_chart": emergency_charts.get("emergency_bars", ""),
                "emergency_timeline_chart": emergency_charts.get("emergency_timeline", ""),
                "transit_chart": transit_charts.get("transit_bars", ""),
                "transit_timeline_chart": transit_charts.get("transit_timeline", ""),
                "baseline_emergency_wait": float(baseline_metrics.emergency_wait_sum),
                "dqn_emergency_wait": float(dqn_metrics.emergency_wait_sum),
                "baseline_emergency_preempt_steps": int(baseline_metrics.emergency_preempt_steps),
                "dqn_emergency_preempt_steps": int(dqn_metrics.emergency_preempt_steps),
                "baseline_emergency_vehicles": int(baseline_metrics.emergency_vehicles_seen),
                "dqn_emergency_vehicles": int(dqn_metrics.emergency_vehicles_seen),
                "emergency_improvement_percent": float(emg_improvement),
                "baseline_transit_wait": float(baseline_metrics.transit_wait_sum),
                "dqn_transit_wait": float(dqn_metrics.transit_wait_sum),
                "baseline_transit_vehicles": int(baseline_metrics.transit_vehicles_seen),
                "dqn_transit_vehicles": int(dqn_metrics.transit_vehicles_seen),
                "baseline_all_vehicles": int(baseline_metrics.all_vehicles_seen),
                "dqn_all_vehicles": int(dqn_metrics.all_vehicles_seen),
                "compare_scheduled_cars": int(baseline_metrics.scheduled_cars),
                "compare_scheduled_transit": int(baseline_metrics.scheduled_transit),
                "compare_scheduled_emergency": int(baseline_metrics.scheduled_emergency),
                "transit_improvement_percent": float(transit_improvement),
                "emergency_timelines": {
                    "baseline": {
                        "t": baseline_metrics.timeline_sim_t,
                        "w": baseline_metrics.timeline_emergency_wait,
                    },
                    "dqn": {
                        "t": dqn_metrics.timeline_sim_t,
                        "w": dqn_metrics.timeline_emergency_wait,
                    },
                },
                "transit_timelines": {
                    "baseline": {
                        "t": baseline_metrics.timeline_sim_t,
                        "w": baseline_metrics.timeline_transit_wait,
                    },
                    "dqn": {
                        "t": dqn_metrics.timeline_sim_t,
                        "w": dqn_metrics.timeline_transit_wait,
                    },
                },
                "seed": seed,
                "model_error": model_error,
                "map_id": map_id,
                "map_name": map_name,
                "min_green_seconds": float(min_green_seconds),
                "min_green_base_seconds": float(min_green_base_seconds),
                "switch_min_vehicles": int(switch_min_vehicles),
            }
            compare_payload = {
                "model_error": model_error or "",
                "dqn_wait_all": float(dqn_wait_all),
                "fixed_wait_all": float(fixed_wait_all),
                "baseline_wait_all": float(fixed_wait_all),
            }
            job.result["compare_valid"] = not is_catastrophic_compare(compare_payload)
            best_prev = read_best_dqn_wait_all(policy_path)
            if is_valid_improvement(compare_payload, best_prev):
                save_best_policy(policy_path, float(dqn_wait_all))
                job.result["best_policy_path"] = best_policy_path(policy_path)
                job.result["best_dqn_wait_all"] = float(dqn_wait_all)
            elif is_catastrophic_compare(compare_payload):
                job.result["compare_invalid"] = True
                if restore_best_policy(policy_path):
                    job.result["policy_rolled_back"] = True
                    job.result["rollback_from"] = best_policy_path(policy_path)
            if fixed_wait > 0:
                try:
                    saved = append_comparison_record(
                        {
                            "map_id": map_id,
                            "map_name": map_name,
                            "baseline_green_seconds": float(baseline_green_seconds),
                            "seed": int(seed),
                            "baseline_wait": float(fixed_wait),
                            "dqn_wait": float(dqn_wait),
                            "baseline_wait_all": float(fixed_wait_all),
                            "dqn_wait_all": float(dqn_wait_all),
                            "improvement_percent": float(improvement),
                            "improvement_percent_all": float(improvement_all),
                            "baseline_priority_wait": float(fixed_wait),
                            "dqn_priority_wait": float(dqn_wait),
                            "baseline_emergency_wait": float(baseline_metrics.emergency_wait_sum),
                            "dqn_emergency_wait": float(dqn_metrics.emergency_wait_sum),
                            "emergency_improvement_percent": float(emg_improvement),
                            "baseline_transit_wait": float(baseline_metrics.transit_wait_sum),
                            "dqn_transit_wait": float(dqn_metrics.transit_wait_sum),
                            "transit_improvement_percent": float(transit_improvement),
                            "baseline_emergency_preempt_steps": int(baseline_metrics.emergency_preempt_steps),
                            "dqn_emergency_preempt_steps": int(dqn_metrics.emergency_preempt_steps),
                            "min_green_seconds": float(min_green_seconds),
                            "min_green_base_seconds": float(min_green_base_seconds),
                            "switch_min_vehicles": int(switch_min_vehicles),
                            "max_green_seconds": max_green,
                            "model_error": model_error or "",
                        }
                    )
                    job.result["report_id"] = saved["id"]
                    job.result["report_saved_at"] = saved.get("timestamp_display", saved["timestamp"])
                except OSError as exc:
                    job.result["report_save_error"] = str(exc)
            if job.result.get("compare_invalid"):
                hint = model_error or "DQN all-vehicle wait much worse than baseline"
                if job.result.get("policy_rolled_back"):
                    job.message = f"INVALID COMPARE — {hint}. Restored {job.result.get('rollback_from', 'best checkpoint')}."
                else:
                    job.message = f"INVALID COMPARE — {hint}. Run --fresh; no best checkpoint to restore."
            elif model_error and dqn_wait == 0:
                job.message = f"Baseline complete. DQN: {model_error}"
            else:
                job.message = "Comparison complete"

        return self.start("compare", work)

    def _wait_for_job(
        self,
        child_id: str,
        parent_job: Job,
        *,
        progress_fn: Callable[[float], float] | None = None,
        poll_s: float = 0.25,
    ) -> Job | None:
        """Poll a child job; cancel child if parent curriculum job was cancelled."""
        while True:
            if self._is_cancelled(parent_job.id):
                self.request_cancel(child_id)
            child = self.get_job(child_id)
            if not child:
                return None
            parent_job.message = child.message or parent_job.message
            if progress_fn is not None:
                parent_job.progress = progress_fn(child.progress)
            if child.status in ("completed", "failed"):
                return child
            time.sleep(poll_s)

    def start_curriculum(
        self,
        sumocfg: str,
        policy_path: str,
        learning_curve_path: str,
        *,
        map_id: str = "",
        map_name: str = "",
        min_green_seconds: float = 60,
        min_green_base_seconds: float = 5,
        switch_min_vehicles: int = 3,
        switch_min_wait_seconds: float = 25,
        max_green_seconds: float | None = None,
        checkpoint_every: int = 10,
        curriculum: CurriculumConfig | None = None,
        gui: bool = False,
        gui_delay: int = 80,
        quiet: bool = False,
        training_log_path: str | os.PathLike | None = None,
    ) -> str:
        cfg = curriculum or CurriculumConfig.load()

        def work(job: Job):
            cm = _silence_stdio() if quiet else contextlib.nullcontext()
            with cm:
                _curriculum_work(job)

        def _curriculum_work(job: Job):
            cycles_out: list[dict[str, Any]] = []
            cancelled = False
            curve = learning_curve_path

            for cycle in range(cfg.max_cycles):
                if self._is_cancelled(job.id):
                    cancelled = True
                    break

                use_resume = cycle > 0 or cfg.resume_after_first_cycle
                job.message = (
                    f"Auto {cycle + 1}/{cfg.max_cycles}: training {cfg.episodes_per_cycle} episodes "
                    f"({'resume' if use_resume else 'fresh'})..."
                )
                job.progress = cycle / max(cfg.max_cycles, 1)

                train_id = self.start_train(
                    sumocfg,
                    episodes=int(cfg.episodes_per_cycle),
                    policy_path=policy_path,
                    learning_curve_path=curve,
                    checkpoint_every=checkpoint_every,
                    min_green_seconds=min_green_seconds,
                    min_green_base_seconds=min_green_base_seconds,
                    switch_min_vehicles=switch_min_vehicles,
                    switch_min_wait_seconds=switch_min_wait_seconds,
                    max_green_seconds=max_green_seconds,
                    map_name=map_name,
                    map_id=map_id,
                    resume=use_resume,
                    gui=bool(gui),
                    gui_delay=int(gui_delay),
                    quiet=bool(quiet),
                    training_log_path=training_log_path,
                )

                def train_prog(p: float) -> float:
                    return (cycle + 0.45 * p) / max(cfg.max_cycles, 1)

                train_job = self._wait_for_job(train_id, job, progress_fn=train_prog)
                if train_job is None or train_job.status == "failed":
                    job.error = train_job.error if train_job else "Training job lost"
                    return
                if self._is_cancelled(job.id):
                    cancelled = True
                    break

                train_result = dict(train_job.result or {})
                job.message = f"Auto {cycle + 1}/{cfg.max_cycles}: fair Compare (seed {cfg.compare_seed})..."
                job.progress = (cycle + 0.5) / max(cfg.max_cycles, 1)

                compare_id = self.start_compare(
                    sumocfg,
                    float(cfg.baseline_green_seconds),
                    seed=int(cfg.compare_seed),
                    policy_path=policy_path,
                    gui=bool(cfg.compare_gui),
                    gui_delay=int(cfg.compare_delay_ms),
                    min_green_seconds=min_green_seconds,
                    min_green_base_seconds=min_green_base_seconds,
                    switch_min_vehicles=switch_min_vehicles,
                    switch_min_wait_seconds=switch_min_wait_seconds,
                    max_green_seconds=max_green_seconds,
                    map_id=map_id,
                    map_name=map_name,
                    inject_seconds=float(cfg.compare_inject_seconds),
                )

                def compare_prog(p: float) -> float:
                    return (cycle + 0.45 + 0.5 * p) / max(cfg.max_cycles, 1)

                compare_job = self._wait_for_job(compare_id, job, progress_fn=compare_prog)
                if compare_job is None or compare_job.status == "failed":
                    job.error = compare_job.error if compare_job else "Compare job lost"
                    return
                if self._is_cancelled(job.id):
                    cancelled = True
                    break

                compare_result = dict(compare_job.result or {})
                verdict = analyze_compare_result(compare_result, cfg)
                cycle_record = {
                    "cycle": cycle + 1,
                    "episodes": int(cfg.episodes_per_cycle),
                    "train_epsilon": train_result.get("epsilon"),
                    "train_avg_wait_last_10": train_result.get("avg_wait_last_10"),
                    "improvement_all_pct": verdict.improvement_all_pct,
                    "improvement_priority_pct": verdict.improvement_priority_pct,
                    "summary": verdict.summary,
                    "recommendation": verdict.recommendation,
                    "success": verdict.success,
                    "model_error": verdict.model_error,
                    "compare": {
                        "dqn_wait_all": compare_result.get("dqn_wait_all"),
                        "baseline_wait_all": compare_result.get("fixed_wait_all"),
                    },
                }
                cycles_out.append(cycle_record)
                log_curriculum_cycle(cycle_record)

                job.result = {
                    "cycles": cycles_out,
                    "last_cycle": cycle_record,
                    "last_compare": compare_result,
                    "last_train": train_result,
                    "cancelled": cancelled,
                }
                job.message = f"Cycle {cycle + 1} done — {verdict.summary}"

                if cycle + 1 >= cfg.min_cycles and not verdict.continue_training:
                    job.message = f"Auto curriculum finished: {verdict.summary}"
                    break
                if compare_result.get("compare_invalid"):
                    job.message = f"Auto curriculum stopped (invalid Compare): {verdict.summary}"
                    break

            job.progress = 1.0
            if cancelled:
                job.message = f"Auto curriculum stopped after {len(cycles_out)} cycle(s)."
            elif not cycles_out:
                job.message = "Auto curriculum finished with no complete cycles."
            job.result = {
                "cycles": cycles_out,
                "cancelled": cancelled,
                "curriculum_log": str(CURRICULUM_LOG_PATH),
            }

        return self.start("curriculum", work)


runner = JobRunner()
