# How the PPO Agent Learns — Monitoring & Progress Guide

---

## 1. What the Agent Sees (Observation — 21 numbers)

Every 5 simulation seconds the agent receives a 21-number snapshot of the intersection. This is everything it knows.

| Index | Name | What it means | Range |
|-------|------|--------------|-------|
| 0–3 | **Phase one-hot** | Which phase is currently green (e.g. [0,1,0,0] = phase 1 active) | 0 or 1 |
| 4 | **Elapsed time** | How long the current phase has been green, normalized by MAX_GREEN (60s) | 0.0 – 1.0 |
| 5 | N-Left demand | Vehicles in N→E left-turn lane / lane capacity | 0.0 – 1.0 |
| 6 | N-Straight demand | Vehicles in N→S straight lanes / capacity | 0.0 – 1.0 |
| 7 | E-Left demand | Vehicles in E→S left-turn lane / capacity | 0.0 – 1.0 |
| 8 | E-Straight demand | Vehicles in E→W straight lanes / capacity | 0.0 – 1.0 |
| 9 | S-Left demand | Vehicles in S→W left-turn lane / capacity | 0.0 – 1.0 |
| 10 | S-Straight demand | Vehicles in S→N straight lanes / capacity | 0.0 – 1.0 |
| 11 | W-Left demand | Vehicles in W→N left-turn lane / capacity | 0.0 – 1.0 |
| 12 | W-Straight demand | Vehicles in W→E straight lanes / capacity | 0.0 – 1.0 |
| 13 | N-Left starvation | How long the longest-waiting vehicle in N-Left has waited / 90s | 0.0 – 1.0 |
| 14–20 | Starvation (other 7 groups) | Same as above for each lane group | 0.0 – 1.0 |

**Key insight:** Demand tells the agent HOW MANY vehicles are waiting. Starvation tells the agent HOW LONG they have been waiting. Together, these let the agent distinguish "5 new vehicles just arrived" from "5 vehicles stuck for 3 minutes."

---

## 2. What the Agent Does (Actions)

The agent picks one of 2 actions every 5 seconds:

- **Action 0 — KEEP**: Hold the current green phase for another 5 seconds
- **Action 1 — SWITCH**: Trigger yellow (3s) then advance to the next phase in the cycle

**Phase cycle:** 0 (N/S Left) → 1 (N/S Straight) → 2 (E/W Left) → 3 (E/W Straight) → back to 0

**Action masking (hard limits the agent cannot break):**
- Cannot SWITCH before 10s green (MIN_GREEN) — prevents rapid flicker
- Cannot KEEP after 60s green (MAX_GREEN) — prevents one direction monopolizing

**Phase skipping (automatic, not the agent's decision):**
If the next phase has zero vehicles in all its lanes, it is automatically skipped. The agent never wastes 10s on a completely empty phase.

---

## 3. What the Agent Feels (Reward)

After every action the agent receives a reward signal:

```
reward = (accumulated_wait_BEFORE_step − accumulated_wait_AFTER_step) / num_lanes
```

- Always ≤ 0 (accumulated wait can only increase over time)
- **Close to 0** = vehicles are flowing freely, little new waiting accumulated
- **Large negative** = many vehicles sat at red during this 5-second window

**Why this reward?** It is exactly what the evaluation measures — total cumulative waiting time. Training directly on the evaluation metric means there is no gap between "what the agent optimizes" and "what we care about."

**Known weakness:** In low traffic with few vehicles, the reward is nearly 0 for every action. The agent gets almost no gradient to learn from. This is why low-traffic performance lags behind.

---

## 4. How the Agent Learns (PPO Mechanics)

### The learning loop

1. **Collect experience:** 10 SUMO environments run in parallel. Each environment steps for 512 time-steps (= 512 × 5s = 2,560 simulation seconds). This gives 10 × 512 = 5,120 (observation, action, reward) tuples per batch.

2. **Compute advantage:** For each step, compute how much better or worse the actual reward was compared to what the value function expected. Positive advantage = "this action worked better than expected." Negative advantage = "worse than expected."

3. **Update the policy:** Gradient descent on the neural network. The network learns to prefer actions with positive advantage and avoid actions with negative advantage. The PPO clip (0.2) limits how aggressively each update can change the policy — prevents catastrophic forgetting.

4. **Repeat:** After 10 epochs of updates on the same batch, collect the next batch of experience.

### The neural network

```
Input (21 numbers)
    ↓
Hidden layer [128 neurons, Tanh]
    ↓
Hidden layer [128 neurons, Tanh]
    ↓
Policy head: 2 logits (Keep / Switch)   +   Value head: 1 number
```

The **policy head** says how likely each action is. The **value head** estimates the expected future return from this state — this is used to compute the advantage.

### Key hyperparameters that control learning

| Parameter | Current value | What it controls |
|-----------|--------------|-----------------|
| `learning_rate` | 3e-4 → 0 (fresh) / 3e-5 (resume) | How big each gradient step is. Too high = unstable. Too low = slow. |
| `ent_coef` | 0.02 (fresh) / 0.01 (resume) | Entropy bonus — how much the agent is encouraged to explore rather than commit. Higher = more random, more discovery. |
| `n_steps` | 512 | Steps collected per env before each update. Lower = more frequent updates but noisier. |
| `gamma` | 0.99 | How much the agent values future rewards vs immediate. 0.99 = cares deeply about long-term. |
| `gae_lambda` | 0.95 | Balance between bias and variance in advantage estimation. |
| `clip_range` | 0.2 | Maximum policy change per update. Prevents collapse. |
| `target_kl` | 0.03 | Early stops an epoch if the policy changed too much — extra safety on top of clip. |

---

## 5. What to Monitor During Training

### From the training console (printed every rollout)

| Metric | Good sign | Bad sign |
|--------|-----------|---------|
| `explained_variance` | Trending toward 0.9–1.0 | Stuck near 0 or going negative — value function not learning |
| `entropy_loss` | Slowly decreasing (agent becomes more decisive) | Drops to 0 immediately (agent locked in too early) |
| `policy_gradient_loss` | Small magnitude, stable | Large spikes — learning rate too high |
| `value_loss` | Decreasing over time | Growing or oscillating |
| `approx_kl` | Stays below target_kl (0.03) | Consistently hitting target — updates too aggressive |

**What to do if explained_variance is stuck near 0:**
The value function can't predict returns. Possible causes: reward scale too large/small, reward too sparse, learning rate too high.

### From evaluation results (run after training)

These are the only numbers that truly matter:

| What to look at | Target |
|----------------|--------|
| **Total_Wait_Time per scenario** | Lower than Fixed_60s in ALL three: Low < 4.6M, Medium < 27M, High < 64M |
| **Peak_Max_Wait_s** | Should stay below ~200s. Spikes above 500s indicate starvation of some direction |
| **Seed variance** | Low variance = converged policy. High variance (e.g. 39M vs 94M for same scenario) = not converged yet |
| **Total_Switches** | Should be roughly 300–450 per episode. Much higher = over-switching. Much lower = holding phases too long |

---

## 6. Current Status & What to Watch For

### V4 Resume (in progress)

The agent already beats Fixed_60s on medium and high traffic. The open question is low traffic.

**Watch for in evaluation results:**
- Low traffic Total_Wait_Time dropping below 27M (approaching Fixed_60s territory)
- Low traffic seed variance narrowing (all seeds in similar range, not 39M vs 94M)

**If low traffic improves → done.** The agent is the winner.

**If low traffic stays the same despite more steps** → the diff_waiting_time reward has too weak a gradient in sparse conditions. Next step: fresh V5 agent with pressure reward (stronger signal in sparse traffic) + same fixed action masking.

---

## 7. Quick Reference — Do We Need a Fresh Agent?

| Change | Fresh agent? |
|--------|-------------|
| More training steps | No — just resume |
| `ent_coef`, `learning_rate` tweak | No — resume with new values |
| Reward function change | **YES — fresh agent** |
| Observation change (what/how many inputs) | **YES — fresh agent** |
| Action masking change | No — masking is external to weights |
| `n_steps`, `batch_size` change | No — resume (rebuild rollout buffer) |
