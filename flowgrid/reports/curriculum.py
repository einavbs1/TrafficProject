"""Auto curriculum: train → compare → analyze → repeat until goals or max cycles."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from flowgrid.paths import DEFAULT_POLICY_CONFIG_PATH, REPORTS_DIR

from flowgrid.rl.compare_guard import is_catastrophic_compare

CURRICULUM_LOG_PATH = REPORTS_DIR / "curriculum_log.jsonl"


@dataclass
class CurriculumConfig:
    episodes_per_cycle: int = 500
    max_cycles: int = 10
    compare_seed: int = 42
    compare_inject_seconds: float = 800.0
    compare_gui: bool = False
    compare_delay_ms: int = 0
    baseline_green_seconds: float = 60.0
    stop_when_all_improvement_pct: float = 0.0
    min_cycles: int = 1
    resume_after_first_cycle: bool = True

    @classmethod
    def load(cls, path: Path | None = None) -> CurriculumConfig:
        cfg_path = path or DEFAULT_POLICY_CONFIG_PATH
        if not cfg_path.is_file():
            return cls()
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        c = raw.get("curriculum") or {}
        return cls(
            episodes_per_cycle=int(c.get("episodes_per_cycle", 500)),
            max_cycles=int(c.get("max_cycles", 10)),
            compare_seed=int(c.get("compare_seed", 42)),
            compare_inject_seconds=float(c.get("compare_inject_seconds", 800)),
            compare_gui=bool(c.get("compare_gui", False)),
            compare_delay_ms=int(c.get("compare_delay_ms", 0)),
            baseline_green_seconds=float(c.get("baseline_green_seconds", 60)),
            stop_when_all_improvement_pct=float(c.get("stop_when_all_improvement_pct", 0.0)),
            min_cycles=int(c.get("min_cycles", 1)),
            resume_after_first_cycle=bool(c.get("resume_after_first_cycle", True)),
        )


@dataclass
class CurriculumVerdict:
    continue_training: bool
    success: bool
    improvement_all_pct: float
    improvement_priority_pct: float
    model_error: str | None
    summary: str
    recommendation: str


def analyze_compare_result(result: dict[str, Any], cfg: CurriculumConfig) -> CurriculumVerdict:
    err = (result.get("model_error") or "").strip() or None
    imp_all = float(result.get("improvement_percent_all", 0) or 0)
    imp_pri = float(result.get("improvement_percent", 0) or 0)
    dqn_all = float(result.get("dqn_wait_all", 0) or 0)
    base_all = float(result.get("fixed_wait_all", 0) or result.get("baseline_wait_all", 0) or 0)

    if is_catastrophic_compare(result):
        return CurriculumVerdict(
            continue_training=False,
            success=False,
            improvement_all_pct=imp_all,
            improvement_priority_pct=imp_pri,
            model_error=err,
            summary=f"Catastrophic Compare — all vehicles {imp_all:+.1f}% (gridlock or incomplete drain).",
            recommendation=(
                "Stop auto curriculum. Restore dqn_policy_best.pth if present, else run "
                "--fresh after backup. Do not resume the collapsed checkpoint."
            ),
        )

    if err and (dqn_all <= 0 or "vehicles on the map" in err.lower()):
        return CurriculumVerdict(
            continue_training=True,
            success=False,
            improvement_all_pct=imp_all,
            improvement_priority_pct=imp_pri,
            model_error=err,
            summary=f"Compare incomplete: {err[:120]}",
            recommendation="More training + check drain settings (dqn_drain_extra_seconds, left phases).",
        )

    success = imp_all >= cfg.stop_when_all_improvement_pct and base_all > 0 and dqn_all > 0
    if success:
        return CurriculumVerdict(
            continue_training=False,
            success=True,
            improvement_all_pct=imp_all,
            improvement_priority_pct=imp_pri,
            model_error=None,
            summary=f"DQN beats baseline on all-vehicle wait ({imp_all:+.1f}%).",
            recommendation="Optional: Compare seeds 43–44, then deploy or fine-tune reward weights.",
        )

    rec_parts = []
    if imp_all < -10:
        rec_parts.append("Total wait much worse — keep training or lower transit_priority_scale.")
    elif imp_all < 0:
        rec_parts.append("Close on total wait — continue auto curriculum or add 500 resume episodes.")
    else:
        rec_parts.append("Mixed metrics — check bus vs all-vehicle charts in Reports.")
    if imp_pri > 5 and imp_all < 0:
        rec_parts.append("Policy still favors buses over cars.")

    return CurriculumVerdict(
        continue_training=True,
        success=False,
        improvement_all_pct=imp_all,
        improvement_priority_pct=imp_pri,
        model_error=err,
        summary=f"All vehicles {imp_all:+.1f}% · bus+emg {imp_pri:+.1f}% vs baseline.",
        recommendation=" ".join(rec_parts),
    )


def log_curriculum_cycle(record: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).astimezone()
    entry = {
        "timestamp": now.isoformat(timespec="seconds"),
        **record,
    }
    with CURRICULUM_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_curriculum_history(limit: int = 50) -> list[dict[str, Any]]:
    if not CURRICULUM_LOG_PATH.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in CURRICULUM_LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def compare_metrics_to_result(
    *,
    baseline_metrics: Any,
    dqn_metrics: Any,
    model_error: str | None,
    baseline_green_seconds: float,
    seed: int,
    map_id: str,
    map_name: str,
    min_green_seconds: float,
    min_green_base_seconds: float,
    switch_min_vehicles: int,
    max_green_seconds: float | None,
) -> dict[str, Any]:
    """Build the same result dict shape as the Compare job (for analyze + GUI)."""
    fixed_wait = baseline_metrics.priority_wait_sum
    dqn_wait = dqn_metrics.priority_wait_sum
    fixed_wait_all = float(baseline_metrics.total_wait)
    dqn_wait_all = float(dqn_metrics.total_wait)

    improvement = 0.0
    if dqn_wait > 0 and fixed_wait > 0:
        improvement = ((fixed_wait - dqn_wait) / fixed_wait) * 100.0

    improvement_all = 0.0
    if dqn_wait_all > 0 and fixed_wait_all > 0:
        improvement_all = ((fixed_wait_all - dqn_wait_all) / fixed_wait_all) * 100.0

    emg_improvement = 0.0
    if dqn_metrics.emergency_wait_sum > 0 and baseline_metrics.emergency_wait_sum > 0:
        emg_improvement = (
            (baseline_metrics.emergency_wait_sum - dqn_metrics.emergency_wait_sum)
            / baseline_metrics.emergency_wait_sum
        ) * 100.0
    elif baseline_metrics.emergency_wait_sum > 0 and dqn_metrics.emergency_wait_sum == 0:
        emg_improvement = 100.0

    transit_improvement = 0.0
    if dqn_metrics.transit_wait_sum > 0 and baseline_metrics.transit_wait_sum > 0:
        transit_improvement = (
            (baseline_metrics.transit_wait_sum - dqn_metrics.transit_wait_sum)
            / baseline_metrics.transit_wait_sum
        ) * 100.0
    elif baseline_metrics.transit_wait_sum > 0 and dqn_metrics.transit_wait_sum == 0:
        transit_improvement = 100.0

    return {
        "baseline_green_seconds": float(baseline_green_seconds),
        "baseline_status": "done",
        "baseline_wait": float(fixed_wait),
        "baseline_wait_all": fixed_wait_all,
        "dqn_status": "done" if dqn_wait > 0 else ("failed" if model_error else "done"),
        "dqn_wait": float(dqn_wait),
        "dqn_wait_all": dqn_wait_all,
        "fixed_wait": float(fixed_wait),
        "fixed_wait_all": fixed_wait_all,
        "improvement_percent": float(improvement),
        "improvement_percent_all": float(improvement_all),
        "baseline_emergency_wait": float(baseline_metrics.emergency_wait_sum),
        "dqn_emergency_wait": float(dqn_metrics.emergency_wait_sum),
        "baseline_transit_wait": float(baseline_metrics.transit_wait_sum),
        "dqn_transit_wait": float(dqn_metrics.transit_wait_sum),
        "emergency_improvement_percent": float(emg_improvement),
        "transit_improvement_percent": float(transit_improvement),
        "compare_scheduled_cars": int(baseline_metrics.scheduled_cars),
        "compare_scheduled_transit": int(baseline_metrics.scheduled_transit),
        "compare_scheduled_emergency": int(baseline_metrics.scheduled_emergency),
        "seed": int(seed),
        "model_error": model_error,
        "map_id": map_id,
        "map_name": map_name,
        "min_green_seconds": float(min_green_seconds),
        "min_green_base_seconds": float(min_green_base_seconds),
        "switch_min_vehicles": int(switch_min_vehicles),
        "max_green_seconds": max_green_seconds,
    }


def curriculum_status_lines(limit: int = 5) -> list[str]:
    hist = load_curriculum_history(limit)
    if not hist:
        return ["No auto curriculum runs yet. Use Train → Auto progress on the Train tab."]
    lines = [f"Last {len(hist)} auto cycle(s):"]
    for row in hist[-limit:]:
        cyc = row.get("cycle", "?")
        imp = row.get("improvement_all_pct")
        summ = row.get("summary", "")
        if imp is not None:
            lines.append(f"  Cycle {cyc}: all-vehicle {float(imp):+.1f}% — {summ}")
        else:
            lines.append(f"  Cycle {cyc}: {summ}")
    last = hist[-1]
    if last.get("recommendation"):
        lines.append(f"Next: {last['recommendation']}")
    return lines
