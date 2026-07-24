"""
Checkpoint Sweep -- learning-curve analysis for one agent version.

Evaluates EVERY saved checkpoint (model + matching vecnormalize stats) of a
chosen version on all 3 traffic scenarios, so we can see how performance
evolved with training steps and how many steps were actually needed.

Outputs (into <version-dir>/results/checkpoint_sweep_<timestamp>/):
    sweep_raw.csv        -- one row per (checkpoint or fixed timer) x scenario x seed
    sweep_raw_paired.csv -- one row per checkpoint x scenario x seed, with PPO wait
                            AND all 3 fixed-timer waits from that SAME seed side by
                            side (the exact paired comparison: same seed -> same
                            SUMO-generated vehicle stream for every controller)
    sweep_table.csv      -- per checkpoint x scenario: mean wait, mean fixed-timer
                            waits, and % improvement vs Fixed_30s/45s/60s (paired)
    sweep_curve.png      -- 3-panel learning curve (log y) with fixed-timer lines
    pct_curve.png        -- % improvement vs Fixed_60s over training steps
    best_checkpoints     -- printed top-5 table by mean improvement vs Fixed_60s

Usage:
    cd PPO_Agent/scripts
    python checkpoint_sweep.py --version-dir ..\\saved_agents\\V8 --seeds 42 123
    python checkpoint_sweep.py --version-dir ..\\saved_agents\\V8 --dry-run

Notes:
    - Checkpoints without a matching vecnormalize .pkl are SKIPPED (evaluating
      them raw would mismatch training-time observation scaling). Only V8+
      runs save stats with every checkpoint.
    - Baselines are evaluated with the SAME seeds so % improvements are paired:
      for a given seed, SUMO generates the identical vehicle stream (same cars,
      same lanes, same arrival times) regardless of which controller drives the
      light, since flows are seeded RNG, not fixed. That means Fixed_30/45/60
      results depend only on (seed, scenario) -- never on the checkpoint -- so
      they're simulated ONCE per seed and reused for every checkpoint's row
      (re-running them per checkpoint would replay the same seed and produce
      bit-identical numbers, just 15x slower).
    - Do not run while a training job is using the CPU cores.
"""
import os, re, sys, glob, shutil, argparse
from datetime import datetime


def _find_version_dir(argv):
    for i, a in enumerate(argv):
        if a == "--version-dir" and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith("--version-dir="):
            return a.split("=", 1)[1]
    return None


# Path setup MUST happen at import time (before evaluate_models) and also runs
# in ProcessPoolExecutor child processes, which re-import this module on spawn.
_VDIR = _find_version_dir(sys.argv)
if _VDIR is None:
    sys.exit("usage: checkpoint_sweep.py --version-dir <PPO_Agent, or Old_Versions/PPO/saved_agents/Vx> "
             "[--seeds 42 123] [--workers 10] [--dry-run]")
_VDIR = os.path.abspath(_VDIR)
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, _VDIR)   # version shim (sumo_rl_env.py) must win the import

import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from evaluate_models import run_evaluation_task  # imports version env via shim
from sweep_aggregate import SCENARIOS, FIXED_TIMERS, aggregate_and_plot

EST_MIN_PER_EPISODE = 2.5


def discover_checkpoints(version_dir, prefix=None):
    """Return sorted [(steps, zip_path, pkl_path_or_None), ...] for one run prefix."""
    ckpt_dir = os.path.join(version_dir, "checkpoints")
    found = {}
    for z in glob.glob(os.path.join(ckpt_dir, "ppo_model_*_steps.zip")):
        m = re.search(r"^(ppo_model_.+)_(\d+)_steps\.zip$", os.path.basename(z))
        if not m:
            continue
        base, steps = m.group(1), int(m.group(2))
        found.setdefault(base, []).append((steps, z))
    if not found:
        sys.exit(f"No checkpoints found in {ckpt_dir}")
    if prefix is None:
        prefix = max(found, key=lambda b: len(found[b]))  # run with most checkpoints
        if len(found) > 1:
            print(f"NOTE: multiple runs in checkpoints/ -- using prefix '{prefix}' "
                  f"({len(found[prefix])} checkpoints). Others: "
                  f"{ {b: len(v) for b, v in found.items() if b != prefix} }")
    result = []
    for steps, z in sorted(found[prefix]):
        pkl = os.path.join(os.path.dirname(z), f"{prefix}_vecnormalize_{steps}_steps.pkl")
        result.append((steps, z, pkl if os.path.exists(pkl) else None))
    return result


def stage_checkpoint(stage_root, steps, zip_path, pkl_path):
    """Copy checkpoint into a dir layout evaluate_models' stats-lookup understands."""
    d = os.path.join(stage_root, f"ck{steps}")
    os.makedirs(d, exist_ok=True)
    staged_zip = os.path.join(d, f"ppo_model_ck{steps}.zip")
    shutil.copy(zip_path, staged_zip)
    shutil.copy(pkl_path, os.path.join(d, f"vec_normalize_ck{steps}.pkl"))
    return staged_zip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-dir", required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 123])
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--prefix", type=str, default=None,
                        help="Checkpoint filename prefix if the folder holds several runs")
    parser.add_argument("--stride", type=int, default=1,
                        help="Evaluate every Nth checkpoint (1 = all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List checkpoints and ETA, run nothing")
    parser.add_argument("--reuse-fixed-timers", type=str, default=None,
                        help="Existing sweep_raw.csv to reuse Fixed_30/45/60s rows from, for "
                             "seeds already covered there. Fixed-timer results depend only on "
                             "(seed, scenario), never on which agent/version is being compared "
                             "-- same net file, same route files -- so re-simulating a seed we "
                             "already have is pure waste. Any seed NOT fully covered (all 3 "
                             "scenarios x all 3 timers present) is still run fresh.")
    args = parser.parse_args()

    version_dir  = os.path.abspath(args.version_dir)
    version_name = os.path.basename(version_dir.rstrip("\\/"))
    ckpts = discover_checkpoints(version_dir, args.prefix)[::args.stride]

    usable  = [(s, z, p) for s, z, p in ckpts if p is not None]
    skipped = [s for s, z, p in ckpts if p is None]

    reused_fixed_rows = []
    seeds_to_run_fixed = list(args.seeds)
    if args.reuse_fixed_timers:
        prior = pd.read_csv(args.reuse_fixed_timers)
        prior_fixed = prior[prior.model.str.startswith("Fixed_")]
        have_combos = set(zip(prior_fixed.model, prior_fixed.scenario, prior_fixed.seed))
        needed_models = [f"Fixed_{ct}s" for ct in FIXED_TIMERS]
        covered_seeds = [
            s for s in args.seeds
            if all((m, scen, s) in have_combos for m in needed_models for scen, _ in SCENARIOS)
        ]
        if covered_seeds:
            reused_fixed_rows = (
                prior_fixed[prior_fixed.seed.isin(covered_seeds)]
                [["model", "scenario", "seed", "total_wait", "arrived", "switches"]]
                .to_dict("records")
            )
            seeds_to_run_fixed = [s for s in args.seeds if s not in covered_seeds]
            print(f"Reusing fixed-timer results for seeds {covered_seeds} from "
                  f"{args.reuse_fixed_timers} ({len(reused_fixed_rows)} rows) -- "
                  f"not re-simulating them.")
            if seeds_to_run_fixed:
                print(f"Seeds not covered by reuse file, running fixed timers fresh for: "
                      f"{seeds_to_run_fixed}")

    n_fixed_episodes = len(FIXED_TIMERS) * len(SCENARIOS) * len(seeds_to_run_fixed)
    n_episodes = len(usable) * len(SCENARIOS) * len(args.seeds) + n_fixed_episodes
    eta_min = n_episodes * EST_MIN_PER_EPISODE / max(args.workers, 1)

    print(f"Version   : {version_name}")
    print(f"Checkpoints usable: {len(usable)}   skipped (no vecnormalize stats): {len(skipped)}")
    if skipped:
        print(f"  skipped steps: {skipped}")
    print(f"Seeds     : {args.seeds}")
    print(f"Episodes  : {n_episodes}   estimated runtime: ~{eta_min:.0f} min "
          f"({args.workers} workers)")
    if args.dry_run:
        print("\n-- DRY RUN, nothing executed --")
        for s, z, p in usable:
            print(f"  {s:>9,} steps  {os.path.basename(z)}")
        return
    if not usable:
        sys.exit("Nothing to evaluate.")

    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir   = os.path.join(version_dir, "results", f"checkpoint_sweep_{ts}")
    stage_dir = os.path.join(out_dir, "stage")
    os.makedirs(stage_dir, exist_ok=True)

    # Task label encodes checkpoint + scenario:  "ck<steps>|<scenario>"
    tasks = []
    for steps, zpath, pkl in usable:
        staged = stage_checkpoint(stage_dir, steps, zpath, pkl)
        for scen, route in SCENARIOS:
            for seed in args.seeds:
                tasks.append((f"ck{steps}|{scen}", "ppo", route, seed, None, staged, False))
    for ct in FIXED_TIMERS:
        for scen, route in SCENARIOS:
            for seed in seeds_to_run_fixed:
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

    rows.extend(reused_fixed_rows)
    raw = pd.DataFrame(rows)
    raw.to_csv(os.path.join(out_dir, "sweep_raw.csv"), index=False)

    aggregate_and_plot(raw, out_dir, version_name, args.seeds)
    shutil.rmtree(stage_dir, ignore_errors=True)
    print(f"\nAll outputs -> {out_dir}")


if __name__ == "__main__":
    main()
