"""
V4 Evaluation Script -- run from THIS folder.

    cd PPOagent/saved_agents/V4_initial
    python evaluate_V4.py --seeds 5

Auto-finds latest model from ./models/
Saves results to ./results/
"""
import os, sys, glob, shutil
from datetime import datetime

# -- Paths relative to this script --------------------------------------------
_HERE       = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(_HERE, "models")
RESULTS_DIR = os.path.join(_HERE, "results")

# -- Import shared evaluation logic from src/ ---------------------------------
_SRC = os.path.join(_HERE, "..", "..", "src")
sys.path.insert(0, _SRC)
sys.path.insert(0, _HERE)

from evaluate_models import run_evaluation_task, evaluate_scenario
import argparse

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
        f.write(f"Run: {timestamp}\nSeeds: {seeds}\nAgent: V4 initial (diff_waiting_time)\n")

    print(f"V4 EVALUATION  |  results -> {eval_dir}\n", flush=True)

    # Auto-find latest V4 model (exclude backups)
    zips = [z for z in glob.glob(os.path.join(MODELS_DIR, "ppo_model_*.zip"))
            if "_backup_" not in os.path.basename(z)]
    if not zips:
        print("ERROR: No model found in", MODELS_DIR); return
    model_path = max(zips, key=os.path.getmtime)
    print(f"Model: {model_path}")

    maps = [
        {"name": "Low_Traffic",    "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml"},
        {"name": "Medium_Traffic", "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_hard.rou.xml"},
        {"name": "High_Traffic",   "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_extreme.rou.xml"},
    ]
    models_to_test = [
        {"name": "Maskable_PPO_V4", "type": "ppo",   "path": model_path},
        {"name": "Fixed_30s",       "type": "fixed",  "cycle_time": 30},
        {"name": "Fixed_45s",       "type": "fixed",  "cycle_time": 45},
        {"name": "Fixed_60s",       "type": "fixed",  "cycle_time": 60},
        {"name": "Max_Pressure",    "type": "mp"},
    ]

    # Copy evaluated model snapshot into results folder
    shutil.copy(model_path, os.path.join(eval_dir, os.path.basename(model_path)))
    agent_id   = os.path.basename(model_path).replace(".zip", "").replace("ppo_model_", "")
    stats_path = os.path.join(MODELS_DIR, f"vec_normalize_{agent_id}.pkl")
    if os.path.exists(stats_path):
        shutil.copy(stats_path, os.path.join(eval_dir, "vec_normalize_stats.pkl"))

    for m in maps:
        evaluate_scenario(m["name"], m["route"], seeds, models_to_test, eval_dir, args.gui)

    print("\nV4 Evaluation complete.")

if __name__ == "__main__":
    main()
