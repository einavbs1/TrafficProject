"""
Verify Top Checkpoints -- 5-seed confirmation for a short list of candidate
checkpoints (per PROJECT_HANDOFF.md SS11), instead of a full checkpoint sweep.

The V8 sweep (2 seeds: 42, 123) suggested a few mid-training checkpoints beat
the 6M final model on Low/Medium. This script:
  1. Reuses the ALREADY-COLLECTED seed 42/123 raw episodes for the candidates
     (from an existing sweep_raw.csv) -- no need to re-simulate them
     (fixed-timer and PPO-checkpoint results are deterministic per seed, see
     checkpoint_sweep.py notes).
  2. Runs ONLY the 3 missing seeds (default: 1337, 2026, 9999) for those
     candidates + the fixed timers, to reach the standard 5-seed set
     [42, 123, 1337, 2026, 9999].
  3. Merges both into one raw table and re-aggregates with sweep_aggregate.

Usage:
    cd PPO_Agent/scripts
    python verify_candidates.py --version-dir ..\\saved_agents\\V8 \\
        --candidates 2200000 2300000 3600000 6000000 \\
        --existing-raw ..\\saved_agents\\V8\\results\\checkpoint_sweep_20260702_135021\\sweep_raw.csv
"""
import os, sys, glob, shutil, argparse
from datetime import datetime


def _find_version_dir(argv):
    for i, a in enumerate(argv):
        if a == "--version-dir" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--version-dir="):
            return a.split("=", 1)[1]
    return None


# Path setup MUST happen at import time, same reasoning as checkpoint_sweep.py:
# ProcessPoolExecutor (spawn, on Windows) re-imports this module in workers.
_VDIR = _find_version_dir(sys.argv)
if _VDIR is None:
    sys.exit("usage: verify_candidates.py --version-dir <PPO_Agent, or Old_Versions/PPO/saved_agents/Vx> "
             "--candidates <steps...> [--existing-raw <sweep_raw.csv>] "
             "[--new-seeds 1337 2026 9999] [--workers 10]")
_VDIR = os.path.abspath(_VDIR)
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, _VDIR)

import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from evaluate_models import run_evaluation_task
from sweep_aggregate import SCENARIOS, FIXED_TIMERS, aggregate_and_plot

EST_MIN_PER_EPISODE = 2.5


def find_checkpoint(ckpt_dir, steps):
    zips = glob.glob(os.path.join(ckpt_dir, f"ppo_model_*_{steps}_steps.zip"))
    if len(zips) != 1:
        sys.exit(f"Expected exactly 1 checkpoint zip for {steps} steps in "
                  f"{ckpt_dir}, found: {zips}")
    zip_path = zips[0]
    pkl_path = zip_path[:-4].replace(f"_{steps}_steps", f"_vecnormalize_{steps}_steps") + ".pkl"
    if not os.path.exists(pkl_path):
        sys.exit(f"Missing matching vecnormalize stats: {pkl_path}")
    return zip_path, pkl_path


def stage_checkpoint(stage_root, steps, zip_path, pkl_path):
    d = os.path.join(stage_root, f"ck{steps}")
    os.makedirs(d, exist_ok=True)
    staged_zip = os.path.join(d, f"ppo_model_ck{steps}.zip")
    shutil.copy(zip_path, staged_zip)
    shutil.copy(pkl_path, os.path.join(d, f"vec_normalize_ck{steps}.pkl"))
    return staged_zip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-dir", required=True)
    parser.add_argument("--candidates", type=int, nargs="+", required=True,
                         help="Checkpoint step counts to verify, e.g. 2200000 2300000 3600000 6000000")
    parser.add_argument("--existing-raw", type=str, default=None,
                         help="Existing sweep_raw.csv to reuse seed 42/123 rows from (skips re-simulating them)")
    parser.add_argument("--new-seeds", type=int, nargs="+", default=[1337, 2026, 9999],
                         help="Seeds to run fresh (not already in --existing-raw)")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    version_dir  = os.path.abspath(args.version_dir)
    version_name = os.path.basename(version_dir.rstrip("\\/"))
    ckpt_dir     = os.path.join(version_dir, "checkpoints")

    checkpoints = {steps: find_checkpoint(ckpt_dir, steps) for steps in args.candidates}

    existing = pd.DataFrame()
    existing_seeds = []
    if args.existing_raw:
        existing = pd.read_csv(args.existing_raw)
        cand_models = {f"ck{s}" for s in args.candidates}
        keep_models = cand_models | {f"Fixed_{ct}s" for ct in FIXED_TIMERS}
        existing = existing[existing.model.isin(keep_models)]
        existing_seeds = sorted(existing.seed.unique().tolist())

    new_seeds = [s for s in args.new_seeds if s not in existing_seeds]
    n_episodes = (len(args.candidates) + len(FIXED_TIMERS)) * len(SCENARIOS) * len(new_seeds)
    eta_min = n_episodes * EST_MIN_PER_EPISODE / max(args.workers, 1)

    print(f"Version          : {version_name}")
    print(f"Candidates       : {args.candidates}")
    print(f"Reused from      : {args.existing_raw or '(none)'}  seeds={existing_seeds}")
    print(f"New seeds to run : {new_seeds}")
    print(f"Full seed set    : {sorted(set(existing_seeds) | set(new_seeds))}")
    print(f"New episodes     : {n_episodes}   estimated runtime: ~{eta_min:.0f} min ({args.workers} workers)")
    if args.dry_run:
        print("\n-- DRY RUN, nothing executed --")
        return
    if not new_seeds:
        print("Nothing new to run -- existing raw already covers all requested seeds.")
        raw = existing
    else:
        ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir   = os.path.join(version_dir, "results", f"verify_candidates_{ts}")
        stage_dir = os.path.join(out_dir, "stage")
        os.makedirs(stage_dir, exist_ok=True)

        tasks = []
        for steps, (zpath, pkl) in checkpoints.items():
            staged = stage_checkpoint(stage_dir, steps, zpath, pkl)
            for scen, route in SCENARIOS:
                for seed in new_seeds:
                    tasks.append((f"ck{steps}|{scen}", "ppo", route, seed, None, staged, False))
        for ct in FIXED_TIMERS:
            for scen, route in SCENARIOS:
                for seed in new_seeds:
                    tasks.append((f"Fixed_{ct}s|{scen}", "fixed", route, seed, ct, None, False))

        print(f"\nRunning {len(tasks)} episodes on {args.workers} workers ...", flush=True)
        rows = []
        done = 0
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_evaluation_task, t): t for t in tasks}
            for fut in as_completed(futures):
                label = futures[fut][0]
                try:
                    name, seed, df = fut.result()
                    model, scen = name.split("|")
                    rows.append({
                        "model": model, "scenario": scen, "seed": seed,
                        "total_wait": df["system_total_waiting_time"].sum(),
                        "arrived": df["total_arrived"].max(),
                        "switches": df["total_switches"].max(),
                    })
                    done += 1
                    if done % 10 == 0 or done == len(tasks):
                        print(f"  {done}/{len(tasks)} episodes done", flush=True)
                except Exception as exc:
                    print(f"  [ERROR] {label}: {exc}", flush=True)

        fresh = pd.DataFrame(rows)
        raw = pd.concat([existing, fresh], ignore_index=True) if len(existing) else fresh
        raw.to_csv(os.path.join(out_dir, "sweep_raw.csv"), index=False)
        shutil.rmtree(stage_dir, ignore_errors=True)

        full_seeds = sorted(raw.seed.unique().tolist())
        aggregate_and_plot(raw, out_dir, f"{version_name}_candidates", full_seeds)
        print(f"\nAll outputs -> {out_dir}")


if __name__ == "__main__":
    main()
