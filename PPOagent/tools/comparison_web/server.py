"""
Comparison Web App -- FastAPI + vanilla HTML/CSS/JS frontend for
interactively comparing PPO checkpoints. Web equivalent of comparison_gui.py
(Tkinter), sharing all non-UI logic via comparison_core.py -- neither UI
duplicates the registry/task-building/evaluation code.

Usage:
    cd PPOagent/tools/comparison_web
    python server.py
Then open http://127.0.0.1:8000 (auto-opens in your default browser).
"""
import os
import sys
import threading
import webbrowser

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _TOOLS_DIR)

import comparison_core as core

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

STATIC_DIR = os.path.join(_HERE, "static")

app = FastAPI(title="PPO Comparison Web")


class JobState:
    """Web equivalent of the Tkinter app's queue.Queue -- duck-types the same
    .put(msg) interface so comparison_core.run_comparison works unmodified."""

    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"   # idle | running | done | error
        self.done = 0
        self.total = 0
        self.results_by_scenario = None
        self.warnings = []
        self.error = None
        self.task_labels = []
        self.watch_live = False

    def reset(self, total, task_labels=None, watch_live=False):
        with self.lock:
            self.status = "running"
            self.done = 0
            self.total = total
            self.results_by_scenario = None
            self.warnings = []
            self.error = None
            self.task_labels = task_labels or []
            self.watch_live = watch_live

    def put(self, msg):
        with self.lock:
            if msg["type"] == "progress":
                self.done, self.total = msg["done"], msg["total"]
            elif msg["type"] == "episode_error":
                self.warnings.append(f"{msg['label']}: {msg['error']}")
            elif msg["type"] == "done":
                self.status = "done"
                self.results_by_scenario = msg["results_by_scenario"]
            elif msg["type"] == "fatal_error":
                self.status = "error"
                self.error = msg["error"]

    def snapshot(self):
        with self.lock:
            results = None
            if self.results_by_scenario is not None:
                results = {}
                for scen, df in self.results_by_scenario.items():
                    table = df.reset_index().rename(columns={"index": "model"})
                    seed_cols = [c for c in table.columns if c not in ("model", "Average")]
                    results[scen] = {
                        "seed_columns": [str(c) for c in seed_cols],
                        "rows": table.to_dict("records"),
                    }
            # Only meaningful in Watch Live mode: with max_workers=1, tasks
            # complete in strict submission order, so task_labels[done] is
            # exactly the one running right now (see describe_task's docstring).
            current = None
            if self.watch_live and self.done < len(self.task_labels):
                current = core.describe_task(self.task_labels[self.done])
            return {
                "status": self.status,
                "done": self.done,
                "total": self.total,
                "warnings": list(self.warnings),
                "error": self.error,
                "results": results,
                "current": current,
            }


job_state = JobState()
registry_lock = threading.Lock()


class AddModelBody(BaseModel):
    path: str


class RemoveModelBody(BaseModel):
    path: str


class StartBody(BaseModel):
    models: list[str]       # list of model paths (from the registry)
    seeds: list[int]
    scenarios: list[str]
    baselines: list[str] = []    # names from AVAILABLE_BASELINES
    watch_live: bool = False


@app.get("/api/models")
def get_models():
    return core.load_registry()


@app.get("/api/baselines")
def get_baselines():
    return [b["name"] for b in core.AVAILABLE_BASELINES]


@app.post("/api/models")
def post_model(body: AddModelBody):
    with registry_lock:
        entries = core.load_registry()
        entries = core.add_model_entry(entries, body.path)
    return entries


@app.delete("/api/models")
def delete_model(body: RemoveModelBody):
    with registry_lock:
        entries = core.load_registry()
        entries = [e for e in entries if e["path"] != body.path]
        core.save_registry(entries)
    return entries


@app.post("/api/start")
def start_comparison(body: StartBody):
    if job_state.status == "running":
        raise HTTPException(status_code=409, detail="A comparison is already running.")
    if not body.models and not body.baselines:
        raise HTTPException(status_code=400, detail="Select at least one model or baseline.")
    if not body.seeds:
        raise HTTPException(status_code=400, detail="Add at least one seed.")
    if not body.scenarios:
        raise HTTPException(status_code=400, detail="Select at least one scenario.")
    if body.watch_live and (len(body.seeds) != 1 or len(body.scenarios) != 1):
        raise HTTPException(
            status_code=400,
            detail="Watch Live requires exactly 1 seed and 1 specific scenario "
                   "(not \"All\") -- SUMO's GUI can only show one window at a time.")

    entries = core.load_registry()
    by_path = {e["path"]: e for e in entries}
    models = [by_path[p] for p in body.models if p in by_path]
    if body.models and not models:
        raise HTTPException(status_code=400, detail="No valid models selected.")

    baselines_by_name = {b["name"]: b for b in core.AVAILABLE_BASELINES}
    baselines = [baselines_by_name[n] for n in body.baselines if n in baselines_by_name]

    tasks, task_meta = core.build_tasks(
        models, body.seeds, body.scenarios, baselines=baselines, use_gui=body.watch_live)
    job_state.reset(len(tasks), task_labels=[t[0] for t in tasks], watch_live=body.watch_live)

    max_workers = 1 if body.watch_live else None
    thread = threading.Thread(target=core.run_comparison,
                               args=(tasks, task_meta, job_state, max_workers), daemon=True)
    thread.start()
    return {"accepted": True, "total": len(tasks)}


@app.get("/api/status")
def get_status():
    return job_state.snapshot()


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def main():
    url = "http://127.0.0.1:8000"
    try:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    except Exception:
        pass
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
