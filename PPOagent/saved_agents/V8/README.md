# V8 — FIRST AGENT TO BEAT ALL BASELINES IN ALL SCENARIOS ✅

**Status:** COMPLETE — 6M steps trained 2026-07-02, model `20260702_011233`  
**Key innovation:** Hard action mask — Switch blocked when intersection is empty

## Architecture changes from V7

| Change | V7 | V8 |
|--------|-----|-----|
| Idle switch penalty | -0.03 (soft) | **Removed** |
| Empty intersection mask | No | **YES — Switch masked when total_visible == 0** |
| Camera range | 150m | 150m (unchanged) |
| Starvation threshold | 45s | 45s (unchanged) |

## Why hard mask beats soft penalty

V7 used `IDLE_SWITCH_PENALTY = 0.03` to discourage switching on empty intersections.
Result: Low traffic stayed at 4.66M, identical to V6-camera. The -0.03 penalty was
absorbed into gradient noise of the large diff_waiting_time signal.

The hard mask is consistent with MIN_GREEN / MAX_GREEN — those are structural
constraints, not penalties. The policy never even sees the forbidden action.
Zero gradient wasted on "don't switch when empty" — the agent simply can't.

```python
def action_masks(self):
    can_keep = self.elapsed_green_time < self.MAX_GREEN
    can_switch = self.elapsed_green_time >= self.MIN_GREEN

    # V8: structurally block Switch on empty intersection
    if self._total_visible == 0:
        can_switch = False

    if not can_keep and not can_switch:
        can_keep = True
    return np.array([can_keep, can_switch], dtype=np.int8)
```

`_total_visible` is already computed in `_compute_observation()` — zero extra TraCI calls.

## Target results

| Scenario | V7 (4.7M) | V8 target | Fixed_60s |
|----------|-----------|-----------|-----------|
| Low      | 4.66M     | **< 4.61M ✅** | 4.61M |
| Medium   | 25.9M     | ~25-26M ✅ | 27.0M |
| High     | 62.2M     | ~61-63M ✅ | 64.3M |

## Results (5-seed average, eval_20260702_053030)

| Scenario | **PPO V8** | Fixed_60s | V7 (prev best) | vs Fixed_60s |
|----------|-----------|-----------|----------------|--------------|
| Low      | **2.29M** | 4.61M     | 4.66M          | ✅ **-50%** |
| Medium   | **17.3M** | 27.0M     | 25.9M          | ✅ **-36%** |
| High     | **59.2M** | 64.3M     | 62.2M          | ✅ **-8%**  |

**First agent in project history to beat every baseline in every scenario.**

Key behavioral change (low traffic):
- Switch rate: **0.4/100s** vs Fixed_60s 1.7/100s — switches only when a real vehicle needs service
- Wait per vehicle: **3,293s** vs Fixed_60s 6,602s (halved)

Why medium/high also improved: the mask removes wasted exploration during
training — every gradient step goes into learning when to switch for real
traffic instead of learning "don't switch at nothing."

Caveat: V8 changed two things vs V7 — the hard mask AND batch_size 256→512.
The mask is almost certainly the driver (the low-traffic behavior matches its
exact mechanism), but strictly both changed.

## Environment

- Reward: `diff_waiting_time - starvation_penalty`
- Observation: 21-dim, camera-limited to 150m
- CAMERA_RANGE: 150m
- STARVATION_THRESHOLD: 45s
- STARVATION_PENALTY_COEF: 0.05
- Empty mask: Switch blocked when total_visible == 0

## Hyperparameters

| Param | Value |
|-------|-------|
| learning_rate | 3e-4 → 0.0 linear |
| ent_coef | 0.02 |
| n_steps | 512 |
| batch_size | 512 |
| n_epochs | 10 |
| gamma | 0.99 |
| num_cpu | 10 (of 12 logical) |
| torch threads | 2 (spare cores) |

## Scripts

| File | Purpose |
|------|---------|
| `sumo_rl_env_V8.py` | Environment with hard empty-intersection mask |
| `sumo_rl_env.py` | Shim for evaluate_models.py import resolution |
| `train_V8.py` | Fresh 6M training |
| `evaluate_V8.py` | Evaluation script |

## How to train and evaluate

```
cd PPOagent/saved_agents/V8
python train_V8.py --timesteps 6000000
python evaluate_V8.py --seeds 5
```
