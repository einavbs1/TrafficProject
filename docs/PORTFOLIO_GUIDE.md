# FlowGrid — Project Portfolio Documentation

This document contains two standalone sections for the final project portfolio: an operator's guide for the local GUI, and a developer maintenance and installation guide.

---

# 2.1 User's Guide

**Audience:** System operators and traffic engineers  
**Scope:** Nominal operation of the FlowGrid local Tkinter control panel (happy path only)

## Overview

FlowGrid trains and evaluates a Deep Q-Network (DQN) agent that controls traffic signals in a SUMO simulation. The desktop application provides four tabs:

| Tab | Purpose |
|-----|---------|
| **Build map** | Create or manage intersection maps |
| **Train AI** | Run DQN training and view live progress |
| **Compare** | Evaluate DQN vs. fixed-time baseline on identical traffic |
| **Reports** | Review training history and past Compare results |

All training and Compare jobs run in the background. Progress appears in the status bar, footer log, and the active tab.

---

## Step 1 — Start the GUI

1. Open a terminal in the project root folder (`TrafficProject`).
2. Launch the application using either method:

   ```text
   python flowgrid_gui.py
   ```

   or double-click:

   ```text
   run_gui.bat
   ```

3. The **FlowGrid** window opens. The application starts on the **Train AI** tab.

---

## Step 2 — Select an Active Map

Every training and Compare run operates on one intersection map. The active map is selected from the header bar (top-right).

### Option A — Use an existing map (recommended)

1. Click the **Active map** dropdown in the top-right corner.
2. Select **Plan 2 (opposite thru+right)** or another saved map from the list.
3. The selected map is now used for all Train and Compare operations.

### Option B — Build and save a new map

1. Open the **Build map** tab.
2. Enter a **Map name** and **Arm length** (meters).
3. Choose a **Phasing plan** and adjust **Traffic flow** values (0–1 per movement) if needed.
4. Click **Save map**.
5. Return to the header **Active map** dropdown and select the newly saved map.

The trained policy for each map is stored separately as `dqn_policy.pth` inside that map's folder under `data/maps/<map_id>/`.

---

## Step 3 — Run a Training Session

1. Confirm the correct map is selected in the **Active map** dropdown.
2. Open the **Train AI** tab.
3. Set the training parameters:

   | Field | Typical value | Description |
   |-------|---------------|-------------|
   | **Episodes** | `500` | Number of training episodes to run |
   | **Save every N ep.** | `10` | Checkpoint interval |
   | **Min base (s)** | `5` | Absolute safety minimum green |
   | **Min green cap (s)** | `60` | Earliest allowed phase switch |
   | **Min cars switch** | `3` | Minimum opposing queue to justify a switch |
   | **Max green (0=off)** | `0` | Optional hard cap on green duration |

4. Leave **Resume from existing dqn_policy.pth** checked to continue from the last saved weights. Uncheck only when intentionally starting a new untrained network.
5. Click **▶ Start training**.

### What happens during training

- The **Training progress** panel shows the current episode, reward, exploration rate (ε), and total wait.
- The **Learning curve (live)** chart updates as episodes complete.
- The policy checkpoint is saved automatically to `data/maps/<map_id>/dqn_policy.pth` at each checkpoint interval and at the end of the run.
- Training log entries are appended to `data/reports/dqn_training_log.jsonl`.

### When training finishes

- The progress bar reaches 100%.
- The status line shows **Training complete**.
- The saved policy is ready for Compare evaluation.

To stop early, click **■ Stop**. The current episode completes and the latest checkpoint is saved.

---

## Step 4 — Run a Compare Evaluation

Compare measures whether the trained DQN reduces total waiting time compared to a fixed-time baseline on **identical traffic**.

1. Confirm the same **Active map** used for training is selected.
2. Open the **Compare** tab.
3. Set the Compare parameters:

   | Field | Typical value | Description |
   |-------|---------------|-------------|
   | **Baseline green (s)** | `60` | Fixed-time green duration per phase |
   | **Inject until (s)** | `800` | Random traffic injection period |
   | **Seed** | `42` | Reproducible traffic random seed |
   | **SUMO 3D** | Optional | Show SUMO graphical window during run |
   | **Delay ms** | `30` | GUI refresh delay when 3D is enabled |

4. Click **▶ Run comparison**.

### What happens during Compare

1. **Phase 1 — Baseline:** SUMO injects random traffic until the inject time, then drains the network using fixed-time signals. Vehicle departures are recorded.
2. **Phase 2 — DQN:** SUMO restarts with the exact same vehicles (replay file). The trained DQN policy controls the signals with exploration disabled.
3. Results appear in the Compare panels: waiting-time summaries, improvement percentage, and bar charts.

### Reading the result

- The primary metric is **all-vehicle wait** (cars, buses, and emergency vehicles combined).
- A successful run shows DQN all-vehicle wait **less than or equal to** the baseline all-vehicle wait.
- Results are stored in `data/reports/comparison_history.json` and visible on the **Reports** tab.

---

## Step 5 — Review Results (optional)

1. Open the **Reports** tab.
2. View the **Training progress** summary and learning-curve chart from the training log.
3. Review the **Compare history** table for past evaluation runs on the active map.

---

## Nominal Workflow Summary

```text
Start GUI  →  Select active map  →  Train AI (500 episodes, resume ON)
           →  Wait for completion  →  Compare (seed 42, inject 800 s)
           →  Review Reports
```

---

# 2.2 Maintenance Guide

**Audience:** Future developers maintaining or upgrading the FlowGrid RL codebase  
**Scope:** Environment requirements and installation of the project-specific software stack

## System Purpose

FlowGrid is a Python application that:

- Wraps SUMO in a Gymnasium RL environment (`flowgrid/core/sumo_env.py`)
- Trains a PyTorch DQN agent (`flowgrid/rl/dqn_agent.py`)
- Persists maps, policies, and logs on the local filesystem (no database)
- Exposes training and evaluation through a Tkinter GUI (`gui/flowgrid_gui.py`) and CLI scripts (`scripts/`)

---

## Required Software Environment

### Operating system

| Platform | Status |
|----------|--------|
| **Windows 10/11** | Primary development and test platform |
| **Linux** | Supported for SUMO and Python components |

### Python

| Requirement | Detail |
|-------------|--------|
| **Version** | Python **3.10 or newer** (3.11+ recommended) |
| **Virtual environment** | Strongly recommended (`venv` or `conda`) |

### SUMO (Simulation of Urban MObility)

| Requirement | Detail |
|-------------|--------|
| **Version** | SUMO **1.18+** (any recent stable release) |
| **Tools required** | `sumo`, `sumo-gui`, `netconvert` (bundled with SUMO) |
| **Python bindings** | `traci`, `sumolib` (installed via pip) |
| **Environment variable** | `SUMO_HOME` must point to the SUMO installation root |

### Python libraries (project dependencies)

Declared in `requirements.txt`:

| Package | Minimum version | Role |
|---------|-----------------|------|
| `torch` | 2.0 | DQN neural network and optimizer |
| `gymnasium` | 0.29 | RL environment API |
| `numpy` | 1.24 | Observation and replay arrays |
| `matplotlib` | 3.7 | Learning curves and Compare charts |
| `pyyaml` | 6.0 | Policy configuration loader |
| `pydantic` | 2.0 | API request models (optional web layer) |
| `fastapi` | 0.100 | Optional web API |
| `uvicorn` | 0.23 | Optional web server |

Additional packages (required for SUMO integration):

| Package | Role |
|---------|------|
| `traci` | TraCI Python API for live SUMO control |
| `sumolib` | SUMO network and route utilities |

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores (SUMO is CPU-bound) |
| **RAM** | 8 GB | 16 GB |
| **GPU** | Not required | NVIDIA GPU with CUDA for faster DQN training |
| **Disk** | 2 GB free | 5+ GB (maps, checkpoints, logs, archives) |

### GUI dependencies

| Component | Detail |
|-----------|--------|
| **Tkinter** | Bundled with standard Python on Windows; required for the desktop GUI |
| **Segoe UI / Cascadia Mono** | Preferred fonts on Windows (fallbacks apply if missing) |

---

## Installation — Step by Step

These steps assume Python and SUMO are already installed on the machine. They cover only the FlowGrid project setup.

### 1. Clone the repository

```powershell
git clone <repository-url> TrafficProject
cd TrafficProject
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install traci sumolib
```

### 4. Configure the SUMO environment variable

**Windows (PowerShell — current session):**

```powershell
$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"
```

**Windows (permanent — User environment variable):**

Set `SUMO_HOME` to your SUMO installation directory (the folder containing `bin/`, `tools/`, and `data/`).

**Linux:**

```bash
export SUMO_HOME=/usr/share/sumo
```

Add the line to `~/.bashrc` or `~/.profile` for persistence.

### 5. Verify SUMO and TraCI

```powershell
python -c "import traci; import sumolib; print('TraCI OK')"
```

```powershell
& "$env:SUMO_HOME\bin\sumo.exe" --version
```

### 6. Initialize the default map (first-time setup)

If no maps exist in `data/maps/registry.json`, create the Plan 2 reference intersection:

```powershell
python scripts/setup_plan2_map.py
```

This generates SUMO network files under `data/maps/plan_2_opposite_thru_right/`.

### 7. Verify the GUI launches

```powershell
python flowgrid_gui.py
```

The FlowGrid window should open with **Plan 2 (opposite thru+right)** available in the Active map dropdown.

### 8. Verify checkpoint I/O (optional developer check)

```powershell
python scripts/verify_checkpoint_load.py
```

Expected output: `OK — Compare loader and resume checkpoint round-trip.`

---

## Key Project Paths

| Path | Contents |
|------|----------|
| `flowgrid/` | Core Python package (simulation, RL, jobs, eval) |
| `gui/flowgrid_gui.py` | Desktop control panel |
| `data/defaults/dqn_policy_config.yaml` | Master RL reward and training configuration |
| `data/maps/` | Saved intersections and per-map `dqn_policy.pth` |
| `data/reports/` | Training log, Compare history, curriculum log |
| `scripts/` | CLI entry points for headless train/compare |

---

## Configuration for Developers

| File | When to edit |
|------|--------------|
| `data/defaults/dqn_policy_config.yaml` | Reward weights, `step_length`, training hyperparameters, Compare inject time |
| `flowgrid/rl/policy_config.py` | Default values when YAML keys are absent |
| `gui/theme.py` | Desktop UI colors and fonts |

After changing reward or constraint values in the YAML, resume training from the GUI (**Resume** checkbox ON) or via:

```powershell
python scripts/run_train.py --map plan_2_opposite_thru_right --resume --episodes 500 --checkpoint-every 10
```

---

## CLI Alternatives to the GUI

For long training runs with live terminal output (recommended on Windows):

```powershell
python scripts/run_train.py --map plan_2_opposite_thru_right --resume --episodes 500 --checkpoint-every 10
python scripts/run_compare.py --map plan_2_opposite_thru_right --seed 42 --inject-seconds 800
python scripts/run_train_then_compare.py --map plan_2_opposite_thru_right --resume --episodes 500 --compare-seed 42 --inject-seconds 800
```

---

## Upgrade and Maintenance Notes

- **One policy per map:** each intersection has its own `dqn_policy.pth`; retraining map A does not affect map B.
- **Checkpoint format:** saves weights, ε, cumulative `episodes_done`, `steps_done`, and `epsilon_decay` (see `flowgrid/rl/policy_checkpoint_io.py`).
- **Policy archives:** `scripts/reset_training.py` and `scripts/backup_training.py` move old checkpoints and logs to `data/reports/training_archive/` and `data/reports/policy_backups/`.
- **No database migrations:** all state is file-based; back up `data/maps/` and `data/reports/` before major upgrades.

---

*FlowGrid Portfolio Guide — Operator and Maintenance documentation for the local RL simulation system.*
