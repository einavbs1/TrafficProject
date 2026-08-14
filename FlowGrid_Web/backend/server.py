"""
FlowGrid_Web's own backend -- both the live data API behind the Live
Junction panel AND, once built, the FlowGrid_Web dashboard itself. This is
a single, standalone process for FlowGrid_Web (the customer-facing
product), entirely independent of PPO_Agent/scripts/comparison_web/
server.py (a developer-only tool for comparing checkpoints). The two are
not coupled: they only happen to import the same underlying simulation
code, comparison_core.py and evaluate_models.py, as shared library code,
exactly the way two separate products can share a common engine without
sharing a server.

Usage (normal -- one process, nothing else to start):
    cd FlowGrid_Web
    npm run build
    cd backend
    python server.py
Then open http://127.0.0.1:8001 (run_web.bat/run_web.vbs do all of this
for you). If FlowGrid_Web/dist/ doesn't exist yet (no build has been run),
this still serves the API alone; run `npm run build` first for the UI.

Usage (active frontend development, hot reload):
    npm run dev  # separate Vite dev server on port 5173
    python backend/server.py  # this file, API only, in a second window
The Vite dev server proxies nothing; FlowGrid_Web's own code simply always
points at http://127.0.0.1:8001 for its API calls, dev or built, so both
setups work unmodified.
"""
import os
import sys
import random
import threading
import multiprocessing
import webbrowser

_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS_DIR = os.path.abspath(os.path.join(_HERE, "..", "..", "PPO_Agent", "scripts"))
sys.path.insert(0, _TOOLS_DIR)

import comparison_core as core

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

STATIC_DIR = os.path.join(_HERE, "static")
DIST_DIR = os.path.join(_HERE, "..", "dist")

app = FastAPI(title="FlowGrid_Web Backend")

app.add_middleware(
    CORSMiddleware,
    # :5173 covers active development (npm run dev); :8001 covers the built
    # app served by this same process -- the frontend always calls
    # http://127.0.0.1:8001 explicitly, so if the page itself was loaded via
    # the "localhost" hostname instead of "127.0.0.1", browsers treat that
    # as a different origin and require both to be allowed here.
    allow_origins=[
        "http://127.0.0.1:5173", "http://localhost:5173",
        "http://127.0.0.1:8001", "http://localhost:8001",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class JobState:
    """Duck-types comparison_core.run_comparison's expected .put(msg) sink,
    the same pattern comparison_web/server.py uses, needed here because
    core.run_comparison() (shared code) always reports progress this way."""

    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"   # idle | running | done | error

    def reset(self, total, task_labels=None, watch_live=False):
        with self.lock:
            self.status = "running"

    def put(self, msg):
        with self.lock:
            if msg["type"] == "done":
                self.status = "done"
            elif msg["type"] == "fatal_error":
                self.status = "error"


job_state = JobState()

# Lazily created on the first run (not at import time -- Windows' spawn
# based multiprocessing re-imports this module in worker processes, so a
# Manager created at module scope could try to spawn its own manager
# process recursively). Published into by evaluate_models.py's
# _publish_live_state() every simulated step; read by the Dashboard's
# poll of GET /api/live_state.
_manager = None
_live_state = None


def _get_live_state():
    global _manager, _live_state
    if _live_state is None:
        _manager = multiprocessing.Manager()
        _live_state = _manager.dict({"active": False})
    return _live_state


class LiveDemoStartBody(BaseModel):
    scenario: str   # "Low" | "Medium" | "High"


@app.post("/api/live_demo/start")
def start_live_demo(body: LiveDemoStartBody):
    """No model picker, no baselines, no seed picker: this is the one
    button the Live Junction panel has. Always the already-registered
    champion checkpoint (comparison_core.DEFAULT_MODEL_PATH), always a
    fresh, server chosen random seed, one scenario, Watch Live always on."""
    if job_state.status == "running":
        raise HTTPException(status_code=409, detail="A run is already in progress.")

    model = {"name": core.DEFAULT_MODEL_NAME, "path": core.DEFAULT_MODEL_PATH}
    seed = random.randint(0, 999_999)

    live_state = _get_live_state()
    live_state.clear()
    live_state["active"] = False
    live_state["seed"] = seed

    tasks, task_meta = core.build_tasks(
        [model], [seed], [body.scenario], baselines=[], use_gui=True, live_state=live_state)
    job_state.reset(len(tasks))

    thread = threading.Thread(target=core.run_comparison,
                               args=(tasks, task_meta, job_state, 1), daemon=True)
    thread.start()
    return {"accepted": True, "seed": seed}


@app.get("/api/live_state")
def get_live_state():
    if _live_state is None:
        return {"active": False}
    return dict(_live_state)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Serves the built dashboard (npm run build's output). Registered last so
# every /api/* route above is matched first; this is purely a fallback for
# anything else, the built assets themselves plus a catch-all for React
# Router's client-side routes (so refreshing on e.g. /reports works too).
if os.path.isdir(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        candidate = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))


def main():
    url = "http://127.0.0.1:8001"
    if os.path.isdir(DIST_DIR):
        try:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()
        except Exception:
            pass
    uvicorn.run(app, host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
