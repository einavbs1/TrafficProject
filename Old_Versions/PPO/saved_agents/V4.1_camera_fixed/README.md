# V4.1 Camera Fixed

**Status:** Training queued (runs after V7 completes)  
**Base:** V4 architecture + 100m camera range  
**Purpose:** Isolate camera range effect — does limiting observation to 100m help WITHOUT starvation penalty?

## Architecture changes from V4

| Change | V4 | V4.1 |
|--------|-----|------|
| Camera range | Full lane | 100m from stop line |
| Starvation in reward | No | No |
| Starvation in observation | Yes (full lane) | Yes (100m only) |
| Ghost car logic | Full lane count | 100m count |

## Results

*Pending — training not yet run.*

## Hypothesis

The camera range alone (without starvation penalty) should NOT fix low traffic,
because the gradient problem (reward ~0 in sparse traffic) is in the reward signal,
not the observation. This run serves as a controlled experiment to confirm
that the starvation penalty (V6/V7) is the real driver of improvement.

## Environment

- Reward: `diff_waiting_time` (full ground truth, no starvation penalty)
- Observation: 21-dim, camera-limited to 100m
- CAMERA_RANGE: 100m

## Scripts

| File | Purpose |
|------|---------|
| `sumo_rl_env_V4_1_camera.py` | Environment with 100m camera range |
| `sumo_rl_env.py` | Shim — redirects evaluate_models.py import to camera env |
| `train_V4_1_camera.py` | Fresh 6M training |
| `evaluate_V4_1_camera.py` | Evaluation script |

## How to train and evaluate

```
cd PPOagent/saved_agents/V4.1_camera_fixed
python train_V4_1_camera.py --timesteps 6000000
python evaluate_V4_1_camera.py --seeds 5
```
