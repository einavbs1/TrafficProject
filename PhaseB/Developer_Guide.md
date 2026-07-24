# FlowGrid — Developer / Maintenance Guide

This guide covers what is needed to continue developing, retraining, or
extending this project after its initial delivery. It assumes familiarity
with standard Python development and does not cover installing well-known
general-purpose infrastructure (Python itself, Git, a code editor) in
detail.

## Required Environment

- Python 3.10, with the packages listed in `../requirements.txt` (notably:
  Stable-Baselines3, sb3-contrib, sumo-rl, pandas, matplotlib, seaborn,
  customtkinter, FastAPI, uvicorn).
- SUMO (Simulation of Urban Mobility), including its Python/TraCI and
  libsumo bindings, installed and available on the system path.
- A multi-core CPU is strongly recommended: training and full evaluation
  sweeps run ten parallel simulation instances by default.

## Project-Specific Installation

Clone the project's Git repository, then install Python dependencies from
`requirements.txt` into a virtual environment. No project-specific
installation step beyond this is required — the environment and training
scripts locate the SUMO network and route files via paths defined in the
code (`SharedData/`).

## Project Structure, at a Glance

- **`PPO_Agent/`** — the current, submitted agent (V8). `scripts/` has every
  runnable tool; `models/`/`checkpoints/` the trained weights; `results/`
  every evaluation run performed against it.
- **`DQN_Agent/`** — the original agent, fully self-contained under its own
  `flowgrid/` package.
- **`Old_Versions/`** — every earlier/alternate PPO version and pre-RL
  prototype, each self-contained in its own folder, never overwritten by
  later versions.
- **`SharedData/`** — the SUMO network/route files and shared reports data,
  read via absolute paths (PPO side) or via `DQN_Agent/flowgrid/paths.py`
  (DQN side). Both resolve to this folder regardless of where the
  individual agent folders sit, as long as `SharedData/` stays a direct
  child of the project root.

## Retraining or Extending the PPO Agent

To train a new version, copy `PPO_Agent/scripts/` (and the model files, if
building on an existing one) into a new folder under `Old_Versions/PPO/`
rather than modifying `PPO_Agent/` in place — this preserves the current
submitted agent as a working reference. Update internal import references
to point to the copy, and adjust `train_V8.py`'s hyperparameters as needed.

**Never resume training an existing checkpoint after changing its reward
function or observation definition.** Train a fresh agent from random
initialization instead — resuming under a changed definition has
previously produced a full, unrecoverable policy collapse (see the book,
Section 2.6).

## Adding a New Baseline or Comparison Target

New fixed-time or rule-based baselines can be added by extending the
baseline list used by the evaluation tools (`PPO_Agent/scripts/comparison_core.py`,
`AVAILABLE_BASELINES`); each baseline needs only a name and, for fixed-time
controllers, a cycle length, since the comparison tools handle result
collection and reporting generically.

## Running an Evaluation Sweep

`PPO_Agent/scripts/final_results_random_seeds.py` and `checkpoint_sweep.py`
both support a `--dry-run` mode that reports exactly how many simulation
runs a given sweep will perform and how long it is expected to take,
without executing anything — always run this first before committing to a
long sweep. Sweeps also write partial results incrementally as they
progress (`final_results_random_seeds.py --resume <out_dir>`) and can be
resumed from where they left off if interrupted.

## Shared Dependency Note

`PPO_Agent/scripts/evaluate_models.py` is the shared evaluation engine used
by every script in that folder (training, comparison, sweeps). It is a
standalone copy — the same file also lives at
`Old_Versions/PPO/src/evaluate_models.py`, used by every archived version's
own `evaluate_*.py`. If you fix a bug in one, consider whether the other
copy needs the same fix.
