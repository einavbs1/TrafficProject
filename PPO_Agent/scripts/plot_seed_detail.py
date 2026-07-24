"""
Per-seed detail plot -- shows WHY the fixed-timer lines in sweep_curve.png are
perfectly flat: Fixed_30/45/60s results depend only on (seed, scenario), never
on the PPO checkpoint's training step, since a fixed timer doesn't train. So
there is structurally no "shape" over the training-steps x-axis for them --
only a height. What sweep_curve.png hides is that this height differs per
seed (different generated traffic per seed). This script draws each seed's
line separately (thin, semi-transparent) behind the bold mean line, for BOTH
the PPO agent and the 3 fixed timers, so the real seed-to-seed spread is
visible instead of being collapsed into one averaged number.

Usage:
    cd PPO_Agent/scripts
    python plot_seed_detail.py --paired-csv ..\\results\\checkpoint_sweep_20260702_135021\\sweep_raw_paired.csv --version-name V8
"""
import os
import sys
import argparse
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_aggregate import SCENARIOS, FIXED_TIMERS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paired-csv", required=True,
                         help="A sweep_raw_paired.csv produced by checkpoint_sweep.py / verify_candidates.py")
    parser.add_argument("--version-name", default="V8")
    parser.add_argument("--out-dir", default=None,
                         help="Defaults to the folder containing --paired-csv")
    args = parser.parse_args()

    df = pd.read_csv(args.paired_csv)
    out_dir = args.out_dir or os.path.dirname(os.path.abspath(args.paired_csv))
    seeds = sorted(df.seed.unique().tolist())
    print(f"Seeds in file: {seeds}  ({len(seeds)} total)")

    cmap = plt.get_cmap("tab10" if len(seeds) <= 10 else "tab20")
    seed_color = {s: cmap(i % cmap.N) for i, s in enumerate(seeds)}
    fixed_styles = {30: ":", 45: "-.", 60: "--"}

    fig, axes = plt.subplots(1, 3, figsize=(19, 6))
    for ax, (scen, _) in zip(axes, SCENARIOS):
        sub = df[df.scenario == scen].sort_values("steps")
        is_first_panel = (scen == SCENARIOS[0][0])

        # -- PPO: thin per-seed lines (real variance across training steps) --
        for seed in seeds:
            s = sub[sub.seed == seed]
            ax.plot(s.steps / 1e6, s.ppo_wait, "-", lw=0.9, alpha=0.5,
                     color=seed_color[seed],
                     label=f"seed {seed}" if is_first_panel else None)
        mean_ppo = sub.groupby("steps")["ppo_wait"].mean().sort_index()
        ax.plot(mean_ppo.index / 1e6, mean_ppo.values, "o-", lw=2.2, ms=4,
                 color="tab:blue", zorder=5,
                 label=f"{args.version_name} mean" if is_first_panel else None)

        # -- Fixed timers: per-seed flat lines -- still flat (no dependence on
        #    training step), but now visibly separated by seed instead of
        #    collapsed into one averaged height.
        for ct in FIXED_TIMERS:
            col = f"fixed_{ct}s_wait"
            for seed in seeds:
                s = sub[sub.seed == seed]
                ax.plot(s.steps / 1e6, s[col], fixed_styles[ct], lw=0.8, alpha=0.55,
                         color=seed_color[seed])
            mean_fixed = sub[col].mean()
            ax.axhline(mean_fixed, ls=fixed_styles[ct], color="black", lw=1.6, zorder=4,
                        label=f"Fixed_{ct}s mean" if is_first_panel else None)

        ax.set_yscale("log")
        ax.set_title(f"{scen} traffic")
        ax.set_xlabel("Training steps (millions)")
        ax.set_ylabel("Total wait time (s, log)")
        ax.grid(alpha=0.3)

    axes[0].legend(fontsize=7, loc="upper right", ncol=1)
    fig.suptitle(f"{args.version_name} -- per-seed detail (seeds {seeds})\n"
                 f"Fixed-timer lines are flat by construction: they depend only on "
                 f"(seed, scenario), never on training step -- but each seed's flat "
                 f"height now visible separately instead of averaged into one line")
    fig.tight_layout()
    out_path = os.path.join(out_dir, "sweep_curve_seed_detail.png")
    fig.savefig(out_path, dpi=140)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
