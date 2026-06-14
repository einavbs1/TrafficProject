"""Read training log and build summary stats for the Reports dashboard."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean

from flowgrid.rl.policy_config import DEFAULT_TRAINING_LOG_PATH


@dataclass
class TrainingDashboard:
    log_path: str = ""
    log_exists: bool = False
    total_episodes: int = 0
    max_episode: int = 0
    sessions: list[dict] = field(default_factory=list)
    last_session_planned: int = 0
    last_session_map: str = ""
    epsilon_latest: float | None = None
    wait_first_100_avg: float | None = None
    wait_last_100_avg: float | None = None
    wait_improvement_pct: float | None = None
    episode_waits: list[tuple[int, float]] = field(default_factory=list)
    ended_reason_counts: dict[str, int] = field(default_factory=dict)
    recommendation: str = ""

    def summary_lines(self) -> list[str]:
        if not self.log_exists:
            return ["No training log found. Run Train on a map to start logging."]
        lines = [
            f"Episodes logged: {self.total_episodes} (max episode #{self.max_episode})",
        ]
        if self.last_session_map:
            lines.append(f"Latest session: {self.last_session_map} ({self.last_session_planned} planned)")
        if self.epsilon_latest is not None:
            lines.append(f"Exploration ε: {self.epsilon_latest:.3f}")
        if self.wait_first_100_avg is not None and self.wait_last_100_avg is not None:
            lines.append(
                f"Training wait (all vehicles): first-100 avg {self.wait_first_100_avg:,.0f} → "
                f"last-100 avg {self.wait_last_100_avg:,.0f}"
                + (
                    f" ({self.wait_improvement_pct:+.1f}%)"
                    if self.wait_improvement_pct is not None
                    else ""
                )
            )
        if self.ended_reason_counts:
            top = ", ".join(f"{k}: {v}" for k, v in sorted(self.ended_reason_counts.items(), key=lambda x: -x[1])[:3])
            lines.append(f"Episode end reasons: {top}")
        if self.recommendation:
            lines.append(self.recommendation)
        return lines


def load_training_dashboard(log_path: Path | None = None) -> TrainingDashboard:
    path = Path(log_path or DEFAULT_TRAINING_LOG_PATH)
    dash = TrainingDashboard(log_path=str(path.resolve()), log_exists=path.is_file())
    if not dash.log_exists:
        dash.recommendation = "Train on Plan 2, then refresh Reports."
        return dash

    episodes: list[dict] = []
    sessions: list[dict] = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("event") == "session_start":
            sessions.append(rec)
        elif rec.get("event") == "episode":
            episodes.append(rec)

    dash.sessions = sessions
    dash.total_episodes = len(episodes)
    if not episodes:
        return dash

    waits = [float(e["total_wait"]) for e in episodes if e.get("total_wait") is not None]
    ep_nums = [int(e["episode"]) for e in episodes if e.get("episode") is not None]
    dash.max_episode = max(ep_nums) if ep_nums else 0
    dash.epsilon_latest = float(episodes[-1].get("epsilon", 0))

    if sessions:
        last = sessions[-1]
        dash.last_session_map = str(last.get("map_name", ""))
        dash.last_session_planned = int(last.get("episodes_planned", 0) or 0)

    if len(waits) >= 100:
        dash.wait_first_100_avg = mean(waits[:100])
        dash.wait_last_100_avg = mean(waits[-100:])
        if dash.wait_first_100_avg > 0:
            dash.wait_improvement_pct = (
                (dash.wait_first_100_avg - dash.wait_last_100_avg) / dash.wait_first_100_avg * 100.0
            )
    elif waits:
        dash.wait_last_100_avg = mean(waits)

    for e in episodes:
        reason = str(e.get("ended_reason") or "unknown")
        dash.ended_reason_counts[reason] = dash.ended_reason_counts.get(reason, 0) + 1

    # Downsample for chart (max ~400 points)
    step = max(1, len(episodes) // 400)
    dash.episode_waits = [
        (int(e["episode"]), float(e["total_wait"]))
        for e in episodes[::step]
        if e.get("episode") is not None and e.get("total_wait") is not None
    ]

    dash.recommendation = _training_recommendation(dash)
    return dash


def _training_recommendation(dash: TrainingDashboard) -> str:
    if dash.total_episodes < 200:
        return "Recommendation: run at least 200–500 resume episodes before trusting Compare."
    if dash.wait_improvement_pct is not None and dash.wait_improvement_pct < 5:
        return (
            "Recommendation: training wait barely improved — try 500+ resume episodes "
            "or tune reward in dqn_policy_config.yaml (see docs/DQN_PRIORITY.md)."
        )
    if dash.epsilon_latest is not None and dash.epsilon_latest > 0.05:
        return "Recommendation: exploration still active — more episodes will stabilize the policy."
    return (
        "Recommendation: resume train 300–500 episodes, then Compare on seeds 42, 43, 44. "
        "Check all-vehicle wait, not only bus+emergency."
    )
