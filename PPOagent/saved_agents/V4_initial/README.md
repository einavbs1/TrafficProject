# V4 Initial — Best Known Agent Snapshot

Saved: 2026-06-29  
Model ID: 20260628_013031  
Training: 6M steps, fresh from random weights

## Results (5-seed average)

| Scenario | PPO V4 | Fixed_60s | Result |
|----------|--------|-----------|--------|
| Low      | 68M    | 4.6M      | ❌ Losing |
| Medium   | 24.7M  | 27.0M     | ✅ Winning (-9%) |
| High     | 61.8M  | 64.3M     | ✅ Winning (-4%) |

First agent in the project to beat any baseline model.

## Files

| File | Purpose |
|------|---------|
| `ppo_model_V4_initial.zip` | Trained model weights |
| `vec_normalize_V4_initial.pkl` | Observation normalization stats (must be loaded together with the model) |
| `train_production_V4.py` | Exact training script used to produce this agent |
| `sumo_rl_env_V4.py` | Exact environment (diff_waiting_time reward, fixed MIN_GREEN=10) |
| `evaluate_models_V4.py` | Evaluation script |

## Key config for this agent

- Reward: `diff_waiting_time = (prev_total_wait - current_wait) / num_lanes`
- Action masking: MIN_GREEN=10 fixed, MAX_GREEN=60 (no dynamic MIN_GREEN)
- Observation: 21-dim (phase one-hot [4], elapsed [1], demand [8], starvation [8])
- ent_coef: 0.02 | learning_rate: 3e-4 → 0 linear | n_steps: 512 | batch_size: 256

## How to resume training from this snapshot

```
cd PPOagent/src
python train_production.py --resume ..\saved_agents\V4_initial\ppo_model_V4_initial.zip --timesteps 3000000
```

## How to evaluate this snapshot

```
cd PPOagent/src
python evaluate_models.py --model ..\saved_agents\V4_initial\ppo_model_V4_initial.zip --vec-normalize ..\saved_agents\V4_initial\vec_normalize_V4_initial.pkl --seeds 5
```

## Why this was saved

The V4 resume (6M additional steps) regressed performance — medium/high traffic got worse and low traffic collapsed to 495M. This snapshot is the fallback if V5 or future experiments do not beat these results.
