# V3.3 Improvements Plan

**Date:** 2026-06-27  
**Status:** Implemented, pending training  
**Based on:** Post-V3.2 evaluation analysis  

## What V3.2 showed

V3.2 (ent_coef 0.005 + dynamic MIN_GREEN at ≤2 vehicles + queue_penalty 0.2 + n_steps 512)
trained for 2M steps produced:

| Scenario     | Before (V3.2 start) | After V3.2 training | Change |
|--------------|---------------------|---------------------|--------|
| Low traffic  | 91.5M               | 49.4M               | ↓ 46% ✅ |
| Medium       | 54.1M               | 67.8M               | ↑ 25% ❌ |
| High         | 84.8M               | 125.1M              | ↑ 47% ❌ |

Low traffic improved as intended. Medium and high traffic degraded significantly.

## Root Cause Analysis

### PPO high/medium traffic regression — two causes

**Cause 1: Dynamic MIN_GREEN triggering in high traffic.**
The ≤2-vehicle threshold checks only the *current phase's lanes*, not the whole
intersection. In high-traffic scenarios, left-turn lanes (phases 0 and 2) frequently
have ≤2 vehicles because left turns are a minority of total flow. This caused:
- Phase 0 / phase 2 released after just 5s even while many vehicles wait for phase 1/3
- Left-turn vehicles get inadequate service → accumulated wait compounds quadratically
- More frequent switches → more yellow time overhead

**Fix:** Add a system-wide total-queue guard. Only trigger the 5s early release when
BOTH the current phase has ≤2 vehicles AND total halted vehicles across all lanes < 10.
This confines the early-release to genuinely sparse conditions.

**Cause 2: Queue penalty 0.2 too aggressive in high-traffic training.**
With penalty=0.2 and many stopped cars, the reward gradient in high traffic pushes the
agent toward frequent phase cycling to clear instantaneous queues. This is suboptimal:
rapid cycling wastes 3s per yellow transition and hurts bulk throughput. 
Reverting to 0.1 restores a balanced reward signal across all traffic levels.

### Max Pressure still broken for 4 of 5 seeds

**Root cause:** The MP evaluator's main loop never re-asserts the traffic-light state
between switches. SUMO runs an internal TL program that overrides our manually-set
state when its timer advances. PPO's SwitchOrKeepWrapper re-asserts the state at every
5-second decision step (once per keep call). MP only sets the state on switch, so SUMO's
internal program overrides it in the multi-second hold windows, producing arbitrary
phase oscillations and catastrophic gridlock.

**Fix:** Add `sumo.trafficlight.setRedYellowGreenState(ts_id, GREEN_STATES[current_phase])`
at the top of the MP main loop — identical to what SwitchOrKeepWrapper does every step.
This is a bug fix in evaluation infrastructure, not a change to the MP greedy algorithm.

## Changes Applied (V3.3)

### 1. evaluate_models.py — MP correct pressure metric
`getLastStepVehicleNumber` counted all vehicles including ones already moving through
on green. A green phase was always measured as "busy", so MP never wanted to leave it.
Changed to `getLastStepHaltingNumber` — counts only queued/stopped vehicles. When a
phase has served its queue (halting → 0), its pressure drops and MP correctly switches.

### 2. evaluate_models.py — MP dynamic MIN_GREEN
When current phase has 0 halting vehicles (queue cleared), allow switch after 5s
instead of holding the full 10s MIN_GREEN:
```python
current_halting = pressures[current_phase]
effective_min = 5 if current_halting == 0 else MIN_GREEN
```

### 3. evaluate_models.py — MP TL state re-assertion
```python
while sim_time < sim_end:
    # Re-assert current green state every decision window.
    sumo.trafficlight.setRedYellowGreenState(ts_id, GREEN_STATES[current_phase])
    pressures = get_mp_pressures(sumo)
    ...
```

### 2. sumo_rl_env.py — Dynamic MIN_GREEN total-queue guard
```python
total_queued = sum(
    self._sumo.lane.getLastStepHaltingNumber(lane)
    for lanes in self.PHASE_LANES.values()
    for lane in lanes
)
effective_min_green = (
    5 if (current_vehicles <= 2 and total_queued < 10) else self.MIN_GREEN
)
```

### 3. sumo_rl_env.py — Queue penalty reverted 0.2 → 0.1
The 0.2 coefficient proved too aggressive in high-traffic training.

## What stays from V3.2

- ent_coef = 0.005 on resume (entropy fix — keep, it's working)
- n_steps = 512 (faster gradient feedback — keep)
- Resume from last checkpoint — no restart

## Expected outcome

- Low traffic: should retain most of the 46% improvement (dynamic MIN_GREEN still fires
  in sparse conditions when total_queued < 10)
- High/medium traffic: should recover toward pre-V3.2 levels (≥ 84.8M high, ≥ 54.1M med)
- Max Pressure: should now work consistently across all seeds
