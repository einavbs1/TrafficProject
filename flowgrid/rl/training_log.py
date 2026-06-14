"""Append-only training log: what the DQN optimizes and per-episode reward breakdown."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowgrid.rl.policy_config import DEFAULT_TRAINING_LOG_PATH, PolicyConfig


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_training_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_training_session_start(
    log_path: Path,
    policy_config: PolicyConfig,
    *,
    map_name: str = "",
    episodes: int = 0,
    policy_path: str = "",
    training_device: str = "",
    training_device_label: str = "",
) -> None:
    record: dict[str, Any] = {
        "event": "session_start",
        "timestamp": _now_iso(),
        "map_name": map_name,
        "episodes_planned": episodes,
        "policy_path": policy_path,
        "config_path": policy_config.source_path,
        "objectives": policy_config.objectives,
        "reward_weights": policy_config.reward.__dict__,
        "constraints": policy_config.constraints.__dict__,
        "training_device_preference": policy_config.training.device,
    }
    if training_device:
        record["training_device"] = training_device
    if training_device_label:
        record["training_device_label"] = training_device_label
    append_training_record(log_path, record)


def log_episode(
    log_path: Path,
    *,
    episode: int,
    reward_total: float,
    total_wait: float,
    epsilon: float,
    reward_components: dict[str, float],
    actions: dict[str, int] | None = None,
    sim_time: float = 0.0,
    steps: int = 0,
    ended_reason: str = "",
    episode_start_kind: str = "",
    episode_seed: int | None = None,
    sampled_phase: str = "",
    flow_scale: float | None = None,
    busy_snapshot: bool | None = None,
    phase_episodes_done: dict[str, int] | None = None,
    curriculum_phase: str = "",
    curriculum_busy_fraction: float | None = None,
) -> None:
    record: dict[str, Any] = {
        "event": "episode",
        "timestamp": _now_iso(),
        "episode": episode,
        "reward_total": reward_total,
        "total_wait": total_wait,
        "epsilon": epsilon,
        "reward_components": reward_components,
        "actions": actions or {},
        "sim_time": sim_time,
        "steps": steps,
        "ended_reason": ended_reason,
        "episode_start_kind": episode_start_kind,
    }
    if episode_seed is not None:
        record["episode_seed"] = episode_seed
    phase_label = sampled_phase or curriculum_phase
    if phase_label:
        record["sampled_phase"] = phase_label
    if flow_scale is not None:
        record["flow_scale"] = float(flow_scale)
    if busy_snapshot is not None:
        record["busy_snapshot"] = bool(busy_snapshot)
    elif curriculum_busy_fraction is not None:
        record["busy_snapshot"] = curriculum_busy_fraction > 0.0
    if phase_episodes_done is not None:
        record["phase_episodes_done"] = dict(phase_episodes_done)
    if curriculum_busy_fraction is not None:
        record["curriculum_busy_fraction"] = curriculum_busy_fraction
    append_training_record(log_path, record)


def write_objectives_text(config: PolicyConfig, text_path: Path) -> None:
    """Human-readable summary next to the policy checkpoint."""
    text_path.parent.mkdir(parents=True, exist_ok=True)
    lines = config.objectives_summary_lines()
    lines.append("")
    lines.append(f"Updated: {_now_iso()}")
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
