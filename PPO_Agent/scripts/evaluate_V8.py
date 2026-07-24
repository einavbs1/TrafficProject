"""
V8 Evaluation Script -- run from THIS folder.

    cd PPO_Agent/scripts
    python evaluate_V8.py --seeds 5

Auto-finds latest model from ./models/
Saves results to ./results/
"""
import os, sys, glob, shutil
from datetime import datetime
import pandas as pd

_HERE       = os.path.dirname(os.path.abspath(__file__))
_ROOT       = os.path.abspath(os.path.join(_HERE, ".."))   # PPO_Agent root
MODELS_DIR  = os.path.join(_ROOT, "models")
RESULTS_DIR = os.path.join(_ROOT, "results")

sys.path.insert(0, _HERE)

from evaluate_models import run_evaluation_task, evaluate_scenario
import argparse


def print_extra_metrics(eval_dir, map_name):
    raw_path = os.path.join(eval_dir, f"eval_{map_name.lower()}_raw_data.csv")
    if not os.path.exists(raw_path):
        return
    df = pd.read_csv(raw_path)
    summary = (df.groupby("Model")
                 .agg(
                     Total_Wait_Time=("Total_Wait_Time", "mean"),
                     Total_Arrived=("Total_Arrived", "mean"),
                     Total_Switches=("Total_Switches", "mean"),
                     Peak_Max_Wait_s=("Peak_Max_Wait_s", "mean"),
                 )
                 .reset_index())
    summary["Wait_Per_Vehicle"] = (
        summary["Total_Wait_Time"] / summary["Total_Arrived"].clip(lower=1)
    ).round(0)
    summary["Switch_Rate_per100s"] = (summary["Total_Switches"] / 200).round(1)
    summary = summary.sort_values("Total_Wait_Time")
    print(f"\n--- {map_name} EXTENDED METRICS ---")
    cols = ["Model", "Total_Wait_Time", "Wait_Per_Vehicle", "Peak_Max_Wait_s",
            "Switch_Rate_per100s", "Total_Arrived"]
    print(summary[cols].to_string(index=False))
    summary[cols].to_csv(
        os.path.join(eval_dir, f"eval_{map_name.lower()}_extended.csv"), index=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui",   action="store_true")
    parser.add_argument("--seeds", type=int, default=5)
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    eval_dir  = os.path.join(RESULTS_DIR, f"eval_{timestamp}")
    os.makedirs(eval_dir, exist_ok=True)

    seeds = [42] if (args.gui and args.seeds == 5) else [42, 123, 1337, 2026, 9999][:args.seeds]

    with open(os.path.join(eval_dir, "evaluation_config.txt"), "w") as f:
        f.write(f"Run: {timestamp}\nSeeds: {seeds}\n")
        f.write(f"Agent: V8 (diff_wait + starvation@45s + hard empty-intersection mask + camera150m)\n")

    print(f"V8 EVALUATION  |  results -> {eval_dir}\n", flush=True)

    zips = [z for z in glob.glob(os.path.join(MODELS_DIR, "ppo_model_*.zip"))
            if "_backup_" not in os.path.basename(z)]
    if not zips:
        print("ERROR: No model found in", MODELS_DIR); return
    model_path = max(zips, key=os.path.getmtime)
    print(f"Model: {model_path}")

    maps = [
        {"name": "Low_Traffic",
         "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml"},
        {"name": "Medium_Traffic",
         "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_hard.rou.xml"},
        {"name": "High_Traffic",
         "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_extreme.rou.xml"},
    ]
    models_to_test = [
        {"name": "Maskable_PPO_V8", "type": "ppo",   "path": model_path},
        {"name": "Fixed_30s",       "type": "fixed",  "cycle_time": 30},
        {"name": "Fixed_45s",       "type": "fixed",  "cycle_time": 45},
        {"name": "Fixed_60s",       "type": "fixed",  "cycle_time": 60},
        {"name": "Max_Pressure",    "type": "mp"},
    ]

    shutil.copy(model_path, os.path.join(eval_dir, os.path.basename(model_path)))
    agent_id   = os.path.basename(model_path).replace(".zip", "").replace("ppo_model_", "")
    stats_path = os.path.join(MODELS_DIR, f"vec_normalize_{agent_id}.pkl")
    if os.path.exists(stats_path):
        shutil.copy(stats_path, os.path.join(eval_dir, "vec_normalize_stats.pkl"))

    for m in maps:
        evaluate_scenario(m["name"], m["route"], seeds, models_to_test, eval_dir, args.gui)
        print_extra_metrics(eval_dir, m["name"])

    print("\nV8 Evaluation complete.")


if __name__ == "__main__":
    main()
