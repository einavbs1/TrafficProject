from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone

from flowgrid.eval.compare_metrics import CompareEpisodeMetrics
from flowgrid.eval.evaluate import evaluate_compare_pair


@dataclass
class RunRecord:
    run_index: int
    seed: int
    ok: bool
    error: str
    baseline: CompareEpisodeMetrics
    dqn: CompareEpisodeMetrics

    @property
    def dqn_wins(self) -> bool:
        return self.ok and self.dqn.total_wait < self.baseline.total_wait

    @property
    def improvement_pct(self) -> float | None:
        if not self.ok:
            return None
        base = float(self.baseline.total_wait)
        if base <= 0:
            return None
        return (base - float(self.dqn.total_wait)) / base * 100.0


def episodes_label(episodes: int | None) -> str:
    return str(episodes) if episodes is not None else "Unknown"


def fmt_num(value: float | int) -> str:
    if isinstance(value, float):
        if abs(value) >= 1000:
            return f"{value:,.0f}"
        return f"{value:.1f}"
    return str(value)


def table_header() -> str:
    cols = [
        ("run", 4),
        ("seed", 8),
        ("status", 8),
        ("b_wait", 12),
        ("d_wait", 12),
        ("b_served", 9),
        ("d_served", 9),
        ("b_emg", 10),
        ("d_emg", 10),
        ("b_transit", 11),
        ("d_transit", 11),
        ("dqn_win", 8),
        ("improve%", 10),
    ]
    header = " ".join(name.rjust(width) for name, width in cols)
    rule = " ".join("-" * width for _, width in cols)
    return f"{header}\n{rule}"


def format_row(record: RunRecord) -> str:
    status = "ok" if record.ok else "FAIL"
    win = "yes" if record.dqn_wins else "no"
    if not record.ok:
        win = "-"
    imp = record.improvement_pct
    imp_s = f"{imp:+.1f}" if imp is not None else "-"
    b = record.baseline
    d = record.dqn
    return (
        f"{record.run_index:4d} "
        f"{record.seed:8d} "
        f"{status:>8} "
        f"{fmt_num(b.total_wait):>12} "
        f"{fmt_num(d.total_wait):>12} "
        f"{b.all_vehicles_seen:9d} "
        f"{d.all_vehicles_seen:9d} "
        f"{fmt_num(b.emergency_wait_sum):>10} "
        f"{fmt_num(d.emergency_wait_sum):>10} "
        f"{fmt_num(b.transit_wait_sum):>11} "
        f"{fmt_num(d.transit_wait_sum):>11} "
        f"{win:>8} "
        f"{imp_s:>10}"
    )


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summary_block(records: list[RunRecord], model_episodes: int | None) -> str:
    ok_records = [item for item in records if item.ok]
    failed = len(records) - len(ok_records)
    if not ok_records:
        return f"SUMMARY: 0 successful runs ({failed} failed).\n"

    b_wait = _average([float(r.baseline.total_wait) for r in ok_records])
    d_wait = _average([float(r.dqn.total_wait) for r in ok_records])
    b_served = _average([float(r.baseline.all_vehicles_seen) for r in ok_records])
    d_served = _average([float(r.dqn.all_vehicles_seen) for r in ok_records])
    b_emg = _average([float(r.baseline.emergency_wait_sum) for r in ok_records])
    d_emg = _average([float(r.dqn.emergency_wait_sum) for r in ok_records])
    b_tr = _average([float(r.baseline.transit_wait_sum) for r in ok_records])
    d_tr = _average([float(r.dqn.transit_wait_sum) for r in ok_records])
    wins = sum(1 for r in ok_records if r.dqn_wins)
    win_rate = wins / len(ok_records) * 100.0
    improvements = [r.improvement_pct for r in ok_records if r.improvement_pct is not None]
    avg_imp = _average(improvements)

    lines = [
        "",
        "STATISTICAL SUMMARY",
        "-" * 60,
        f"Model Training Episodes: {episodes_label(model_episodes)}",
        f"Successful runs:     {len(ok_records)} / {len(records)}  (failed: {failed})",
        f"DQN win rate:        {wins} / {len(ok_records)}  ({win_rate:.1f}%)",
        f"Avg total wait:      baseline {fmt_num(b_wait)}  |  DQN {fmt_num(d_wait)}",
        f"Avg served:          baseline {fmt_num(b_served)}  |  DQN {fmt_num(d_served)}",
        f"Avg emergency wait:  baseline {fmt_num(b_emg)}  |  DQN {fmt_num(d_emg)}",
        f"Avg transit wait:    baseline {fmt_num(b_tr)}  |  DQN {fmt_num(d_tr)}",
        f"Avg wait improvement: {avg_imp:+.2f}%  (positive = DQN lower wait)",
        "",
    ]
    if failed:
        lines.append("Failed runs:")
        for item in records:
            if not item.ok:
                lines.append(f"  run {item.run_index} seed {item.seed}: {item.error}")
        lines.append("")
    return "\n".join(lines)


def batch_header(
    map_info: dict,
    runs: int,
    inject_seconds: float,
    baseline_green: float,
    model_episodes: int | None,
    policy_path: str,
    *,
    gui: bool,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"{'=' * 100}\n"
        f"Batch evaluation  {ts}\n"
        f"Map: {map_info['display_name']} ({map_info['id']})\n"
        f"Model Training Episodes: {episodes_label(model_episodes)}\n"
        f"Policy: {policy_path}\n"
        f"Runs: {runs}  Inject until: {inject_seconds:.0f}s  Baseline green: {baseline_green:.0f}s  GUI: {'dqn' if gui else 'no'}\n"
        f"{'=' * 100}\n"
    )


def checkpoint_header(
    map_info: dict,
    checkpoint_episode: int,
    runs: int,
    seed: int | None,
    inject_seconds: float,
    baseline_green: float,
    policy_path: str,
) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    seed_label = str(seed) if seed is not None else "random"
    return (
        f"{'=' * 100}\n"
        f"Checkpoint evaluation  {ts}\n"
        f"Map: {map_info['display_name']} ({map_info['id']})\n"
        f"Training checkpoint episode: {checkpoint_episode}\n"
        f"Model Training Episodes: {checkpoint_episode}\n"
        f"Policy: {policy_path}\n"
        f"Eval runs: {runs}  Seed: {seed_label}  Inject until: {inject_seconds:.0f}s  "
        f"Baseline green: {baseline_green:.0f}s\n"
        f"{'=' * 100}\n"
    )


def execute_run(
    run_index: int,
    seed: int,
    map_info: dict,
    *,
    baseline_green: float,
    inject_seconds: float,
    quiet: bool,
    gui: bool = False,
    phase_tracker: bool = False,
) -> RunRecord:
    if not quiet:
        print(f"Run {run_index}: seed={seed} ...", flush=True)
    baseline, dqn, error = evaluate_compare_pair(
        map_info["sumocfg"],
        map_info["policy_path"],
        baseline_green_seconds=float(baseline_green),
        seed=int(seed),
        gui=bool(gui),
        gui_delay=0,
        dqn_gui_only=bool(gui),
        map_settings=map_info,
        inject_seconds=float(inject_seconds),
        log_phase_tracker=phase_tracker,
    )
    ok = not error
    if phase_tracker:
        if ok:
            b_wait = float(baseline.total_wait)
            d_wait = float(dqn.total_wait)
            if d_wait < b_wait:
                winner = "dqn"
            elif d_wait > b_wait:
                winner = "baseline"
            else:
                winner = "tie"
            print(
                f"[PHASE_TRACKER] b_wait={fmt_num(b_wait)} d_wait={fmt_num(d_wait)} winner={winner}",
                flush=True,
            )
        else:
            print(f"[PHASE_TRACKER] FAILED: {error}", flush=True)
    if not quiet:
        if ok:
            imp = (
                (baseline.total_wait - dqn.total_wait) / baseline.total_wait * 100
                if baseline.total_wait > 0
                else 0.0
            )
            print(
                f"  baseline wait {fmt_num(baseline.total_wait)}  "
                f"dqn wait {fmt_num(dqn.total_wait)}  "
                f"improve {imp:+.1f}%",
                flush=True,
            )
        else:
            print(f"  FAILED: {error}", flush=True)
    return RunRecord(
        run_index=run_index,
        seed=seed,
        ok=ok,
        error=error or "",
        baseline=baseline,
        dqn=dqn,
    )


def run_batch(
    map_info: dict,
    *,
    runs: int,
    seed: int | None,
    baseline_green: float,
    inject_seconds: float,
    quiet: bool = False,
    gui: bool = False,
    phase_tracker: bool = False,
) -> list[RunRecord]:
    records: list[RunRecord] = []
    for run_index in range(1, runs + 1):
        run_seed = int(seed) if seed is not None else random.randint(1, 2_147_483_647)
        records.append(
            execute_run(
                run_index,
                run_seed,
                map_info,
                baseline_green=baseline_green,
                inject_seconds=inject_seconds,
                quiet=quiet,
                gui=gui,
                phase_tracker=phase_tracker,
            )
        )
    return records


def build_batch_report(
    records: list[RunRecord],
    header: str,
    model_episodes: int | None,
) -> str:
    parts = [header, table_header()]
    parts.extend(format_row(record) for record in records)
    parts.append(summary_block(records, model_episodes))
    return "\n".join(parts)


def checkpoint_progress_line(records: list[RunRecord], checkpoint_episode: int) -> str:
    ok_records = [item for item in records if item.ok]
    if not ok_records:
        failed = len(records)
        return f"Checkpoint ep {checkpoint_episode}: eval failed ({failed} failed runs)"
    wins = sum(1 for r in ok_records if r.dqn_wins)
    improvements = [r.improvement_pct for r in ok_records if r.improvement_pct is not None]
    avg_imp = _average(improvements)
    return (
        f"Checkpoint ep {checkpoint_episode}: DQN wins {wins}/{len(ok_records)}, "
        f"avg improve {avg_imp:+.1f}%"
    )


def run_checkpoint_batch(
    map_info: dict,
    *,
    runs: int,
    seed: int | None,
    baseline_green: float,
    inject_seconds: float,
    checkpoint_episode: int,
    quiet: bool = True,
) -> tuple[list[RunRecord], str]:
    records = run_batch(
        map_info,
        runs=runs,
        seed=seed,
        baseline_green=baseline_green,
        inject_seconds=inject_seconds,
        quiet=quiet,
    )
    header = checkpoint_header(
        map_info,
        checkpoint_episode,
        runs,
        seed,
        inject_seconds,
        baseline_green,
        map_info["policy_path"],
    )
    report = build_batch_report(records, header, checkpoint_episode)
    return records, report
