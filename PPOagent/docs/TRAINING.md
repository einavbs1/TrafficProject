# FlowGrid — DQN training guide

How training works, how to read progress, and how many episodes are enough.

## What training does

- **Map:** Usually Plan 2 (`plan_2_opposite_thru_right`).
- **Environment:** SUMO + actuated traffic lights; agent chooses **hold** or **advance** phase each control step (20 s of sim time per step).
- **Checkpoint:** `data/maps/<map>/dqn_policy.pth`
- **Log:** `data/reports/dqn_training_log.jsonl`

Training optimizes **reward** (all-vehicle delay + modest bus/emergency extras, fairness, throughput, penalties) — not the same numbers as Compare until the policy is good.

After changing `reward:` or `priority_service:` in `dqn_policy_config.yaml`:

- **Small tweak, already on new policy:** `--resume` 300–500 episodes.
- **~20k episodes on the old 2.5× bus-weighted policy:** use **`--fresh`** — see [FRESH_START.md](FRESH_START.md).

See [CHANGELOG.md](CHANGELOG.md) for what changed between policy eras.

## Starting fresh (new policy era)

When the checkpoint was trained on the **previous** objective (weighted bus delay 2.5×, instant emergency), a **fresh** network is the cleanest experiment.

1. **Backup:** `python scripts/backup_training.py --label pre_balanced_policy_20k`
2. **Train:** `python scripts/run_train.py --map plan_2_opposite_thru_right --fresh --episodes 500 --checkpoint-every 10`

Full steps: [FRESH_START.md](FRESH_START.md).

`--fresh` archives old `.pth` files and rotates the training log; it does **not** delete your backup in `policy_backups/`.

## How to train

**New run:**

```text
python scripts/run_train.py --map plan_2_opposite_thru_right --episodes 500
```

**Continue from checkpoint (recommended):**

```text
python scripts/run_train.py --map plan_2_opposite_thru_right --episodes 500 --resume --checkpoint-every 10
```

Or use the **Train** tab in the GUI.

## GPU / device (DQN only)

The DQN neural network can run on GPU. **SUMO traffic simulation always runs on CPU** and is usually the main bottleneck per episode.

| Hardware | Setting |
|----------|---------|
| NVIDIA | `device: auto` or `device: cuda` (default auto picks CUDA) |
| AMD / Intel on Windows | Install DirectML, then `device: auto` or `device: directml` |

**AMD (e.g. Radeon RX 480) on Windows:**

```powershell
pip install torch-directml
python scripts/check_device.py --device directml
```

Config (`data/defaults/dqn_policy_config.yaml`):

```yaml
training:
  device: auto
```

CLI override:

```text
python scripts/run_train.py --device directml --episodes 500
```

Resolved device is logged at training session start (`data/reports/dqn_training_log.jsonl`) and printed when training from the CLI.

## See progress (without Compare every time)

| Where | What you see |
|-------|----------------|
| **Train tab** | Live episode, reward, ε, wait chart, reward parts |
| **Reports tab** | Training wait trend, compare history table, **auto curriculum** summary |
| **Log file** | `data/reports/dqn_training_log.jsonl` — one line per episode |
| **Curriculum log** | `data/reports/curriculum_log.jsonl` — after each auto cycle |

You do **not** have to run Compare manually after every train block if you use **Auto progress** (below).

## Auto progress (train → compare → repeat)

Runs **automatically**:

1. Train **N** episodes (resume after cycle 1).  
2. Fair **Compare** (same seed / inject as config).  
3. **Analyze** results (all-vehicle wait vs baseline).  
4. Log advice and **repeat** until DQN wins on total wait or **max cycles** is reached.

**GUI:** Train tab → **Auto progress** → set episodes/cycle and max cycles → **Start auto curriculum**.

**CLI (recommended if the GUI freezes)** — run in PowerShell from the project folder; each episode and cycle prints a line:

```powershell
cd C:\Users\Einavs_PC\Documents\TrafficProject

# First time with new policy (archives old .pth + log):
python scripts/run_curriculum.py --map plan_2_opposite_thru_right --fresh --episodes-per-cycle 500 --max-cycles 10

# Continue existing policy:
python scripts/run_curriculum.py --map plan_2_opposite_thru_right --episodes-per-cycle 500 --max-cycles 10
```

**Train only** (one block, live episode lines):

```powershell
python scripts/run_train.py --map plan_2_opposite_thru_right --resume --episodes 500 --checkpoint-every 10
```

(`--fresh` once, then drop `--fresh` and keep `--resume` for later runs.)

**Train + compare once** (two steps in one command; episode lines, then compare progress):

```powershell
# First time (new policy era):
python scripts/run_train_then_compare.py --map plan_2_opposite_thru_right --fresh --episodes 500 --checkpoint-every 10 --compare-seed 42 --inject-seconds 800

# Continue from checkpoint:
python scripts/run_train_then_compare.py --map plan_2_opposite_thru_right --resume --episodes 500 --checkpoint-every 10 --compare-seed 42 --inject-seconds 800
```

Or use the PowerShell wrapper (same folder):

```powershell
.\scripts\powershell\train_and_compare.ps1 -Fresh
.\scripts\powershell\train_and_compare.ps1 -Resume
.\scripts\powershell\train_and_compare.ps1 -Curriculum -Fresh   # train+compare loop, many cycles
```

**Compare only** (after training):

```powershell
python scripts/run_compare.py --map plan_2_opposite_thru_right --seed 42 --inject-seconds 800
```

Settings in `data/defaults/dqn_policy_config.yaml` under `curriculum:` (seed, inject seconds, stop threshold).

**Stop when:** `improvement_percent_all >= stop_when_all_improvement_pct` (default `0` = DQN wait ≤ baseline).

### Resume / fine-tune

- `--resume` loads existing `dqn_policy.pth` (weights + **saved ε**). It does **not** jump ε back to 0.2 anymore.
- Checkpoints store cumulative `episodes_done`, `steps_done`, `epsilon`, and `epsilon_decay`. `--resume` restores all of these; training fails immediately if the checkpoint is missing or corrupt (no silent reset to ε=1.0).
- Legacy `.pth` files (weights only): ε is restored from the last line of `dqn_training_log.jsonl` when possible.
- `fine_tune.preserve_epsilon: true` in `dqn_policy_config.yaml` — use `--fresh` only to start a new network from scratch.
- Training log `wait=` is a **sum over steps**; also watch `mean_step=` (average congestion per control step). **Compare** is the fair score for all-vehicle wait vs baseline.

## Recovery after gridlock (collapsed policy)

If Compare shows **INVALID COMPARE**, `model_error` (vehicles left on map), or DQN all-vehicle wait **much worse** than baseline (~159k on seed 42):

1. **Do not** keep `--resume` on the collapsed `dqn_policy.pth`.
2. **Backup:** `python scripts/backup_training.py --label before_fresh_fix`
3. **Fresh start** with the current reward config:

```powershell
cd C:\Users\Einavs_PC\Documents\TrafficProject
python scripts/run_train_then_compare.py --map plan_2_opposite_thru_right --fresh --episodes 500 --checkpoint-every 10 --compare-seed 42 --inject-seconds 800
```

**Success gates (use these, not training `wait` alone):**

| Gate | Target |
|------|--------|
| Compare | No `INVALID COMPARE`; `model_error` empty |
| All-vehicle wait | DQN ≤ baseline (~159k on seed 42) |
| Training | Some episodes end with `end=drained`, not 100% `max_time` |
| Generalization | Compare seeds 43 and 44 after seed 42 passes |

**Safeguards (automatic):**

- Best fair Compare is saved as `dqn_policy_best.pth` next to the map policy.
- Catastrophic Compare (error or DQN wait > 2× baseline) **rolls back** to `dqn_policy_best.pth` when it exists.
- Auto curriculum **stops** on catastrophic Compare instead of training further.

Verify checkpoint loading: `python scripts/verify_checkpoint_load.py`

## Episode design (training)

| Setting | Meaning |
|---------|---------|
| `episode_training.min_sim_seconds` | Minimum time before “drain” can end the episode |
| `episode_training.max_sim_seconds` | Safety cap (often 2400 s sim) |
| `busy_fraction` | Fraction of episodes that start from a **busy snapshot** (pre-loaded queue) |
| `end_when_clear` | Episode can end when the junction drains (training uses cohort + queue rules) |

Training episodes often end with reason **`max_time`** — that is normal when the cap is hit before the map fully clears.

## Reading progress

### Reports tab → **Training progress (DQN)**

- **Green line:** total wait per episode (from the training log).
- **Yellow line:** moving average (trend).
- **Text block:** episode count, ε, first-100 vs last-100 average wait, end reasons, **recommendation**.

### Log file (`dqn_training_log.jsonl`)

Each episode line includes:

| Field | Meaning |
|-------|---------|
| `episode` | Episode number in this session |
| `total_wait` | Sum of lane waiting time over the episode (all vehicles) |
| `reward_total` | Scalar reward (higher is better) |
| `reward_components` | spillback, delay_delta, throughput, fairness, … |
| `epsilon` | Exploration rate (→ 0.01 when nearly done exploring) |
| `ended_reason` | e.g. `max_time`, `drained` |

## How many episodes?

There is **no fixed “pro” number**. Use milestones:

| Stage | Episodes (rough) | What to check |
|-------|------------------|---------------|
| First Compare (fresh policy) | 500 | Often **worse than baseline** — normal; network is still learning |
| First usable policy | **1,500–2,500** | Compare without errors; trend down in Reports |
| Stable sim behavior | 2,000–5,000+ | Training wait trend down; ε ≈ 0.01 |
| Match or beat baseline | — | **Compare** on seeds 42, 43, 44: green on **all vehicles** chart |

Your log may already show **5,000+** episodes — that is a lot for simulation. If Compare still loses on **total wait**, train **more only if the Reports trend is still improving**. If the trend is flat, tune **reward** (see [DQN_PRIORITY.md](DQN_PRIORITY.md)), not only episode count.

**Practical target (new policy, after `--fresh`):** **500–1,000 episodes**, then **Compare** on seeds 42, 43, 44. If all-vehicle wait still loses, tune `transit_priority_scale` / `emergency_priority_scale` before training another 5,000 episodes.

**Previous era (~20k episodes, old reward):** resume alone often keeps bus-heavy habits — prefer **fresh** (above).

## Training vs Compare (different goals)

| | Training | Compare |
|---|----------|---------|
| Traffic | Random / busy starts | Baseline random inject → **replay exact fleet** for DQN |
| Controller test | DQN only | Baseline **and** DQN |
| Success | Reward ↑, wait ↓ in log | DQN **lower wait** than baseline on same fleet |

Compare did **not** break training. Fair compare can show DQN **worse on total wait** while **better on buses/emergency** — that reflects **reward priority**, not a broken inject.

## Config files

- `data/defaults/dqn_policy_config.yaml` — reward, constraints, compare, episode limits
- `data/maps/plan_2_opposite_thru_right/dqn_policy_objectives.txt` — copy of objectives next to the checkpoint

## Related docs

- [COMPARE.md](COMPARE.md) — fair baseline vs DQN
- [DQN_PRIORITY.md](DQN_PRIORITY.md) — buses, emergency, empty green
- [FRESH_START.md](FRESH_START.md) — backup + fresh commands
- [CHANGELOG.md](CHANGELOG.md) — policy change history
- [README.md](README.md) — doc index
