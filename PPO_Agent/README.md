# PPO Agent (V8 — final, submitted agent)

This is the trained reinforcement learning agent that controls the FlowGrid
intersection: a Maskable PPO policy trained on SUMO's ground-truth traffic
state. It is the only PPO version carried forward into the final submission;
every earlier iteration (V4 through V9, plus two longer-training experiments)
is preserved for reference under `../Old_Versions/PPO/`, alongside the
project's original agent, `../Old_Versions/DQN_Agent/`.

## What's in this folder

- `run_web.bat` / `run_web.vbs` — double-click to launch the comparison app.
  This is FlowGrid's PPO interface; start here.
- `scripts/` — everything you run: training, evaluation, and the browser
  comparison app itself. See below.
- `models/`, `checkpoints/` — the trained agent. `models/ppo_model_20260702_011233.zip`
  (+ its matching `vec_normalize_20260702_011233.pkl`) is the champion model
  used everywhere in the submitted book and poster. `checkpoints/` holds a
  save every 100k training steps, used by the evaluation tools below.
- `results/` — every evaluation run performed against this agent:
  - `final_random_seeds_20260705_005802/` — the headline result: every
    checkpoint evaluated against its own independently drawn random seed
    and scenario (nothing cherry-picked). `summary.txt` has the win-rate
    breakdown (88.3%), `final_results.csv` the raw per-checkpoint numbers,
    `checkpoint_waittime_scatter.png` / `win_rate_scatter.png` the charts
    used in the book (Figures 2.2/2.3).
  - `checkpoint_sweep_20260702_135021/` — the full learning-curve sweep
    (2 fixed seeds, every checkpoint, all 3 scenarios).
  - `verify_candidates_*/` — 5-seed confirmation runs on a short list of
    candidate checkpoints.
  - `Untitled.png` — the linear-scale medium-traffic chart used as
    Figure 2.4 in the book / the poster's second chart.
- `tensorboard/` — raw training logs (loss curves, entropy, KL), viewable
  with `tensorboard --logdir tensorboard`.
- `docs/` — reference material specific to this agent (see below).

## Running it

All commands below assume `cd PPO_Agent/scripts` first.

**Train a fresh agent from scratch** (takes several hours):
```
python train_V8.py --timesteps 6000000
```
Resumes automatically from the latest checkpoint in `../models/` if one
exists; pass `--fresh` to force a clean run instead.

**Evaluate the champion model** against the three fixed-time baselines:
```
python evaluate_V8.py --seeds 5
```

**Re-run the full rigorous sweep** (every checkpoint, its own random
seed/scenario — what produced `results/final_random_seeds_20260705_005802/`):
```
python final_results_random_seeds.py --version-dir .. --dry-run   # see the plan first
python final_results_random_seeds.py --version-dir ..
```
Crash-safe: re-running with `--resume <out_dir>` continues an interrupted
run instead of restarting it.

**Launch the comparison app** — FlowGrid's PPO interface: pick any trained
model, any traffic scenario, any seed (including one typed in on the spot),
and watch the result, optionally live in an actual SUMO window. Double-click
`run_web.bat` right in the `PPO_Agent/` folder (or `run_web.vbs` for no
console window), or run it directly:
```
cd comparison_web && python server.py    # opens your browser automatically
```
The app includes a built-in guided tour (top-right "? Guide" button) that
walks through every field on first load and any time you reopen it. Its
logic lives in `comparison_core.py`, shared with the CLI sweep tools below,
and it reads/writes the model registry, `model_registry.json` (regenerated
automatically per machine, not checked into git).

This is a developer-only tool for comparing checkpoints. For a
customer-facing dashboard with one junction wired to this same agent live,
see `../FlowGrid_Web/` (`../FlowGrid_Web/run_web.bat`) — a separate product
with its own dedicated backend, not connected to this app.

## Docs in this folder

- `PPO_VERSION_HISTORY.md` — the full changelog: every version from V1
  through V9, what changed, and what happened.
- `ppo_vs_dqn_architecture.md` — why PPO's clipped updates and action
  masking beat DQN's discrete Q-learning for this problem.
- `HOW_PPO_LEARNS.md` — what the agent observes (21-dimensional state),
  how the reward is computed, and how to read its training progress.
- `V8_ARCHITECTURE_NOTES.md` — the specific changes that made V8 the first
  version to beat every baseline in every traffic condition (the hard
  action mask on empty-intersection switching).

For the full project write-up (background, results, lessons learned),
see `../PhaseB/FlowGrid_Capstone_Project_Book.docx`.
