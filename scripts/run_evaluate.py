from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.eval.batch_evaluate import (
    RunRecord,
    batch_header,
    build_batch_report,
    episodes_label,
    run_batch,
)
from flowgrid.eval.evaluate import _compare_yaml
from flowgrid.maps.map_registry import DEFAULT_MAP_ID, list_maps_for_gui
from flowgrid.paths import LOGS_DIR
from flowgrid.util.labeled_paths import batch_eval_log_path_for_label
from flowgrid.rl.policy_checkpoint_io import read_checkpoint_training_episodes

from scripts.cli_poll import configure_stdout

configure_stdout()


def _pick_map(maps: list[dict], map_arg: str) -> dict:
    match = next(
        (item for item in maps if item["id"] == map_arg or item["display_name"] == map_arg),
        None,
    )
    if match is None:
        available = [item["id"] for item in maps]
        raise SystemExit(f"Map not found: {map_arg!r}. Available: {available}")
    return match


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch fair compare: fixed-time baseline vs DQN")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--map", type=str, default=DEFAULT_MAP_ID)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--inject-seconds", type=float, default=None)
    parser.add_argument("--baseline-green", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=None, help="Fixed seed for every run (default: random per run)")
    parser.add_argument("--gui", action="store_true", help="Open SUMO 3D for DQN replay only")
    parser.add_argument(
        "--phase-tracker",
        action="store_true",
        help="Print [PHASE_TRACKER] lines for baseline/DQN phase switches (debug)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Experiment label; appends to logs/batch_evaluation_<label>.log instead of default",
    )
    args = parser.parse_args()

    if args.runs < 1:
        raise SystemExit("--runs must be >= 1")

    maps = list_maps_for_gui()
    if not maps:
        raise SystemExit("No maps found.")
    map_info = _pick_map(maps, args.map)

    cmp = _compare_yaml()
    inject_seconds = float(
        args.inject_seconds if args.inject_seconds is not None else cmp.get("inject_seconds", 800)
    )

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    batch_log_path = batch_eval_log_path_for_label(args.label or None)
    model_episodes = read_checkpoint_training_episodes(map_info["policy_path"])

    if not args.quiet:
        print(
            f"Batch evaluate: {map_info['display_name']}  runs={args.runs}  "
            f"inject={inject_seconds:.0f}s  gui={bool(args.gui)}  log={batch_log_path}",
            flush=True,
        )
        print(f"Model Training Episodes: {episodes_label(model_episodes)}", flush=True)

    records: list[RunRecord] = run_batch(
        map_info,
        runs=args.runs,
        seed=args.seed,
        baseline_green=float(args.baseline_green),
        inject_seconds=inject_seconds,
        quiet=bool(args.quiet),
        gui=bool(args.gui),
        phase_tracker=bool(args.phase_tracker),
    )

    report = build_batch_report(
        records,
        batch_header(
            map_info,
            args.runs,
            inject_seconds,
            float(args.baseline_green),
            model_episodes,
            map_info["policy_path"],
            gui=bool(args.gui),
        ),
        model_episodes,
    )

    with batch_log_path.open("a", encoding="utf-8") as handle:
        handle.write(report)
        handle.write("\n")

    print(report, flush=True)

    ok_count = sum(1 for item in records if item.ok)
    if ok_count == 0:
        sys.exit(1)
    if ok_count < len(records):
        sys.exit(2)


if __name__ == "__main__":
    main()
