import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# __file__ = PhaseB/book_source/plot_dqn_inconsistency.py; project root is two levels up.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.join(_HERE, "..", "..")
_COMPARISON_HISTORY = os.path.join(_PROJECT_ROOT, "SharedData", "reports", "comparison_history.json")

with open(_COMPARISON_HISTORY, encoding="utf-8") as f:
    data = json.load(f)

records = [r for r in data["records"] if r.get("map_name") != "Test"]
records.sort(key=lambda r: r["timestamp"])

x = list(range(1, len(records) + 1))
y = [r["improvement_percent"] for r in records]
failed = [r["dqn_wait"] == 0.0 for r in records]

colors = ["gray" if f else ("tab:red" if v < 0 else "tab:blue") for f, v in zip(failed, y)]

plt.figure(figsize=(12, 6))
plt.scatter(x, y, c=colors, s=60, zorder=3)
plt.axhline(0, color="black", linewidth=1)
plt.yscale("symlog", linthresh=100)
plt.xlabel("Evaluation run, in chronological order (all on a single seed, 42)")
plt.ylabel("% improvement vs. fixed-time baseline (symlog scale)")
plt.title("DQN evaluation history: every logged run, nothing excluded")
plt.grid(alpha=0.3)

from matplotlib.lines import Line2D
legend_elems = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='tab:blue', markersize=9, label='Improvement over baseline'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='tab:red', markersize=9, label='Worse than baseline'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=9, label='Logged as 0 wait time (likely a failed run)'),
]
plt.legend(handles=legend_elems, loc="lower left")
plt.tight_layout()
plt.savefig(os.path.join(_HERE, "dqn_inconsistency_chart.png"), dpi=130)
print("saved")
