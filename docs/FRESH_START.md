# Fresh DQN training (new policy era)

Use this when the agent was trained for a long time on an **old** objective (e.g. ~20,000 episodes with **2.5× bus-weighted** delay and **instant emergency** preemption) and you want a **clean** network under the **current** `dqn_policy_config.yaml`.

## Do you need fresh?

| Situation | Recommendation |
|-----------|----------------|
| **~20k episodes on old reward** | **`--fresh`** — clearest test of the new policy |
| Small yaml tweak after 500 episodes on new reward | `--resume` |
| Only changed Compare inject time | No retrain; optional cache delete if inject seconds changed |

**Yes — for your case (20k on previous policy), fresh is the right choice.**

---

## Step 1 — Backup (keeps a copy; nothing deleted)

From the project root (`TrafficProject`):

```powershell
cd C:\Users\Einavs_PC\Documents\TrafficProject
python scripts/backup_training.py --label pre_balanced_policy_20k
```

Optional — also copy every `dqn_policy_epNNN.pth` (large):

```powershell
python scripts/backup_training.py --label pre_balanced_policy_20k --all-episode-checkpoints
```

Backup location:

`data/reports/policy_backups/<timestamp>_pre_balanced_policy_20k/`

- `dqn_policy.pth`
- `dqn_policy_objectives.txt`
- `config/dqn_policy_config.yaml`
- `logs/dqn_training_log.jsonl`
- `BACKUP_README.txt`

### Restore old policy later

```powershell
copy data\reports\policy_backups\<YOUR_STAMP_FOLDER>\dqn_policy.pth data\maps\plan_2_opposite_thru_right\dqn_policy.pth
```

---

## Step 2 — Fresh training (archives old checkpoints + new log)

Use **PowerShell in the project folder** so you see every episode line (GUI can freeze on long runs).

### Option A — Auto train → compare → repeat (recommended)

```powershell
cd C:\Users\Einavs_PC\Documents\TrafficProject
python scripts/run_curriculum.py --map plan_2_opposite_thru_right --fresh --episodes-per-cycle 500 --max-cycles 10
```

You will see lines like `[ 12%] Episode 60/500 ...` then cycle summaries with % vs baseline.

### Option B — Train only, then compare yourself

```powershell
python scripts/run_train.py --map plan_2_opposite_thru_right --fresh --episodes 500 --checkpoint-every 10
python scripts/run_compare.py --map plan_2_opposite_thru_right --seed 42 --inject-seconds 800
```

**2,000 episodes (more stable):**

```powershell
python scripts/run_train.py --map plan_2_opposite_thru_right --resume --episodes 2000 --checkpoint-every 50
```

### What `--fresh` does

1. **Moves** (does not delete) old files to `data/reports/training_archive/<timestamp>/`:
   - `dqn_policy.pth`, `dqn_policy_ep*.pth`, objectives text, etc.
2. **Moves** `data/reports/dqn_training_log.jsonl` → `dqn_training_log_<timestamp>.jsonl.bak`
3. Starts training with **ε = 1.0** and a **new** log file

Your **backup** in `policy_backups/` is separate and stays until you remove it.

---

## Step 3 — GUI alternative

1. **Train** tab → uncheck **Resume** (or use terminal `--fresh`).
2. Episodes: start with **500–1000**.
3. Run training.

There is no separate “Fresh” button; use terminal `--fresh` once to archive old weights, or run `python scripts/reset_training.py` then train without `--resume`.

---

## Step 4 — Compare (after first 500+ episodes)

1. **Compare** tab: seed **42**, **Inject until (s)** **800**, delay **0**.
2. Run baseline → DQN.
3. Check all three charts: **all vehicles**, **bus**, **emergency**.

Repeat seeds **43**, **44** when the Reports trend looks good.

You do **not** need to delete `.compare_cache` unless you changed **inject_seconds**.

---

## Milestones (new policy)

| Episodes | What to do |
|----------|------------|
| 500–1,000 | First Compare; check Reports trend |
| 2,000–5,000 | ε → ~0.01; Compare on 3 seeds |
| Flat trend + bad Compare | Tune `transit_priority_scale` in yaml, then **resume** (not another 20k blind) |

---

## Related

- [CHANGELOG.md](CHANGELOG.md) — what changed and when
- [TRAINING.md](TRAINING.md) — training guide
- [DQN_PRIORITY.md](DQN_PRIORITY.md) — reward and bus/emergency behavior
