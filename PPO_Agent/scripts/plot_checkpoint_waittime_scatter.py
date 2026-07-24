"""
Per-checkpoint wait-time scatter -- raw PPO vs. fixed-timer wait times, one
row per checkpoint, from a final_results_random_seeds.py output CSV.

Complementary to win_rate_scatter.png (which plots % improvement): this
plots the actual wait-time values so you can see PPO vs. each fixed timer
directly, not just the percentage gap.

Per-spec: y-axis = checkpoint training step, x-axis = waiting time (seconds).
PPO plotted in red, larger marker than the 3 fixed timers (blue/orange/green).

Usage:
    python plot_checkpoint_waittime_scatter.py --csv <path/to/final_results.csv>
"""
import os
import argparse
import pandas as pd
import seaborn as sns
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_CSV = (r"C:\Users\Einavs_PC\Documents\TrafficProject\PPO_Agent"
               r"\results\final_random_seeds_20260705_005802\final_results.csv")

PALETTE = {"PPO": "red", "Fixed_30s": "tab:blue",
           "Fixed_45s": "tab:orange", "Fixed_60s": "tab:green"}
RENAME = {"ppo_wait": "PPO", "fixed_30s_wait": "Fixed_30s",
          "fixed_45s_wait": "Fixed_45s", "fixed_60s_wait": "Fixed_60s"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--stride", type=int, default=10,
                        help="Plot every Nth checkpoint row (default 10) to cut clutter.")
    args = parser.parse_args()

    df = pd.read_csv(args.csv).sort_values("steps").iloc[::args.stride]
    out_path = os.path.join(os.path.dirname(os.path.abspath(args.csv)),
                             "checkpoint_waittime_scatter.png")

    melted = df.melt(id_vars=["steps", "scenario"], value_vars=list(RENAME.keys()),
                     var_name="Wait_Type", value_name="Wait_Time_Value")
    melted["Wait_Type"] = melted["Wait_Type"].map(RENAME)

    plt.figure(figsize=(12, 6))

    # style="scenario" makes seaborn draw a separate connected line per
    # (Wait_Type, scenario) combination -- so dots only connect to the next
    # checkpoint of the SAME traffic type, instead of zigzagging across
    # Low/Medium/High. 4 Wait_Types x 3 scenarios = 12 lines total, PPO's
    # marker now the same regular size as the 3 baselines.
    sns.lineplot(data=melted, x="steps", y="Wait_Time_Value",
                 hue="Wait_Type", style="scenario", palette=PALETTE,
                 marker="o", markersize=6, linewidth=1.5, alpha=0.85)

    plt.yscale("log")
    plt.ylabel("Waiting time (seconds, log scale)")
    plt.xlabel("Checkpoint training step")
    plt.title(os.path.basename(os.path.dirname(os.path.abspath(args.csv))) +
              f" -- PPO vs. fixed timers, every {args.stride}th checkpoint")
    plt.legend(title="Wait Type")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=130)
    print(f"Saved -> {out_path}")


if __name__ == "__main__":
    main()
