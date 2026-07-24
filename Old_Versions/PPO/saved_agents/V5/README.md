# V5 — Pressure Reward Agent

## What changed from V4

| What | V4 | V5 |
|------|----|----|
| Reward | `diff_waiting_time` | **Pressure** |
| Reward formula | `(prev_wait - curr_wait) / num_lanes` | `(red_halting - green_halting) / num_lanes - total_halting/num_lanes*0.1` |
| Low-traffic gradient | Near-zero (sparse reward) | Non-zero even with 1 halting vehicle |
| Training | Fresh from scratch | **Fresh from scratch** (reward change → must be fresh) |
| Everything else | — | Identical: 21-dim obs, MIN_GREEN=10 fixed, ghost car logic, 10 parallel envs |

## Why pressure?

V4 resume failed on low traffic (495M vs Fixed_60s 4.6M) because `diff_waiting_time` is nearly zero
in sparse traffic — the agent received almost no gradient signal in low-traffic episodes.

Pressure counts halting vehicles directly. Even 1 car waiting at a red lane → reward = ~0.08 (non-zero).
The agent can learn even in nearly-empty conditions.

## Output folders

| Folder | Contents |
|--------|---------|
| `models/` | Trained model `.zip` + `vec_normalize_*.pkl` + safety backups |
| `checkpoints/` | Intermediate checkpoints every 100k steps |
| `results/` | Evaluation results vs Fixed_30s/45s/60s and Max Pressure |

## How to train

```
cd PPOagent/src
python train_V5.py --timesteps 6000000
```

Automatically resumes from `V5/models/` if a model exists there.
For a guaranteed fresh start: delete `V5/models/*.zip` first.

## How to evaluate

```
cd PPOagent/src
python evaluate_V5.py --seeds 5
```

## How to train then auto-evaluate (one command)

```
cd PPOagent/src
python train_V5.py --timesteps 6000000 ; python evaluate_V5.py --seeds 5
```

## Targets to beat

| Scenario | Fixed_60s | Must beat |
|----------|-----------|-----------|
| Low      | 4.6M      | < 4.6M    |
| Medium   | 27.0M     | < 27.0M   |
| High     | 64.3M     | < 64.3M   |

V4 initial already beats Medium (24.7M) and High (61.8M). V5 needs to fix Low traffic.
