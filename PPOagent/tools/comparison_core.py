"""
Comparison Core -- shared, UI-agnostic logic for comparing PPO checkpoints.

Used by BOTH comparison_gui.py (Tkinter) and comparison_web/server.py
(FastAPI) so neither duplicates the registry/task-building/evaluation logic.
Nothing in this module depends on Tkinter, FastAPI, or any other UI layer --
`run_comparison`'s only requirement on its `sink` argument is that it have a
`.put(msg_dict)` method, so a real `queue.Queue` (Tkinter) or any other
thread-safe sink (e.g. the web app's JobState) both work unmodified.

HARD CONSTRAINT: evaluate_models.py resolves its environment class via
`from sumo_rl_env import ...`, a process-wide import cached the first time it
happens, resolved via whichever version folder is first on sys.path. This
module hardcodes that resolution to V8's shim. Every model added to the
registry MUST be a V8-family checkpoint (V8 itself, V8_replicate, or another
V8-derived version, all sharing V8's 21-dim observation/action space). Do
NOT add V4/V6/V7 checkpoints -- they use a different (13-dim) observation
space and this process only ever loads one environment definition.
"""
import os
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC  = os.path.abspath(os.path.join(_HERE, "..", "src"))
_VDIR = os.path.abspath(os.path.join(_HERE, "..", "saved_agents", "V8"))
sys.path.insert(0, _SRC)
sys.path.insert(0, _VDIR)   # V8 shim (sumo_rl_env.py) must win the import
from evaluate_models import run_evaluation_task
sys.path.insert(0, _HERE)
from sweep_aggregate import SCENARIOS

from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd

REGISTRY_PATH      = os.path.join(_HERE, "comparison_gui_models.json")
DEFAULT_MODEL_NAME = "PPO_Agent_V8"
DEFAULT_MODEL_PATH = os.path.join(_VDIR, "models", "ppo_model_20260702_011233.zip")
EST_MIN_PER_EPISODE = 2.5
MAX_WORKERS        = 10

# Same baseline names/definitions used throughout this project's eval tables
# (see PPOagent/src/evaluate_models.py's models_to_test list). Max_Pressure is
# excluded -- known to gridlock on this network (diagnosed earlier this
# session), not a meaningful comparison target here.
AVAILABLE_BASELINES = [
    {"name": "Fixed_30s", "type": "fixed", "cycle_time": 30},
    {"name": "Fixed_45s", "type": "fixed", "cycle_time": 45},
    {"name": "Fixed_60s", "type": "fixed", "cycle_time": 60},
]


def load_registry():
    if not os.path.exists(REGISTRY_PATH):
        entries = [{"name": DEFAULT_MODEL_NAME, "path": DEFAULT_MODEL_PATH}]
        save_registry(entries)
        return entries
    with open(REGISTRY_PATH, "r") as f:
        return json.load(f)


def save_registry(entries):
    with open(REGISTRY_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def add_model_entry(entries, new_path):
    new_norm = os.path.normcase(os.path.abspath(new_path))
    for e in entries:
        if os.path.normcase(os.path.abspath(e["path"])) == new_norm:
            return entries  # already registered
    name = os.path.basename(new_path)
    if name.endswith(".zip"):
        name = name[:-4]
    entries = entries + [{"name": name, "path": new_path}]
    save_registry(entries)
    return entries


def compute_estimate(n_models, n_seeds, n_scenarios):
    n_episodes = n_models * n_seeds * n_scenarios
    if n_episodes <= 0:
        return 0, 0.0, 1
    workers = max(1, min(MAX_WORKERS, n_episodes))
    eta_min = n_episodes * EST_MIN_PER_EPISODE / workers
    return n_episodes, eta_min, workers


def describe_task(label):
    """label is "scenario|name|seed" (see build_tasks) -- turn it into a
    human-readable string for "currently running" displays. With
    max_workers=1 (Watch Live), tasks complete in strict submission order
    (a single worker, no reordering possible), so task_labels[done] is
    always the one actually running right now."""
    scen, name, seed = label.split("|")
    return f"{name} -- {scen} traffic (seed {seed})"


def build_tasks(models, seeds, scenario_names, baselines=None, use_gui=False):
    """models: list of {"name", "path"}; scenario_names: e.g. ["Low", "High"];
    baselines: list of entries from AVAILABLE_BASELINES (or a matching dict),
    added alongside the PPO models using the same "fixed"/"mp" model types
    evaluate_models.py already supports. use_gui: threaded into every task's
    last slot -- True opens a real SUMO window per episode (see run_comparison's
    max_workers note: only ever run with max_workers=1 when use_gui=True)."""
    scen_lookup = dict(SCENARIOS)
    tasks = []
    task_meta = {}  # label -> (scenario, model_name, seed)
    for scen in scenario_names:
        route = scen_lookup[scen]
        for m in models:
            for seed in seeds:
                label = f"{scen}|{m['name']}|{seed}"
                tasks.append((label, "ppo", route, seed, None, m["path"], use_gui))
                task_meta[label] = (scen, m["name"], seed)
        for b in (baselines or []):
            for seed in seeds:
                label = f"{scen}|{b['name']}|{seed}"
                tasks.append((label, b["type"], route, seed, b.get("cycle_time"), None, use_gui))
                task_meta[label] = (scen, b["name"], seed)
    return tasks, task_meta


def run_comparison(tasks, task_meta, sink, max_workers=None):
    """Runs entirely inside a background thread. Owns the ProcessPoolExecutor.
    Only ever communicates back via sink.put(...) -- never touches any UI
    directly, so the same function drives both the Tkinter queue.Queue and
    the web app's JobState.

    max_workers: pass 1 when any task has use_gui=True -- SUMO's GUI mode is
    only sensible to view one window at a time (mirrors the existing
    `workers = 1 if use_gui else 10` in evaluate_models.py's evaluate_scenario).
    Defaults to MAX_WORKERS for the normal headless case."""
    try:
        total = len(tasks)
        done = 0
        raw = {}  # scenario -> model_name -> seed -> total_wait
        workers = max_workers or MAX_WORKERS
        with ProcessPoolExecutor(max_workers=min(workers, max(total, 1))) as pool:
            futures = {pool.submit(run_evaluation_task, t): t for t in tasks}
            for fut in as_completed(futures):
                label = futures[fut][0]
                try:
                    name, seed, df = fut.result()
                    scen, model_name, seed_meta = task_meta[name]
                    total_wait = df["system_total_waiting_time"].sum()
                    raw.setdefault(scen, {}).setdefault(model_name, {})[seed_meta] = total_wait
                except Exception as exc:
                    sink.put({"type": "episode_error", "label": label, "error": str(exc)})
                done += 1
                sink.put({"type": "progress", "done": done, "total": total})

        results_by_scenario = {}
        for scen, model_data in raw.items():
            df = pd.DataFrame(model_data).T          # rows=models, cols=seeds
            df = df[sorted(df.columns)]               # deterministic seed-column order
            df["Average"] = df.mean(axis=1)
            results_by_scenario[scen] = df
        sink.put({"type": "done", "results_by_scenario": results_by_scenario})
    except Exception as exc:
        sink.put({"type": "fatal_error", "error": str(exc)})
