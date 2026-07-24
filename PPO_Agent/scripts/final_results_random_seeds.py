"""
Final Results -- one independently-random (seed, scenario) per checkpoint.

Instead of testing ONE model against a fixed, reused seed set (which a
skeptic could dismiss as "your favorite five seeds"), this evaluates EVERY
checkpoint of a version against its OWN freshly-drawn random seed and a
cycled scenario -- so no two rows share a traffic situation, and nothing is
hand-picked. Within a row the comparison is still fair: the PPO checkpoint
and all 3 fixed timers face the identical seeded SUMO traffic instance for
that row (fixed-timer results depend only on (seed, scenario), proven
elsewhere in this project's tooling).

This is deliberately NOT filtered to "good" checkpoints -- if a version has
genuine unstable/collapsed checkpoints, this shows that honestly rather than
hiding it. A checkpoint sweep already characterizes the full learning curve;
this artifact answers a different question: across many totally scattered,
never-reused random situations, how often does the agent actually win.

Crash-safe: the full (checkpoint, seed, scenario) plan is written to
assignments.csv BEFORE any episode runs, and each checkpoint's row is
appended to final_results.csv as soon as all 4 of its episodes (1 PPO + 3
fixed timers) complete -- not batched until the very end. If the process is
killed partway through, nothing already-finished is lost, and --resume
picks up exactly where it left off using the same original plan (not a
fresh random re-draw).

Outputs (into <version-dir>/results/final_random_seeds_<timestamp>/):
    assignments.csv       -- the full (steps, scenario, seed) plan, written
                              upfront, before any episode runs
    final_results.csv     -- one row per checkpoint, appended incrementally
                              as each checkpoint finishes: steps, scenario,
                              seed, ppo_wait, fixed_30/45/60s_wait,
                              pct_vs_30/45/60s, beats_all_fixed
    summary.txt           -- win-rate accounting, overall + per scenario,
                             plus an explicit list of every row that lost
    win_rate_scatter.png  -- pct_vs_60s per checkpoint, symlog y-axis so both
                             normal wins/losses and extreme collapses are
                             visible on one plot

Usage:
    cd PPO_Agent/scripts
    python final_results_random_seeds.py --version-dir ..\\saved_agents\\V8_replicate --dry-run
    python final_results_random_seeds.py --version-dir ..\\saved_agents\\V8_replicate

    # If a run was interrupted (crash, killed, etc.), continue it exactly
    # where it left off -- same checkpoints/seeds/scenarios already planned,
    # already-finished checkpoints are not re-run:
    python final_results_random_seeds.py --version-dir ..\\saved_agents\\V8_replicate ^
        --resume ..\\saved_agents\\V8_replicate\\results\\final_random_seeds_20260704_135633

    # Just regenerate summary.txt/win_rate_scatter.png from whatever rows
    # are in final_results.csv right now, without running anything:
    python final_results_random_seeds.py --version-dir ..\\saved_agents\\V8_replicate ^
        --summarize-only ..\\saved_agents\\V8_replicate\\results\\final_random_seeds_20260704_135633
"""
import os, re, sys, csv, glob, shutil, argparse, random
from datetime import datetime
from collections import Counter


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
    sys.exit("usage: final_results_random_seeds.py --version-dir <PPO_Agent, or Old_Versions/PPO/saved_agents/Vx> "
             "[--workers 10] [--dry-run] [--resume <out_dir>] [--summarize-only <out_dir>]")
_VDIR = os.path.abspath(_VDIR)
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, _VDIR)

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor, as_completed
from evaluate_models import run_evaluation_task
from sweep_aggregate import SCENARIOS, FIXED_TIMERS

EST_MIN_PER_EPISODE = 2.5
RESULTS_FIELDS = (["steps", "scenario", "seed", "ppo_wait"]
                  + [f"fixed_{ct}s_wait" for ct in FIXED_TIMERS]
                  + [f"pct_vs_{ct}s" for ct in FIXED_TIMERS]
                  + ["beats_all_fixed"])


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
        prefix = max(found, key=lambda b: len(found[b]))
        if len(found) > 1:
            print(f"NOTE: multiple runs in checkpoints/ -- using prefix '{prefix}' "
                  f"({len(found[prefix])} checkpoints).")
    result = []
    for steps, z in sorted(found[prefix]):
        pkl = os.path.join(os.path.dirname(z), f"{prefix}_vecnormalize_{steps}_steps.pkl")
        result.append((steps, z, pkl if os.path.exists(pkl) else None))
    return result


def stage_checkpoint(stage_root, steps, zip_path, pkl_path):
    d = os.path.join(stage_root, f"ck{steps}")
    os.makedirs(d, exist_ok=True)
    staged_zip = os.path.join(d, f"ppo_model_ck{steps}.zip")
    shutil.copy(zip_path, staged_zip)
    shutil.copy(pkl_path, os.path.join(d, f"vec_normalize_ck{steps}.pkl"))
    return staged_zip


def compute_row(steps, d):
    """d: {"scenario", "seed", "ppo_wait", "fixed_30s_wait", ...} for one checkpoint."""
    row = {"steps": steps, "scenario": d.get("scenario"), "seed": d.get("seed"),
           "ppo_wait": d.get("ppo_wait")}
    beats_all = True
    for ct in FIXED_TIMERS:
        fw = d.get(f"fixed_{ct}s_wait")
        pct = None
        if fw is not None and row["ppo_wait"] is not None:
            pct = round(100.0 * (fw - row["ppo_wait"]) / fw, 1)
        row[f"fixed_{ct}s_wait"] = fw
        row[f"pct_vs_{ct}s"] = pct
        if pct is None or pct <= 0:
            beats_all = False
    row["beats_all_fixed"] = beats_all
    return row


def write_summary_and_plot(out_dir, version_name):
    """Regenerate summary.txt + win_rate_scatter.png from whatever rows are
    currently in final_results.csv -- works whether the run fully finished
    or was interrupted partway through."""
    results_path = os.path.join(out_dir, "final_results.csv")
    if not os.path.exists(results_path):
        sys.exit(f"No final_results.csv in {out_dir} yet -- nothing to summarize.")
    final = pd.read_csv(results_path).sort_values("steps")

    lines = []
    total = len(final)
    win_all = int(final["beats_all_fixed"].sum())
    lines.append(f"Rows so far: {total}   "
                 f"({win_all}/{total} beat ALL 3 fixed timers, {100*win_all/max(total,1):.1f}%)")
    lines.append("")
    for scen, _ in SCENARIOS:
        sub = final[final.scenario == scen]
        if len(sub) == 0:
            continue
        lines.append(f"{scen} traffic ({len(sub)} random draws so far):")
        for ct in FIXED_TIMERS:
            wins = int((sub[f"pct_vs_{ct}s"] > 0).sum())
            lines.append(f"  vs Fixed_{ct}s: {wins}/{len(sub)} wins ({100*wins/len(sub):.1f}%)")

    losses = final[~final.beats_all_fixed]
    lines.append("")
    lines.append(f"{len(losses)}/{total} checkpoints (so far) lost to at least one fixed "
                 f"timer on their random draw (full list, nothing excluded):")
    for _, r in losses.iterrows():
        lines.append(f"  step {int(r.steps):>9,}  scenario={r.scenario:6s}  "
                      f"seed={int(r.seed)}  ppo_wait={r.ppo_wait:,.0f}  "
                      f"pct_vs_30/45/60s={r.pct_vs_30s}/{r.pct_vs_45s}/{r.pct_vs_60s}")

    summary_text = "\n".join(lines)
    print("\n" + summary_text)
    with open(os.path.join(out_dir, "summary.txt"), "w") as f:
        f.write(summary_text + "\n")

    fig, ax = plt.subplots(figsize=(14, 6))
    colors = {"Low": "tab:green", "Medium": "tab:orange", "High": "tab:red"}
    for scen, _ in SCENARIOS:
        sub = final[final.scenario == scen]
        if len(sub) == 0:
            continue
        ax.scatter(sub.steps / 1e6, sub.pct_vs_60s, s=20, color=colors[scen],
                   label=scen, alpha=0.7)
    ax.axhline(0, color="black", lw=1)
    ax.set_yscale("symlog", linthresh=100)
    ax.set_xlabel("Checkpoint training steps (millions)")
    ax.set_ylabel("% improvement vs Fixed_60s (symlog; that row's own random seed)")
    ax.set_title(f"{version_name} -- one random (seed, scenario) per checkpoint, "
                 f"nothing cherry-picked or filtered ({total} rows so far)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "win_rate_scatter.png"), dpi=130)
    print(f"\nsummary.txt + win_rate_scatter.png refreshed -> {out_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-dir", required=True)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--prefix", type=str, default=None)
    parser.add_argument("--seed-min", type=int, default=1)
    parser.add_argument("--seed-max", type=int, default=1_000_000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", type=str, default=None,
                        help="Existing final_random_seeds_<ts> dir to continue -- reuses its "
                             "assignments.csv plan (same checkpoints/seeds/scenarios, not a "
                             "fresh random draw) and skips checkpoints already present in "
                             "final_results.csv.")
    parser.add_argument("--summarize-only", type=str, default=None,
                         help="Just regenerate summary.txt/win_rate_scatter.png from whatever "
                              "rows are currently in this dir's final_results.csv, run nothing.")
    args = parser.parse_args()

    version_dir  = os.path.abspath(args.version_dir)
    version_name = os.path.basename(version_dir.rstrip("\\/"))

    if args.summarize_only:
        write_summary_and_plot(os.path.abspath(args.summarize_only), version_name)
        return

    scen_route = dict(SCENARIOS)

    if args.resume:
        out_dir = os.path.abspath(args.resume)
        plan_path = os.path.join(out_dir, "assignments.csv")
        if not os.path.exists(plan_path):
            sys.exit(f"--resume dir has no assignments.csv (nothing to resume from): {out_dir}")
        plan = pd.read_csv(plan_path)

        ckpts = discover_checkpoints(version_dir, args.prefix)
        ckpt_by_steps = {s: (z, p) for s, z, p in ckpts}

        results_path = os.path.join(out_dir, "final_results.csv")
        done_steps = set()
        if os.path.exists(results_path):
            done_steps = set(pd.read_csv(results_path)["steps"].tolist())

        assignments = []
        for _, r in plan.iterrows():
            steps = int(r["steps"])
            if steps in done_steps or steps not in ckpt_by_steps:
                continue
            z, p = ckpt_by_steps[steps]
            if p is None:
                continue
            assignments.append(((steps, z, p), (r["scenario"], scen_route[r["scenario"]]),
                                 int(r["seed"])))
        print(f"Resuming {out_dir}")
        print(f"  already done: {len(done_steps)}   remaining: {len(assignments)}")
    else:
        ckpts = discover_checkpoints(version_dir, args.prefix)
        usable  = [(s, z, p) for s, z, p in ckpts if p is not None]
        skipped = [s for s, z, p in ckpts if p is None]
        n = len(usable)
        if n == 0:
            sys.exit("Nothing to evaluate.")

        # Deterministic even scenario cycling: Low -> Medium -> High -> Low -> ...
        scenario_cycle = [SCENARIOS[i % len(SCENARIOS)] for i in range(n)]

        # Independently-random, non-repeating seeds -- not meta-seeded, so a
        # re-run draws a genuinely fresh set. Recorded in assignments.csv so
        # a later --resume reuses this exact plan rather than re-drawing.
        seed_pool_size = args.seed_max - args.seed_min + 1
        if seed_pool_size < n:
            sys.exit(f"--seed-min/--seed-max range ({seed_pool_size}) smaller than "
                      f"checkpoint count ({n}); widen the range.")
        drawn_seeds = random.sample(range(args.seed_min, args.seed_max + 1), n)
        assignments = list(zip(usable, scenario_cycle, drawn_seeds))
        print(f"Checkpoints usable: {n}   skipped (no vecnormalize stats): {len(skipped)}")

    scen_counts = Counter(scen for _, (scen, _), _ in assignments)
    n_episodes = len(assignments) * (1 + len(FIXED_TIMERS))
    eta_min = n_episodes * EST_MIN_PER_EPISODE / max(args.workers, 1)

    print(f"Version   : {version_name}")
    print(f"Scenario coverage (this run) : {dict(scen_counts)}")
    print(f"Episodes  : {n_episodes}   estimated runtime: ~{eta_min:.0f} min "
          f"({args.workers} workers)")
    if args.dry_run:
        print("\n-- DRY RUN, nothing executed -- first 20 assignments --")
        for (steps, z, p), (scen, route), seed in assignments[:20]:
            print(f"  {steps:>9,} steps  scenario={scen:6s}  seed={seed}")
        print("  ...")
        return
    if not assignments:
        print("Nothing left to run -- already fully done.")
        write_summary_and_plot(out_dir if args.resume else out_dir, version_name)
        return

    if not args.resume:
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(version_dir, "results", f"final_random_seeds_{ts}")
        os.makedirs(out_dir, exist_ok=True)
        # Write the full plan upfront, before any episode runs, so a crash
        # can still be resumed with the exact same (checkpoint, seed,
        # scenario) assignments -- not a fresh random re-draw.
        plan_rows = [{"steps": s, "scenario": scen, "seed": seed}
                     for (s, z, p), (scen, route), seed in assignments]
        pd.DataFrame(plan_rows).to_csv(os.path.join(out_dir, "assignments.csv"), index=False)

    stage_dir = os.path.join(out_dir, "stage")
    os.makedirs(stage_dir, exist_ok=True)

    tasks = []
    task_meta = {}  # label -> (steps, scenario, seed)
    for (steps, zpath, pkl), (scen, route), seed in assignments:
        staged = stage_checkpoint(stage_dir, steps, zpath, pkl)
        label_ppo = f"ck{steps}|ppo"
        tasks.append((label_ppo, "ppo", route, seed, None, staged, False))
        task_meta[label_ppo] = (steps, scen, seed)
        for ct in FIXED_TIMERS:
            label_fixed = f"ck{steps}|fixed{ct}"
            tasks.append((label_fixed, "fixed", route, seed, ct, None, False))
            task_meta[label_fixed] = (steps, scen, seed)

    # Crash-safe incremental writer: append a checkpoint's row to
    # final_results.csv the moment all 4 of its episodes are in, instead of
    # holding everything in memory until the very end.
    results_path = os.path.join(out_dir, "final_results.csv")
    header_needed = not os.path.exists(results_path)
    csv_file = open(results_path, "a", newline="")
    csv_writer = csv.DictWriter(csv_file, fieldnames=RESULTS_FIELDS)
    if header_needed:
        csv_writer.writeheader()
        csv_file.flush()

    print(f"\nRunning {len(tasks)} episodes on {args.workers} workers ...", flush=True)
    pending = {}   # steps -> partial dict, until all 4 of its episodes are in
    done = 0
    rows_written = 0
    try:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(run_evaluation_task, t): t for t in tasks}
            for fut in as_completed(futures):
                label = futures[fut][0]
                try:
                    name, seed, df = fut.result()
                    steps, scen, seed_meta = task_meta[name]
                    total_wait = df["system_total_waiting_time"].sum()
                    d = pending.setdefault(steps, {"scenario": scen, "seed": seed_meta})
                    if name.endswith("|ppo"):
                        d["ppo_wait"] = total_wait
                    else:
                        ct = int(name.split("fixed")[1])
                        d[f"fixed_{ct}s_wait"] = total_wait

                    expected_keys = {"ppo_wait"} | {f"fixed_{ct}s_wait" for ct in FIXED_TIMERS}
                    if expected_keys.issubset(d.keys()):
                        row = compute_row(steps, d)
                        csv_writer.writerow(row)
                        csv_file.flush()
                        rows_written += 1
                        del pending[steps]
                except Exception as exc:
                    print(f"  [ERROR] {label}: {exc}", flush=True)
                done += 1
                if done % 20 == 0 or done == len(tasks):
                    print(f"  {done}/{len(tasks)} episodes done   "
                          f"({rows_written} checkpoint rows written so far)", flush=True)
    finally:
        csv_file.close()

    if pending:
        print(f"\nNOTE: {len(pending)} checkpoint(s) had partial results (some but not all of "
              f"their 4 episodes finished) and were NOT written -- rerun with --resume {out_dir} "
              f"to pick them back up.")

    write_summary_and_plot(out_dir, version_name)
    shutil.rmtree(stage_dir, ignore_errors=True)
    print(f"\nAll outputs -> {out_dir}")


if __name__ == "__main__":
    main()
