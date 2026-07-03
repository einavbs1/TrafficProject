# V4 Initial

**Model ID:** 20260628_013031  
**Training:** ~4M steps fresh from random weights  
**Restored from:** `PPOagent/results/eval_20260628_113537/` (original eval snapshot)

## Results (5-seed average, confirmed twice)

| Scenario | PPO V4 | Fixed_60s | Gap |
|----------|--------|-----------|-----|
| Low      | 68.3M  | 4.6M      | ❌ -1385% |
| Medium   | 24.7M  | 27.0M     | ✅ +8.8% |
| High     | 61.8M  | 64.3M     | ✅ +3.9% |

First agent to beat any baseline. Low traffic is structurally unsolvable with
diff_waiting_time alone (near-zero gradient in sparse traffic).

## Additional training runs (from this base)

| Run | Extra steps | Low | Medium | High |
|-----|------------|-----|--------|------|
| +6M steps (equal thirds) | 6M | 38.6M | 23.2M ✅ | 61.8M ✅ |
| +3M low50weighted | 3M | 39.2M | **21.6M ✅** | 61.8M ✅ |

Best combined result: Low=39.2M, Medium=21.6M, High=61.8M

## Environment

- Reward: `diff_waiting_time = (prev_total_wait - current_wait) / num_lanes`
- Observation: 21-dim `[phase(4), elapsed(1), lane_demands(8), lane_starvation(8)]`
- Camera: full lane (no range limit)
- Starvation penalty in reward: NO (starvation only in observation)
- Action masking: MIN_GREEN=10s, MAX_GREEN=60s

## Hyperparameters

| Param | Value |
|-------|-------|
| learning_rate | 3e-4 → 0.0 linear |
| ent_coef | 0.02 |
| n_steps | 512 |
| batch_size | 256 |
| n_epochs | 10 |
| gamma | 0.99 |
| gae_lambda | 0.95 |
| net_arch | [128, 128] Tanh |

## Scripts

| File | Purpose |
|------|---------|
| `sumo_rl_env_V4.py` | Environment (diff_waiting_time, no starvation penalty) |
| `train_V4_initial.py` | Fresh training, equal-thirds routing |
| `train_V4_initial_low50weighted.py` | Resume with 50% low-traffic route probability |
| `evaluate_V4.py` | Evaluation script |

## How to evaluate

```
cd PPOagent/saved_agents/V4_initial
python evaluate_V4.py --seeds 5
```
