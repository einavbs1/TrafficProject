# Old Versions

Everything superseded by the final submission, kept for the record rather
than deleted.

## `PPO/`

The renamed former `PPOagent/` folder, minus V8 (now `../PPO_Agent`) and its
shared comparison tools (now `../PPO_Agent/scripts`). Still contains:
- `saved_agents/{V4_initial, V4.1_camera_fixed, V5, V6, V7, V9, V8_replicate,
  V8_12M}` — every earlier and alternate iteration. Each is self-contained
  (its own env, train/evaluate scripts, checkpoints, final model, tensorboard
  logs) and still runnable — the shared `src/evaluate_models.py` dependency
  moved with this whole tree, so the relative imports these versions use
  (`../../src`) still resolve.
- `src/`, `models/`, `results/`, `logs/`, `tensorboard/`, `assets/` — the
  project's pre-versioning first experiments (behavioral cloning, curriculum
  learning, a "production" agent, and a `perception.py` module from when
  computer-vision input was still the plan) — all abandoned in favor of the
  versioned `saved_agents/` approach.
- `docs/` — the historical, version-specific planning docs (per-version
  summaries, upgrade plans, the DQN priority/handoff notes) not carried
  into `../PPO_Agent/docs`, which only keeps docs still relevant to V8.

**A note on `checkpoints/` folders:** each version originally saved a
checkpoint every 100k (or, for `V8_12M`, every 10k) training steps, adding
up to well over a gigabyte across all versions combined. To keep this
archive a reasonable size, every version's `checkpoints/` was thinned down
to roughly one in ten of its original checkpoints, always keeping the very
first and very last, so the learning curve shape is still visible and every
tool that reads `checkpoints/` still finds real data to work with; nothing
was removed outright. Some checkpoints in the thinned set lack a matching
`vecnormalize` `.pkl` file, exactly as before thinning, since not every
version saved one at every step (`checkpoint_sweep.py` and the other sweep
tools already skip checkpoints missing their stats file, so this is expected
rather than a new gap this introduced).

## `DQN_Agent/`

The project's original reinforcement learning approach, in full: its own
`flowgrid/` package, desktop GUI, web dashboard, scripts, and evaluation
history — see `DQN_Agent/README.md` for the full breakdown. Superseded by
PPO as the primary approach (the book's Section 2.3 explains why), but
completely self-contained and still runnable from right here. Its
`legacy/` subfolder holds the pre-DQN, pre-RL prototype scripts
(manual/rule-based traffic simulators: `4WaySimulator.py`, `phase1_traci.py`,
`simpleSimulator.py`) that predate the reinforcement learning agent
entirely.

## `root_prototype/`

The very first PPO experiments, run before either the `PPOagent/` folder or
its `saved_agents/` versioning convention existed — `checkpoints/` (thinned,
same as above), `models/`, `results/`, `tensorboard/` from that earliest
run, plus a few stray root-level files (`PROJECT_STRUCTURE.txt`,
`repomix-output.xml`, `debug-216f56.log`) from the same period.
