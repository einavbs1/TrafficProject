"""
Shared aggregation/plotting logic for checkpoint sweeps. No argv-dependent
import-time code (unlike checkpoint_sweep.py, which needs sys.argv to locate
the version dir before importing evaluate_models) -- safe to import from
both a live sweep run and a from-cached-data regenerate script.
"""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCENARIOS = [
    ("Low",    r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml"),
    ("Medium", r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_hard.rou.xml"),
    ("High",   r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_extreme.rou.xml"),
]
FIXED_TIMERS = [30, 45, 60]


def aggregate_and_plot(raw, out_dir, version_name, seeds):
    """Build sweep_raw_paired.csv, sweep_table.csv, best_checkpoints.csv, and
    both PNGs from a raw per-episode DataFrame (columns: model, scenario, seed,
    total_wait, ...). Used both for a live sweep run and for regenerating
    outputs from a previously-collected sweep_raw.csv (fixed-timer results are
    deterministic per seed, so re-simulating them is unnecessary -- verified
    empirically: identical seed rerun in a fresh process reproduces bit-
    identical total_wait/switches/arrived and full per-step trajectory)."""
    # -- Per-seed paired table: one row per (checkpoint, scenario, seed) with
    #    PPO wait + all 3 baseline waits from THAT SAME seed side by side.
    #    Baselines depend only on (seed, scenario) -- never on the checkpoint --
    #    since the SUMO route flow for a given seed is generated identically
    #    regardless of which controller drives the traffic light. So the same
    #    per-seed baseline value is looked up (not re-simulated) for every
    #    checkpoint row; it is the true paired result for that seed, not a stale
    #    placeholder.
    base_by_seed = {}
    for ct in FIXED_TIMERS:
        sub = raw[raw.model == f"Fixed_{ct}s"]
        for _, r in sub.iterrows():
            base_by_seed[(r.scenario, r.seed, ct)] = r.total_wait

    ck_raw = raw[raw.model.str.startswith("ck")].copy()
    ck_raw["steps"] = ck_raw.model.str.replace("ck", "", regex=False).astype(int)
    paired_rows = []
    for _, r in ck_raw.iterrows():
        row = {
            "steps": r.steps, "scenario": r.scenario, "seed": r.seed,
            "ppo_wait": r.total_wait,
        }
        for ct in FIXED_TIMERS:
            fixed_wait = base_by_seed[(r.scenario, r.seed, ct)]
            row[f"fixed_{ct}s_wait"] = fixed_wait
            row[f"pct_vs_{ct}s"] = round(
                100.0 * (fixed_wait - r.total_wait) / fixed_wait, 1)
        paired_rows.append(row)
    paired = pd.DataFrame(paired_rows).sort_values(["scenario", "steps", "seed"])
    paired.to_csv(os.path.join(out_dir, "sweep_raw_paired.csv"), index=False)

    # -- Aggregate: mean over seeds (paired, per checkpoint x scenario) ------
    mean_wait = (raw.groupby(["model", "scenario"])["total_wait"]
                    .mean().reset_index())
    base = {(f"Fixed_{ct}s", scen): float(
                mean_wait[(mean_wait.model == f"Fixed_{ct}s")
                          & (mean_wait.scenario == scen)].total_wait.iloc[0])
            for ct in FIXED_TIMERS for scen, _ in SCENARIOS}

    ck = mean_wait[mean_wait.model.str.startswith("ck")].copy()
    ck["steps"] = ck.model.str.replace("ck", "", regex=False).astype(int)
    for ct in FIXED_TIMERS:
        ck[f"fixed_{ct}s_wait"] = ck.scenario.map(
            lambda scen, ct=ct: base[(f"Fixed_{ct}s", scen)])
        ck[f"pct_vs_{ct}s"] = ck.apply(
            lambda r: 100.0 * (base[(f"Fixed_{ct}s", r.scenario)] - r.total_wait)
                      / base[(f"Fixed_{ct}s", r.scenario)], axis=1).round(1)
    ck = ck.sort_values(["scenario", "steps"])
    table = ck[["steps", "scenario", "total_wait",
                "fixed_30s_wait", "pct_vs_30s",
                "fixed_45s_wait", "pct_vs_45s",
                "fixed_60s_wait", "pct_vs_60s"]]
    table.to_csv(os.path.join(out_dir, "sweep_table.csv"), index=False)

    # -- Improvement table (what the user reads) -----------------------------
    print(f"\n===== {version_name} CHECKPOINT SWEEP -- % improvement vs fixed timers "
          f"(positive = agent better) =====")
    for scen, _ in SCENARIOS:
        sub = table[table.scenario == scen]
        print(f"\n--- {scen} traffic ---   (Fixed_30s={base[('Fixed_30s', scen)]:,.0f}  "
              f"Fixed_45s={base[('Fixed_45s', scen)]:,.0f}  "
              f"Fixed_60s={base[('Fixed_60s', scen)]:,.0f})")
        print(sub.to_string(index=False,
              formatters={"total_wait": lambda v: f"{v:,.0f}"}))

    # -- Best checkpoints by mean improvement vs Fixed_60s across scenarios --
    pivot = ck.pivot_table(index="steps", columns="scenario",
                           values="pct_vs_60s").reset_index()
    pivot["mean_pct_vs_60s"] = pivot[[s for s, _ in SCENARIOS]].mean(axis=1).round(1)
    best = pivot.sort_values("mean_pct_vs_60s", ascending=False).head(5)
    print("\n===== TOP 5 CHECKPOINTS (mean % improvement vs Fixed_60s across scenarios) =====")
    print(best.to_string(index=False))
    pivot.to_csv(os.path.join(out_dir, "best_checkpoints.csv"), index=False)

    # -- Learning-curve plot ---------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))
    for ax, (scen, _) in zip(axes, SCENARIOS):
        sub = ck[ck.scenario == scen]
        ax.plot(sub.steps / 1e6, sub.total_wait, "o-", lw=1.5, ms=4,
                color="tab:blue", label=version_name)
        styles = {30: ":", 45: "-.", 60: "--"}
        for ct in FIXED_TIMERS:
            ax.axhline(base[(f"Fixed_{ct}s", scen)], ls=styles[ct],
                       color="gray", lw=1.2, label=f"Fixed_{ct}s")
        ax.set_yscale("log")
        ax.set_title(f"{scen} traffic")
        ax.set_xlabel("Training steps (millions)")
        ax.set_ylabel("Total wait time (s, log)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle(f"{version_name} learning curve -- total wait vs training steps "
                 f"(seeds {seeds})")
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "sweep_curve.png"), dpi=130)

    # -- % improvement plot ----------------------------------------------------
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    colors = {"Low": "tab:green", "Medium": "tab:orange", "High": "tab:red"}
    for scen, _ in SCENARIOS:
        sub = ck[ck.scenario == scen]
        ax2.plot(sub.steps / 1e6, sub.pct_vs_60s, "o-", lw=1.5, ms=4,
                 color=colors[scen], label=f"{scen} traffic")
    ax2.axhline(0, color="black", lw=1)
    ax2.set_xlabel("Training steps (millions)")
    ax2.set_ylabel("% improvement vs Fixed_60s (positive = agent wins)")
    ax2.set_title(f"{version_name} -- when did the agent beat the strongest baseline?")
    ax2.grid(alpha=0.3)
    ax2.legend()
    fig2.tight_layout()
    fig2.savefig(os.path.join(out_dir, "pct_curve.png"), dpi=130)
