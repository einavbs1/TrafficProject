# FlowGrid_Web

A SaaS-style traffic operations dashboard (login, multi-junction navigation
by district/city/freeway, device settings, reports, user management). This
is a separate, independent product from `PPO_Agent/scripts/comparison_web/`
(that one is a developer-only tool for comparing checkpoints); FlowGrid_Web
demonstrates what a deployed traffic-ops product could look like to an
actual operator.

Most of it is a complete, working UI backed by simulated demo data
generated in the browser. The one exception is deliberate: the
**"Live Junction (SUMO Simulation)"** entry is wired to a real backend
(`backend/server.py`) that runs the actual trained PPO agent against a real
SUMO episode and streams back genuine per-direction vehicle counts, signal
colors, and a live snapshot image.

## Running it

Double-click `run_web.bat` (keeps a console window open, useful for logs)
or `run_web.vbs` (no visible window). Either one:

1. Builds the dashboard (`npm run build`)
2. Starts `backend/server.py`, which serves both the built UI and its API
   from **one process** on `http://127.0.0.1:8001`
3. Opens your browser automatically

That's it — one script, one process, no separate dev server needed to just
run it. Allow up to ~30 seconds after launch before "Run Agent" works; the
backend needs that long to import torch, SUMO, and Stable-Baselines3.

**Login:** `admin` / `admin123` (Administrator) or `operator` / `op123`
(Operator) — fixed demo accounts, no real authentication server.

## Active frontend development

If you're editing the React code and want hot-reload, run the Vite dev
server separately instead of building:

```
npm run dev            # port 5173, hot reload
cd backend && python server.py   # API only, port 8001, in a second window
```

The frontend always calls `http://127.0.0.1:8001` for its API regardless of
which mode it's running in, so both setups work unmodified.

## Project layout

- `src/` — the React app. `JunctionContext.jsx` defines the one real
  junction (`LIVE_JUNCTION_ID`); `pages/Dashboard.jsx` is where it's wired
  to the live backend; `Tour.jsx` is the built-in guided tour.
- `backend/server.py` — FlowGrid_Web's own dedicated FastAPI backend.
  Imports `comparison_core.py`/`evaluate_models.py` from `PPO_Agent/scripts/`
  as shared library code only; it does not talk to or depend on
  `comparison_web/server.py` in any way.
- `backend/static/` — where the live SUMO snapshot image lands each run.

See the project's Developer Guide (`PhaseB/Developer_Guide.docx`, Section 6)
for the full technical walkthrough, and the User Guide
(`PhaseB/User_Guide.docx`, Section 6) for a field-by-field usage guide.
