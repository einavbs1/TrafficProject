"""Fair baseline vs DQN compare from the terminal (no GUI)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.jobs.job_runner import JobRunner
from flowgrid.maps.map_registry import list_maps_for_gui
from flowgrid.eval.evaluate import _compare_yaml
from flowgrid.rl.compare_guard import print_compare_summary

from scripts.cli_poll import configure_stdout, poll_job

configure_stdout()

from flowgrid.maps.map_registry import DEFAULT_MAP_ID

DEFAULT_MAP = DEFAULT_MAP_ID


def main():
    parser = argparse.ArgumentParser(description="FlowGrid fair compare (baseline then DQN)")
    parser.add_argument("--map", default=DEFAULT_MAP)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--inject-seconds", type=float, default=None)
    parser.add_argument("--baseline-green", type=float, default=60.0)
    parser.add_argument("--gui", action="store_true", help="Open SUMO 3D")
    parser.add_argument("--delay", type=int, default=0, help="SUMO gui delay ms")
    args = parser.parse_args()
    configure_stdout()

    maps = list_maps_for_gui()
    m = next((x for x in maps if x["id"] == args.map or x["display_name"] == args.map), None)
    if not m:
        raise SystemExit(f"Map not found: {args.map}")

    cmp = _compare_yaml()
    inject = float(args.inject_seconds if args.inject_seconds is not None else cmp.get("inject_seconds", 800))

    print(f"Compare {m['display_name']} seed={args.seed} inject={inject}s gui={args.gui}", flush=True)
    runner = JobRunner()
    job_id = runner.start_compare(
        m["sumocfg"],
        float(args.baseline_green),
        seed=int(args.seed),
        policy_path=m["policy_path"],
        gui=bool(args.gui),
        gui_delay=int(args.delay),
        map_id=m["id"],
        map_name=m["display_name"],
        inject_seconds=inject,
    )

    def on_message(msg: str, progress: float, result: dict) -> None:
        pct = int(progress * 100)
        print(f"[{pct:3d}%] {msg}", flush=True)

    job = poll_job(runner, job_id, poll_s=0.5, on_message=on_message)
    if not job or job.status == "failed":
        print(f"FAILED: {job.error if job else 'unknown'}", flush=True)
        sys.exit(1)

    r = job.result or {}
    r["fixed_wait_priority"] = r.get("baseline_wait", 0)
    r["dqn_wait_priority"] = r.get("dqn_wait", 0)
    print_compare_summary(r)
    print("Saved to Reports / comparison_history.json", flush=True)
    if r.get("compare_invalid"):
        sys.exit(2)


if __name__ == "__main__":
    main()
