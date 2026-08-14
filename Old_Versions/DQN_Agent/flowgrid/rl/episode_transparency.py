from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowgrid.paths import EPISODE_TRANSPARENCY_LOG_PATH

TRAFFIC_PROFILE_LABELS = {
    "easy": "Sparse",
    "medium": "Medium",
    "hard": "Heavy",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def traffic_profile_label(
    *,
    sampled_phase: str,
    flow_scale: float | None = None,
    busy_snapshot: bool | None = None,
) -> str:
    if busy_snapshot:
        base = "Busy Snapshot"
    else:
        base = TRAFFIC_PROFILE_LABELS.get(sampled_phase, sampled_phase or "Unknown")
    parts = [base]
    if flow_scale is not None:
        parts.append(f"scale={float(flow_scale):.2f}")
    if busy_snapshot is not None and not busy_snapshot:
        parts.append("busy_snapshot=False")
    elif busy_snapshot:
        parts.append("busy_snapshot=True")
    return " | ".join(parts)


def format_episode_transparency_report(
    *,
    episode: int,
    reward_total: float,
    transparency: dict[str, Any],
    sampled_phase: str = "",
    flow_scale: float | None = None,
    busy_snapshot: bool | None = None,
    sim_time: float = 0.0,
    steps: int = 0,
    ended_reason: str = "",
    epsilon: float | None = None,
) -> str:
    phase_seconds: dict[str, float] = dict(transparency.get("phase_seconds") or {})
    actions = transparency.get("actions") or {}
    reward_components: dict[str, float] = dict(transparency.get("reward_components") or {})
    hold = int(actions.get("hold", 0))
    advance = int(actions.get("advance", 0))
    forced_hold = int(actions.get("forced_hold", 0))
    forced_advance = int(actions.get("forced_advance", 0))

    lines = [
        "=" * 80,
        f"Episode {episode} | {_now_iso()}",
        "-" * 80,
        f"Traffic Profile: {traffic_profile_label(sampled_phase=sampled_phase, flow_scale=flow_scale, busy_snapshot=busy_snapshot)}",
        "Phase Distribution:",
    ]
    if phase_seconds:
        for phase_id, seconds in sorted(phase_seconds.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"  {phase_id}: {seconds:.0f}s")
    else:
        lines.append("  (none)")

    lines.extend(
        [
            "Action Distribution (agent-chosen):",
            f"  Hold: {hold}",
            f"  Advance: {advance}",
            "Action Distribution (forced):",
            f"  Hold: {forced_hold}",
            f"  Advance: {forced_advance}",
            "Reward Components (episode sum):",
            f"  Total Reward: {reward_total:.2f}",
        ]
    )
    for key in sorted(reward_components.keys()):
        lines.append(f"  {key}: {reward_components[key]:.2f}")

    tail = f"Sim Time: {sim_time:.0f}s | Steps: {steps}"
    if ended_reason:
        tail += f" | End: {ended_reason}"
    if epsilon is not None:
        tail += f" | Epsilon: {epsilon:.4f}"
    lines.append(tail)
    lines.append("=" * 80)
    return "\n".join(lines)


def append_episode_transparency_report(
    report: str,
    path: Path | None = None,
    *,
    echo: bool = False,
) -> Path:
    log_path = path or EPISODE_TRANSPARENCY_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(report)
        handle.write("\n\n")
    if echo:
        print(report, flush=True)
    return log_path
