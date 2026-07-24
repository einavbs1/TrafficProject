# V6 Camera

**Training:** 6M steps fresh from random weights  
**Key innovation:** Starvation penalty in reward + 100m camera range

## Architecture changes from V4

| Change | V4 | V6-camera |
|--------|-----|-----------|
| Camera range | Full lane | 100m from stop line |
| Starvation in reward | No | **YES** — penalty = max_starvation * 0.05 |
| Starvation threshold | 90s (obs only) | 90s |
| Idle switch penalty | No | No |

## Results (5-seed average, eval_20260701_072958)

| Scenario | PPO V6-camera | Fixed_60s | Gap |
|----------|---------------|-----------|-----|
| Low      | **4.66M**     | 4.61M     | ❌ -1% (almost solved!) |
| Medium   | **26.9M**     | 27.0M     | ✅ +0.5% |
| High     | 67.0M         | 64.3M     | ❌ -4.3% |

Extended metrics (low traffic):
- Switch rate: 5.7/100s vs Fixed_60s 1.7/100s
- Throughput: 708 vehicles arrived vs Fixed_60s 699

**Breakthrough:** Low traffic transformed from 38.6M (V4+6M) to 4.66M.
The starvation penalty gave the agent a non-zero gradient in sparse traffic.

**Regression:** High traffic went from 61.8M (V4) to 67.0M. The 100m camera
range cuts off too early in dense traffic — queues build beyond 100m.

## Why starvation penalty fixes low traffic

In sparse traffic, diff_waiting_time ≈ 0 for most steps (no vehicles = no reward
signal). The starvation penalty fires the moment any vehicle starts waiting:
```
starvation_score = max_consecutive_wait / 90s  (capped at 1.0)
penalty = max(starvation_scores) * 0.05
```
Even 1 vehicle waiting 45s → penalty = -0.025. Non-zero gradient every step
a vehicle exists, so the policy learns to serve isolated vehicles instead of
randomly locking onto one direction.

## Environment

- Reward: `diff_waiting_time - starvation_penalty` (full ground truth)
- Observation: 21-dim, camera-limited to 100m
- STARVATION_THRESHOLD: 90s
- STARVATION_PENALTY_COEF: 0.05
- CAMERA_RANGE: 100m

## Scripts

| File | Purpose |
|------|---------|
| `sumo_rl_env_V6.py` | Original V6 env (no camera range) — kept as reference |
| `train_V6.py` | Original V6 training script — kept as reference |
| `evaluate_V6.py` | Original V6 eval script — kept as reference |
| `sumo_rl_env_V6_camera.py` | **Active** — V6 + 100m camera range |
| `train_V6_camera.py` | **Active** — fresh 6M training |
| `evaluate_V6_camera.py` | **Active** — evaluation with extended metrics |
| `sumo_rl_env.py` | Shim — redirects evaluate_models.py import to camera env |

## How to evaluate

```
cd PPOagent/saved_agents/V6
python evaluate_V6_camera.py --seeds 5
```
