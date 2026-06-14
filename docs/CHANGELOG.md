# FlowGrid changelog

Record of behavior and documentation changes. Older docs are **updated in place** (not removed); this file is the timeline.

---

## 2026-05-31 — Through vs left phasing (Plan 2)

| Change | Detail |
|--------|--------|
| **LEFT priority** | Dedicated LEFT phase only when left queue **exceeds** through queue on that arm (not merely ≥1 left car) |
| **Symptom** | Compare looked like only left + right green: right is **always** green by design; through was starved by over-aggressive left forcing |

**Files:** `actuated_controller.py`, `sumo_env.py`

---

## 2026-05-22 — Gridlock fix: reward, Compare loader, best checkpoint

| Change | Detail |
|--------|--------|
| **Compare load** | `_try_load_policy` uses new checkpoint format (`policy_state` + weights) |
| **Reward** | Stronger `total_wait_scale`, capped `fairness`, `drain_bonus` for arrivals / fleet shrink |
| **Best policy** | `dqn_policy_best.pth` saved on valid Compare; catastrophic Compare rolls back |
| **Curriculum** | Stops on catastrophic Compare (gridlock / 2× baseline wait) |
| **CLI** | `INVALID COMPARE` banner; all-vehicle wait shown as primary metric |

**Files:** `compare_guard.py`, `evaluate.py`, `sumo_env.py`, `job_runner.py`, `curriculum.py`, `dqn_policy_config.yaml`

---

## 2026-05-22 — Resume epsilon + total-wait reward

| Change | Detail |
|--------|--------|
| **Checkpoints** | `dqn_policy.pth` now saves weights + ε; resume keeps ε (~0.01) instead of resetting to 0.2 (fixes 42M wait spike on resume) |
| **Legacy .pth** | ε restored from `dqn_training_log.jsonl` when checkpoint has no ε field |
| **Reward** | `total_wait_scale` penalizes high network wait each step (all vehicles); bus/emergency stay modest extras on **delta** only |
| **Log line** | Training episodes print `mean_step=` (wait sum ÷ steps) for easier reading |

**Files:** `flowgrid/rl/policy_checkpoint_io.py`, `job_runner.py`, `sumo_env.py`, `dqn_policy_config.yaml`

---

## 2026-05-30 — Auto curriculum (train → compare → repeat)

| Change | Detail |
|--------|--------|
| **Auto curriculum** | After each training block, run fair Compare, analyze, log to `curriculum_log.jsonl`, repeat until goal or max cycles |
| **GUI** | Train tab → Auto progress card |
| **CLI** | `scripts/run_curriculum.py` |
| **Config** | `curriculum:` in `dqn_policy_config.yaml` |

**Files:** `flowgrid/reports/curriculum.py`, `flowgrid/jobs/job_runner.py`, `gui/flowgrid_gui.py`

---

## 2026-05-30 — Left-turn service + Compare drain fixes

| Change | Detail |
|--------|--------|
| **Left phases** | `phase_for_arm` prefers LEFT phase when `_LT` queue ≥ threshold; ring advance jumps to left phase when needed |
| **Force switch** | After min green, require switch if left-turn movements wait on red while current phase is through-only |
| **Compare drain** | `dqn_drain_extra_seconds: 1500`; `stall_control_steps: 0` (no early stop with cars on map) |
| **Training** | `epsilon_decay: 0.995` — 500 fresh episodes is early; target 1500–2500+ before trusting Compare |

**Files:** `actuated_controller.py`, `sumo_env.py`, `dqn_policy_config.yaml`, docs

---

## 2026-05-30 — Modern light GUI theme

### User interface

| Change | Detail |
|--------|--------|
| **Light default** | Replaced hardcoded dark palette (`#0c0f14` bg) with readable light neutrals (`#f6f8fb` page, `#ffffff` cards, `#0f172a` text) |
| **Central theme** | New [`gui/theme.py`](../gui/theme.py) — `THEME_LIGHT`, fonts, `apply_ttk_style()`, `style_matplotlib_axes()` |
| **Charts** | Matplotlib figures: light plot background, grid lines, legend styling |
| **Reports table** | `ttk.Treeview` + scrollbar styled for light mode |
| **Intersection canvas** | Shared light road/vehicle colors via `get_canvas_colors()` |
| **Typography** | Body 11pt (was 10), improved card padding |

**Files:** `gui/theme.py`, `gui/flowgrid_gui.py`, `gui/intersection_canvas.py`, [GUI.md](GUI.md)

**Dark theme:** `THEME_DARK` retained in `theme.py` for reference; app defaults to light.

---

## 2026-05-30 — Balanced policy era (reward + deferred priority)

### Policy / training (breaking for old checkpoints)

| Change | Before | After |
|--------|--------|--------|
| **Delay reward** | Weighted total wait; buses **2.5×** (`transit_delay_multiplier`) | **All vehicles equal** in base delay delta; extras `transit_priority_scale` (0.4), `emergency_priority_scale` (0.35) |
| **Emergency control** | Instant phase cut when emergency on red (`_emergency_active` forced switch) | **`priority_service`**: next green after min green; starvation guards for other arms |
| **Bus control** | Mostly via reward / actuated preemption | **Deferred next green** for transit arms when fair |
| **Throughput / fairness** | Defaults in earlier yaml | `throughput_per_vehicle: 0.75`, stronger starving/inactive penalties |

**Files:** `flowgrid/core/sumo_env.py`, `flowgrid/core/actuated_controller.py`, `flowgrid/rl/policy_config.py`, `data/defaults/dqn_policy_config.yaml`

**Migration:** Checkpoints trained ~20k episodes on the **old** reward should use **`--fresh`** training (see [FRESH_START.md](FRESH_START.md)). Resume is OK for small tweaks only.

**Backup:** `python scripts/backup_training.py` → `data/reports/policy_backups/<timestamp>_…/`

### Documentation

- [DQN_PRIORITY.md](DQN_PRIORITY.md) — balanced reward + `priority_service`
- [TRAINING.md](TRAINING.md) — fresh start section
- [COMPARE.md](COMPARE.md) — DQN phase uses deferred priority on switch
- [FRESH_START.md](FRESH_START.md) — backup + fresh commands
- This changelog

### Scripts

- `scripts/backup_training.py` — copy `.pth`, log, config snapshot (no delete)

---

## 2026-05-22 — 2026-05-29 — Compare, training, and fairness (summary)

These were added or improved earlier in the project; details remain in the linked docs.

| Area | Improvements |
|------|----------------|
| **Fair Compare** | Same fleet for baseline and DQN: record departures → replay XML; drain to **0 vehicles**; validate counts |
| **Inject time** | `compare.inject_seconds` (e.g. **800 s**) → 400+ vehicles; GUI **Inject until (s)** |
| **DQN runaway time** | Cap DQN sim ≈ baseline + `dqn_drain_extra_seconds`; `stall_control_steps`; `dqn_max_green_seconds: 60` |
| **Departure capture** | Micro-step `getDepartedIDList` + lane metadata (fair routes/lanes) |
| **Empty green** | Force switch when green empty and red queued (`switch_min_vehicles`) |
| **Training visibility** | Reports dashboard, `dqn_training_log.jsonl`, `training_summary.py` |
| **Episode limits** | `end_when_clear`, `require_empty_network`, busy snapshots, per-episode seeds |
| **Docs** | [COMPARE.md](COMPARE.md), [TRAINING.md](TRAINING.md), [DQN_PRIORITY.md](DQN_PRIORITY.md) |

### Previous policy era (pre–balanced reward)

- Primary objective: *“Minimize weighted waiting time (transit/bus weighted higher)”*
- `transit_delay_multiplier: 2.5`
- Emergency could **preempt immediately** (skip min green)
- Typical Compare outcome: **better bus/emergency**, **worse all-vehicle wait** vs fixed-time baseline

---

## How to use this log

1. Read the latest section when upgrading config or resetting training.
2. Use [FRESH_START.md](FRESH_START.md) after a **reward** or **priority_service** change.
3. Keep backups under `data/reports/policy_backups/` before `--fresh`.
