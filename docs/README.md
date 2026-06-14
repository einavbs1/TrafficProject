# FlowGrid documentation

Index of project docs for simulation, training, and comparison.

## Core workflows

| Doc | When to read |
|-----|----------------|
| [DQN_HE.md](DQN_HE.md) | **עברית** — איך סוכן ה-DQN עובד ומה המדיניות שלו |
| [COMPARE.md](COMPARE.md) | Running baseline vs DQN, fair traffic, wait metrics, inject time, delay ms |
| [TRAINING.md](TRAINING.md) | Training episodes, resume, log file, how many episodes, Reports dashboard |
| [DQN_PRIORITY.md](DQN_PRIORITY.md) | Buses, emergency, empty-green fairness, reward tuning |
| [FRESH_START.md](FRESH_START.md) | **Backup + `--fresh`** after a big policy change (~20k old-era weights) |
| [CHANGELOG.md](CHANGELOG.md) | **What changed** (reward, priority, compare) — timeline |
| [DEVELOPMENT_STATUS_REPORT.md](DEVELOPMENT_STATUS_REPORT.md) | **Engineering retrospective** — architecture, bug fixes, current DQN state |
| [PORTFOLIO_GUIDE.md](PORTFOLIO_GUIDE.md) | **Portfolio docs** — User's Guide (2.1) + Maintenance Guide (2.2) |
| [GUI.md](GUI.md) | Desktop UI theme, fonts, tabs |

## Suggested reading order

1. **TRAINING.md** — how the agent learns.  
2. **DQN_PRIORITY.md** — what it optimizes (and why Compare can look “mixed”).  
3. **COMPARE.md** — how to run a fair evaluation.

## Other topics worth documenting later

| Topic | Why it matters |
|-------|----------------|
| **Map build / Plan 2 geometry** | Lanes, phases, routes, probabilities — so demand matches real intent |
| **Deployment / real junction** | Shadow mode, detectors, fallback to fixed-time, safety review |
| **Config reference** | Full `dqn_policy_config.yaml` field list |
| **Troubleshooting SUMO** | SUMO_HOME, GUI, TraCI errors, cache folders |

## Key file locations

| Path | Purpose |
|------|---------|
| `data/defaults/dqn_policy_config.yaml` | Reward, training, compare settings |
| `data/reports/dqn_training_log.jsonl` | Training history |
| `data/reports/comparison_history.json` | Saved Compare runs |
| `data/maps/plan_2_opposite_thru_right/dqn_policy.pth` | Learned weights |
| `data/maps/plan_2_opposite_thru_right/.compare_cache/` | Fair compare route files |
| `data/reports/policy_backups/` | Manual backups (`scripts/backup_training.py`) |
| `data/reports/training_archive/` | Files moved by `--fresh` / `reset_training.py` |

## GUI

- **Train** — run learning, stop, checkpoint interval.  
- **Compare** — baseline then DQN; set **Inject until (s)** and **Delay ms**.  
- **Reports** — training curve, compare history (all vehicles + bus + emergency), saved table.
