"""Run one checkpoint batch eval in an isolated process (safe during training)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.eval.batch_evaluate import checkpoint_progress_line, run_checkpoint_batch
from flowgrid.eval.evaluate import _compare_yaml
from flowgrid.maps.map_registry import DEFAULT_MAP_ID, list_maps_for_gui
from flowgrid.util.labeled_paths import checkpoint_eval_log_path_for_label

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
    parser = argparse.ArgumentParser(description="Evaluate one training checkpoint (subprocess-safe)")
    parser.add_argument("--map", default=DEFAULT_MAP_ID)
    parser.add_argument("--checkpoint-episode", type=int, required=True)
    parser.add_argument("--eval-runs", type=int, default=10)
    parser.add_argument("--eval-seed", type=int, default=42)
    parser.add_argument(
        "--eval-quiet",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--inject-seconds", type=float, default=None)
    parser.add_argument("--baseline-green", type=float, default=60.0)
    parser.add_argument("--label", type=str, default="")
    args = parser.parse_args()

    if args.eval_runs < 1:
        raise SystemExit("--eval-runs must be >= 1")

    maps = list_maps_for_gui()
    if not maps:
        raise SystemExit("No maps found.")
    map_info = _pick_map(maps, args.map)

    cmp = _compare_yaml()
    inject_seconds = float(
        args.inject_seconds if args.inject_seconds is not None else cmp.get("inject_seconds", 800)
    )
    eval_log = checkpoint_eval_log_path_for_label(args.label or None)
    eval_log.parent.mkdir(parents=True, exist_ok=True)

    records, report = run_checkpoint_batch(
        map_info,
        runs=args.eval_runs,
        seed=args.eval_seed,
        baseline_green=float(args.baseline_green),
        inject_seconds=inject_seconds,
        checkpoint_episode=args.checkpoint_episode,
        quiet=bool(args.eval_quiet),
    )
    with eval_log.open("a", encoding="utf-8") as handle:
        handle.write(report)
        handle.write("\n")

    progress = checkpoint_progress_line(records, args.checkpoint_episode)
    print(progress, flush=True)
    print(f"  Logged to {eval_log}", flush=True)


if __name__ == "__main__":
    main()
