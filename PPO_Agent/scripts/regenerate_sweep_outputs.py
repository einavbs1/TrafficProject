"""
Regenerate checkpoint-sweep CSVs/PNGs from an already-collected sweep_raw.csv,
without re-running any SUMO simulation.

Why this is safe: for a fixed seed, SUMO's route <flow> generation is seeded
deterministically and does not depend on which controller (PPO checkpoint or
a fixed timer) drives the traffic light. So Fixed_30s/45s/60s results only
depend on (seed, scenario), never on the checkpoint -- re-simulating them
would reproduce bit-identical numbers (verified empirically: same seed run
twice, and the same seed re-run in a fresh process on a different day, both
gave identical total_wait/switches/arrived and identical per-step
trajectories). So this script just re-aggregates the existing raw episode
data with the corrected pairing/columns from checkpoint_sweep.py.

Usage:
    cd PPO_Agent/scripts
    python regenerate_sweep_outputs.py --sweep-dir ..\\results\\checkpoint_sweep_20260702_135021 --version-name V8
"""
import os
import sys
import argparse
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_aggregate import aggregate_and_plot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep-dir", required=True,
                         help="Existing checkpoint_sweep_<ts> folder containing sweep_raw.csv")
    parser.add_argument("--version-name", required=True)
    args = parser.parse_args()

    sweep_dir = os.path.abspath(args.sweep_dir)
    raw_path = os.path.join(sweep_dir, "sweep_raw.csv")
    if not os.path.exists(raw_path):
        sys.exit(f"No sweep_raw.csv found in {sweep_dir}")

    raw = pd.read_csv(raw_path)
    seeds = sorted(raw.seed.unique().tolist())
    print(f"Loaded {len(raw)} rows from {raw_path}")
    print(f"Seeds found in raw data: {seeds}")

    aggregate_and_plot(raw, sweep_dir, args.version_name, seeds)
    print(f"\nRegenerated outputs in-place -> {sweep_dir}")


if __name__ == "__main__":
    main()
