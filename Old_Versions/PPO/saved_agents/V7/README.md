# V7

**Status:** COMPLETE at 4.7M steps (model `20260701_133743`, restored from checkpoint)  
**Key innovations:** Starvation fires earlier (45s) + wider camera (150m) + idle switch penalty  
**Superseded by:** V8 (hard mask instead of idle switch penalty)

## Architecture changes from V6-camera

| Change | V6-camera | V7 |
|--------|-----------|-----|
| Camera range | 100m | **150m** |
| Starvation threshold | 90s | **45s** |
| Starvation coef | 0.05 | 0.05 (unchanged) |
| Idle switch penalty | No | **0.03 when intersection empty** |

### Why each change

**150m camera** — In dense traffic, vehicle queues extend beyond 100m. V6-camera
was blind to building congestion far from the intersection, causing high traffic
to regress from V4 (67M vs 61.8M). 150m captures the full near-intersection queue
in all traffic scenarios without reverting to omniscient full-lane visibility.

**45s starvation threshold** — At 90s, a vehicle waiting 15s only scores 0.17
(penalty = 0.008). Lowering to 45s doubles the signal strength at any wait time.
A vehicle waiting 15s now scores 0.33 (penalty = 0.016), giving the policy a
clearer gradient to act on isolated vehicles before they reach critical wait times.

**Idle switch penalty (0.03)** — When the camera sees zero vehicles in all lane
groups and the agent switches, it wastes 3 seconds of yellow dead time for zero
benefit. V6-camera got to within 1% of Fixed_60s on low traffic; this penalty
directly closes that gap by discouraging pointless phase switches on empty roads.
Implemented with zero extra TraCI calls (reuses cached `_total_visible`).

## Target results

| Scenario | V6-camera | V7 target | Fixed_60s |
|----------|-----------|-----------|-----------|
| Low      | 4.66M     | **< 4.61M ✅** | 4.61M |
| Medium   | 26.9M     | **~24-26M ✅** | 27.0M |
| High     | 67.0M     | **~61-63M ✅** | 64.3M |

## Results (5-seed average, 4.7M steps, eval_20260701_214417)

| Scenario | PPO V7 | Fixed_60s | Gap |
|----------|--------|-----------|-----|
| Low      | 4.66M  | 4.61M     | ❌ -1% (same as V6 — penalty did nothing) |
| Medium   | **25.9M** | 27.0M  | ✅ +4.1% |
| High     | **62.2M** | 64.3M  | ✅ +3.2% |

150m camera FIXED the V6 high-traffic regression (67.0M → 62.2M).
The -0.03 idle switch penalty FAILED (too weak) — led to V8's hard mask.

## Resume incident (2026-07-02)

Training crashed at 4.7M before saving VecNormalize stats. A resume run
silently rebuilt fresh stats → observation distribution shift → policy
collapse (Low 35.4M / Med 62.1M / High 77.0M at 5.9M steps). The good 4.7M
checkpoint was restored from `checkpoints/`. All training scripts now save
stats with every checkpoint, refuse to resume without matching stats, and
auto-recover from crashes.

## Environment

- Reward: `diff_waiting_time - starvation_penalty - idle_switch_penalty`
- Observation: 21-dim, camera-limited to 150m
- CAMERA_RANGE: 150m
- STARVATION_THRESHOLD: 45s
- STARVATION_PENALTY_COEF: 0.05
- IDLE_SWITCH_PENALTY: 0.03

## Hyperparameters (same as V4/V6)

| Param | Value |
|-------|-------|
| learning_rate | 3e-4 → 0.0 linear |
| ent_coef | 0.02 |
| n_steps | 512 |
| batch_size | 256 |
| n_epochs | 10 |
| gamma | 0.99 |
| net_arch | [128, 128] Tanh |
| route weighting | Equal thirds (33/33/33%) |

## Scripts

| File | Purpose |
|------|---------|
| `sumo_rl_env_V7.py` | Environment with all 3 V7 changes |
| `sumo_rl_env.py` | Shim for evaluate_models.py import resolution |
| `train_V7.py` | Fresh 6M training |
| `evaluate_V7.py` | Evaluation with extended metrics |

## How to train and evaluate

```
cd PPOagent/saved_agents/V7
python train_V7.py --timesteps 6000000
python evaluate_V7.py --seeds 5
```
