"""Auto curriculum: train → compare → analyze → repeat (CLI, live PowerShell output)."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.jobs.job_runner import JobRunner
from flowgrid.maps.map_registry import list_maps_for_gui
from flowgrid.reports.curriculum import CURRICULUM_LOG_PATH, CurriculumConfig, curriculum_status_lines
from flowgrid.util.labeled_paths import training_log_path_for_label

from scripts.cli_poll import configure_stdout, poll_job

configure_stdout()

from flowgrid.maps.map_registry import DEFAULT_MAP_ID

DEFAULT_MAP = DEFAULT_MAP_ID


def _pick_map(map_arg: str) -> dict:
    maps = list_maps_for_gui()
    m = next((x for x in maps if x["id"] == map_arg or x["display_name"] == map_arg), None)
    if not m:
        raise SystemExit(f"Map not found: {map_arg!r}. Available: {[x['id'] for x in maps]}")
    return m


def _build_cfg(args: argparse.Namespace) -> CurriculumConfig:
    cfg = CurriculumConfig.load()
    return CurriculumConfig(
        episodes_per_cycle=int(args.episodes_per_cycle or cfg.episodes_per_cycle),
        max_cycles=int(args.max_cycles or cfg.max_cycles),
        compare_seed=int(args.compare_seed if args.compare_seed is not None else cfg.compare_seed),
        compare_inject_seconds=float(
            args.inject_seconds if args.inject_seconds is not None else cfg.compare_inject_seconds
        ),
        compare_gui=bool(args.compare_gui),
        compare_delay_ms=int(args.compare_delay_ms),
        baseline_green_seconds=float(cfg.baseline_green_seconds),
        stop_when_all_improvement_pct=float(cfg.stop_when_all_improvement_pct),
        min_cycles=int(cfg.min_cycles),
        resume_after_first_cycle=not bool(args.fresh),
    )


def main():
    parser = argparse.ArgumentParser(
        description="FlowGrid auto curriculum: train, fair compare, analyze, repeat (terminal output)"
    )
    parser.add_argument("--map", default=DEFAULT_MAP, help="Map id or display name")
    parser.add_argument("--episodes-per-cycle", type=int, default=None, help="Training episodes each cycle")
    parser.add_argument("--max-cycles", type=int, default=None, help="Max train-then-compare cycles")
    parser.add_argument("--compare-seed", type=int, default=None)
    parser.add_argument("--inject-seconds", type=float, default=None, help="Compare inject until (s)")
    parser.add_argument("--compare-gui", action="store_true", help="Show SUMO window during compare")
    parser.add_argument("--compare-delay", type=int, default=0, dest="compare_delay_ms")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Archive old policy + log first (like run_train.py --fresh)",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=10,
        help="Save dqn_policy.pth every N episodes within each cycle",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Experiment label for training log (logs/dqn_training_log_<label>.jsonl)",
    )
    args = parser.parse_args()
    configure_stdout()

    if args.fresh:
        print("Archiving old checkpoints and training log (--fresh)...", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "reset_training.py")], check=True)

    m = _pick_map(args.map)
    cfg = _build_cfg(args)
    curve = str(Path(m["policy_path"]).parent / "learning_curve.png")
    train_log = training_log_path_for_label(args.label or None)
    train_log.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 60, flush=True)
    print("FlowGrid auto curriculum (CLI)", flush=True)
    print(f"  Map:              {m['display_name']} ({m['id']})", flush=True)
    print(f"  Policy:           {m['policy_path']}", flush=True)
    print(f"  Episodes / cycle: {cfg.episodes_per_cycle}", flush=True)
    print(f"  Max cycles:       {cfg.max_cycles}", flush=True)
    print(f"  Compare:          seed {cfg.compare_seed}, inject {cfg.compare_inject_seconds}s, gui={cfg.compare_gui}", flush=True)
    print(f"  Stop when:        all-vehicle wait >= baseline ({cfg.stop_when_all_improvement_pct}% threshold)", flush=True)
    print(f"  Log:              {CURRICULUM_LOG_PATH}", flush=True)
    if args.label:
        print(f"  Training log:     {train_log}", flush=True)
    print("=" * 60, flush=True)

    runner = JobRunner()
    job_id = runner.start_curriculum(
        m["sumocfg"],
        m["policy_path"],
        curve,
        map_id=m["id"],
        map_name=m["display_name"],
        checkpoint_every=max(1, args.checkpoint_every),
        curriculum=cfg,
        training_log_path=str(train_log),
    )

    last_cycle_count = 0
    last_train_ep = 0

    def on_message(msg: str, progress: float, result: dict) -> None:
        nonlocal last_cycle_count, last_train_ep
        pct = int(progress * 100)
        print(f"[{pct:3d}%] {msg}", flush=True)

        cycles = result.get("cycles") or []
        if len(cycles) > last_cycle_count:
            rec = cycles[-1]
            last_cycle_count = len(cycles)
            print("-" * 40, flush=True)
            print(f"  Cycle {rec.get('cycle')} summary: {rec.get('summary')}", flush=True)
            print(f"  All vehicles: {rec.get('improvement_all_pct'):+.1f}% vs baseline", flush=True)
            print(f"  Bus+emergency: {rec.get('improvement_priority_pct'):+.1f}%", flush=True)
            print(f"  Next: {rec.get('recommendation')}", flush=True)
            print("-" * 40, flush=True)
            last_train_ep = 0

        last_train = result.get("last_train") or {}
        ep_done = int(last_train.get("episodes_done", 0) or 0)
        if ep_done > last_train_ep and "Episode" in msg:
            last_train_ep = ep_done

    job = poll_job(runner, job_id, poll_s=0.4, on_message=on_message)

    print("=" * 60, flush=True)
    if not job:
        print("Job lost.", flush=True)
        sys.exit(1)
    if job.status == "failed":
        print(f"FAILED: {job.error}", flush=True)
        sys.exit(1)

    cycles = (job.result or {}).get("cycles") or []
    print(job.message or "Finished.", flush=True)
    print(f"Completed {len(cycles)} cycle(s).", flush=True)
    for line in curriculum_status_lines(min(10, len(cycles) or 1)):
        print(f"  {line}", flush=True)
    print(f"Full log: {CURRICULUM_LOG_PATH}", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    main()
