# DQN Agent

The project's original reinforcement learning approach: a Deep Q-Network
trained on the same kind of ground-truth SUMO state as the PPO agent, with a
richer, more heavily hand-tuned reward function (12+ weighted terms) against
a 10-dimensional observation. This was the project's primary agent for the
first part of development before the team moved to PPO — see
`../PhaseB/FlowGrid_Capstone_Project_Book.docx` (Section 2.3) for the full,
honest account of why, including the 34-run evaluation history showing the
DQN controller's instability.

Pre-DQN, pre-RL prototype scripts (manual/rule-based signal simulators) live
under `../Old_Versions/DQN/legacy/`, not here.

## What's in this folder

- `flowgrid/` — the core Python package: SUMO environment (`core/`), the DQN
  agent itself (`rl/`), map building (`maps/`), baseline-vs-trained
  evaluation (`eval/`), background job handling for the GUI (`jobs/`), and
  `paths.py`, which every other file reads project locations from.
- `gui/` — the desktop app (Tkinter): `flowgrid_gui.py`.
- `web/` — the browser dashboard: FastAPI backend (`main.py`) + `index.html`.
- `scripts/` — command-line entry points: `train.py`, `run_evaluate.py`,
  `run_compare.py`, `run_menu.py` (interactive menu over all of the above),
  plus maintenance scripts (`backup_training.py`, `check_device.py`, etc.).
- `launchers/` — double-clickable Windows launchers (`run_gui.bat`/`.vbs`)
  that start the GUI in its own process.
- `data/maps/` — your saved intersection presets (each subfolder is one
  map + its trained policy, if any).
- `results/` — a snapshot of the real evaluation history used in the book:
  `comparison_history.json` (35 logged DQN-vs-fixed-timer runs),
  `dqn_training_log*.jsonl(.bak)` (per-run training logs), and
  `training_archive/` / `policy_backups/` (saved policy checkpoints and
  learning curves per training run). The live, authoritative copy of this
  data is at `../SharedData/reports/` (that's what `flowgrid/paths.py`
  actually reads and writes) — this folder is a point-in-time copy kept
  here for easy browsing alongside the rest of the agent.
- `outputs/` — ad-hoc chart exports (e.g. `comparison_bar.png`).
- `docs/` — `GUI.md` (desktop app usage/theme reference) and `COMPARE.md`
  (how the Compare tab's fair, same-traffic comparison works).

## Running it

**Desktop GUI:**
```
cd DQN_Agent/gui
python flowgrid_gui.py
```
or double-click `launchers/run_gui.bat`.

**Browser dashboard:**
```
cd DQN_Agent/web
python main.py
```

**Command line** (train / evaluate / compare, or the interactive menu over
all of them):
```
cd DQN_Agent/scripts
python run_menu.py
```
