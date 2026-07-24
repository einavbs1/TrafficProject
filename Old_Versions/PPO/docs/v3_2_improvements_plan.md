# V3.2 Improvements Plan

**Date:** 2026-06-27  
**Base:** V3.1 (cyclic `SwitchOrKeepWrapper`, queue penalty reward)  
**Type:** Resume-compatible — no new agent required  
**Status:** Applied

---

## Context

V3.1 is the best-performing PPO architecture to date (84.7M high-traffic wait vs V4–V6 which were worse). However it still loses to Fixed_60s across all traffic levels, most severely in low traffic (91M vs 4.6M — 20x gap). Four targeted fixes address the root causes without touching the architecture.

---

## Changes Applied

### 1. Entropy coefficient on resume: 0.0 → 0.005
**File:** `src/train_production.py`

The original resume code set `model.ent_coef = 0.0` to "stop exploration." This permanently locked the policy — if the agent converged to a biased behavior (e.g., always-keep on high-traffic), it could never escape. `0.005` is small enough to not destabilize learned weights but large enough to allow continued policy refinement.

### 2. Dynamic effective MIN_GREEN for sparse phases
**File:** `src/sumo_rl_env.py`

**New class constant:**
```python
PHASE_LANES = {
    0: ["n_to_center_3", "s_to_center_3"],
    1: ["n_to_center_1", "n_to_center_2", "s_to_center_1", "s_to_center_2"],
    2: ["e_to_center_3", "w_to_center_3"],
    3: ["e_to_center_1", "e_to_center_2", "w_to_center_1", "w_to_center_2"],
}
```

**In `action_masks()`:** Count vehicles currently in the active phase's lanes. If ≤ 2 vehicles, `effective_min_green = 5s` instead of the standard `MIN_GREEN = 10s`.

- Phases with 0 vehicles: already skipped entirely (existing logic)
- Phases with 1–2 vehicles: now released after 5s (was: held for up to 60s = MAX_GREEN)
- Phases with 3+ vehicles: standard 10s MIN_GREEN (unchanged)

**Why this matters:** In low traffic, 1–2 cars in a phase prevented the skip logic but still forced a full MIN_GREEN window. The agent would sit in an almost-empty phase while queues built in other directions — directly causing the 20x low-traffic performance gap.

**Starvation guarantee:** The phase always gets served (a minimum 5s green), preventing the hours-long waits the user was concerned about.

### 3. Queue penalty coefficient: 0.1 → 0.2
**File:** `src/sumo_rl_env.py`

```python
queue_penalty = (sum_of_queues / num_lanes) * 0.2  # was 0.1
```

In low traffic with 3 stopped cars across 12 lanes, the old reward was `≈ 0.025` — effectively noise. The gradient from good vs bad decisions was indistinguishable. Doubling the coefficient gives clearer learning signal in sparse scenarios without affecting high-traffic stability (where the pressure signal already dominates).

### 4. n_steps: 2048 → 512
**Files:** `src/train_production.py` (new agents + resume)

With 10 parallel envs and 20,000s episodes (4,000 steps/ep):
- Old: `n_steps=2048` → policy updates every 20,480 env steps → <1 update per episode per env
- New: `n_steps=512` → policy updates every 5,120 env steps → ~8 updates per episode per env

On resume, the rollout buffer is rebuilt using `MaskableRolloutBuffer` without touching policy weights.

**Total gradient updates over 2M steps stays ~similar (~78k), but they arrive evenly throughout training instead of in slow large batches.**

---

## What Was NOT Changed

- Architecture: still `SwitchOrKeepWrapper`, Discrete(2), 21-dim obs
- Reward structure: still pressure + queue penalty
- Network size: still [128, 128]
- LR on resume: still 3e-5 constant
- VecNormalize: unchanged (already correctly fit across all 3 traffic scenarios)
- Phase-skip logic for 0-vehicle phases: unchanged

---

## Expected Impact

| Issue | Root cause | Fix |
|-------|-----------|-----|
| Low traffic 20x gap | 1–2 car phases held for up to 60s | Dynamic MIN_GREEN (change 2) |
| Always-keep local optimum | ent_coef=0 blocked exploration | ent_coef=0.005 (change 1) |
| Weak gradient in sparse traffic | Queue penalty too small | 0.1→0.2 (change 3) |
| Slow policy adaptation | 1 update per episode | n_steps 2048→512 (change 4) |

---

## Training Run
Resume from latest checkpoint, 2M additional timesteps, then full 5-seed evaluation.
