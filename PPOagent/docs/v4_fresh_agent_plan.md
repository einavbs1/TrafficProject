# V4 Agent — Fresh Training Plan

**Date:** 2026-06-28  
**Status:** Implementing  
**Goal:** PPO agent must achieve lower total waiting time than all baselines

---

## Root Cause of V3.3 Collapse

V3.3 added a dynamic MIN_GREEN: if the current phase had ≤2 vehicles AND total_queued < 10, the agent could switch at 5s instead of 10s.

**The fatal flaw:** when a phase is GREEN and serving vehicles, those vehicles are *moving* — not halting. So `getLastStepVehicleNumber` for the current phase = near-zero (vehicles have already passed through), satisfying the ≤2 condition almost always. Combined with other phases having < 10 halting (they had 8-9, just below the threshold), the agent could switch at 5s in heavy traffic. Over 2M training steps it learned to exploit this: skip left-turn phases (0, 2) after exactly 5s, hold straight phases for 60s. Left-turn vehicles waited 17,000+ seconds.

V3.3 training on top of an already-degraded V3.2 policy produced total collapse: 899M/932M/963M waiting time.

---

## V4 Changes

### 1. Remove dynamic MIN_GREEN (the root fix)
`SwitchOrKeepWrapper.action_masks()` now always enforces `MIN_GREEN=10`. No threshold checks, no vehicle counting. Simple and correct.

### 2. Reward: diff_waiting_time (directly aligned with evaluation)
Replace pressure/queue_penalty reward with the decrease in accumulated waiting time:
```
reward = (prev_accumulated_wait - current_accumulated_wait) / num_lanes
```
This is directly what the evaluation measures (integral of queue length over time). The training gradient now pushes the agent to minimize exactly the metric we care about.

Previously: pressure reward could be positive even when vehicles were queueing (if outgoing > incoming). The misalignment allowed the agent to optimize for throughput at the intersection exit, not overall wait minimization.

### 3. Fresh training — no resume
The V3.3 weights are poisoned. We start from scratch:
- LR: 3e-4 → 0 linear decay over 6M steps
- ent_coef: 0.02 (higher exploration than V3.1's 0.01)
- n_steps: 512, batch_size: 256
- n_epochs: 10, gae_lambda: 0.95, clip_range: 0.2, target_kl: 0.03
- VecNormalize: norm_obs=True, norm_reward=False, clip_obs=10
- 10 parallel envs, MultiRouteWrapper (low/medium/high mixed per episode)

---

## What stays the same as V3.1

- SwitchOrKeepWrapper architecture (cyclic Discrete(2), MIN_GREEN=10, MAX_GREEN=60)
- 21-dim observation (phase one-hot + elapsed + 8 lane demands + 8 starvation scores)
- Ghost Car Logic, phase skipping
- Custom yellow transitions
- SubprocVecEnv with 10 workers
- MultiRouteWrapper curriculum

---

## Expected Outcome

| Model         | Low Traffic | Medium Traffic | High Traffic |
|---------------|-------------|----------------|--------------|
| Fixed_60s     | ~4.6M       | ~27M           | ~64M         |
| Fixed_45s     | ~TBD        | ~TBD           | ~80M         |
| Fixed_30s     | ~TBD        | ~TBD           | ~126M        |
| Max_Pressure  | TBD (fixed) | TBD (fixed)    | TBD (fixed)  |
| **V4 PPO**    | **< 4.6M**  | **< 27M**      | **< 64M**    |

---

## Training Command
```
cd C:\Users\Einavs_PC\Documents\TrafficProject\PPOagent\src
python train_production.py --newAgent --timesteps 6000000
```
