# Max Pressure Baseline Fix

**Date:** 2026-06-27  
**File:** `PPOagent/src/evaluate_models.py` — `evaluate_mp_on_seed()`  
**Status:** Applied

---

## Problem

The Max Pressure baseline evaluation was producing catastrophically wrong results:

| Scenario     | MP Peak Wait | Fixed_60s Peak Wait |
|--------------|-------------|----------------------|
| Low traffic  | 19,530 s    | 183 s                |
| Medium       | 19,353 s    | 180 s                |
| High         | 14,818 s    | 180 s                |

The MP total wait was ~1.7 **billion** seconds vs Fixed_60s at ~4.6 **million** — a 365× gap that made the benchmark meaningless. Comparisons against PPO were invalid.

---

## Root Cause Analysis

### Bug 1 — No MAX_GREEN enforcement (critical)

The while-loop condition to switch was:

```python
if best_phase != current_phase and elapsed_green >= MIN_GREEN:
```

If `best_phase == current_phase` (MP always thinks the current phase is best), the phase **never switches**. In low-traffic scenarios, the straight-through phase (phase 1: N/S straight) typically has the most vehicles, so MP would hold it indefinitely and starve left-turn and E/W phases completely.

With `sim_max_time = 20,000 seconds` (sumo_rl default), a vehicle entering a left-turn lane could sit through the entire simulation, producing ~19,000s wait times.

**This is a physical constraint violation, not an algorithmic decision.** `MAX_GREEN = 60s` is a fundamental safety constraint (same value enforced in the PPO wrapper via action masking).

### Bug 2 — Yellow state never applied

`_apply_yellow_then_green` stepped the simulation without changing the traffic light state:

```python
def _apply_yellow_then_green(from_phase, to_phase, elapsed_seconds):
    steps_elapsed = elapsed_seconds
    while steps_elapsed < YELLOW_TIME:
        sumo.simulationStep()   # light still showing old green
        sim_time += 1
        steps_elapsed += 1
    sumo.trafficlight.setRedYellowGreenState(ts_id, GREEN_STATES[to_phase])
```

The light went directly green→green with no yellow warning. This violates physical constraints (`YELLOW_TIME = 3s`) and may cause incorrect SUMO vehicle behavior at the intersection.

### Bug 3 — Double SUMO query per step

```python
best_phase = max(get_mp_pressures(sumo), key=get_mp_pressures(sumo).get)
```

`get_mp_pressures` was called twice per iteration, reading SUMO state twice unnecessarily.

### Bug 4 — Dead code `YELLOW_STATES` dict

A `YELLOW_STATES` dict was defined but never used anywhere in the function (the yellow logic didn't reference it). Additionally, one entry had the wrong length (15 chars instead of 16).

---

## Fix Applied

### 1. Added MAX_GREEN = 60 enforcement

```python
force_switch = elapsed_green >= MAX_GREEN
want_switch  = best_phase != current_phase and elapsed_green >= MIN_GREEN

if force_switch or want_switch:
    # When forced, pick the highest-pressure phase that isn't current
    if force_switch and best_phase == current_phase:
        best_phase = max(
            (p for p in pressures if p != current_phase),
            key=pressures.get
        )
    _apply_yellow_then_green(current_phase, best_phase)
```

When forced, the algorithm still selects the highest-pressure OTHER phase — staying true to the greedy Max Pressure spirit while respecting the physical constraint.

### 2. Fixed yellow transition

Added `_compute_yellow_state` (same logic as `SwitchOrKeepWrapper`):

```python
def _compute_yellow_state(from_state, to_state):
    yellow = []
    for f, t in zip(from_state, to_state):
        if f.lower() in ('g', 'y') and t == 'r':
            yellow.append('y')
        else:
            yellow.append(f)
    return ''.join(yellow)

def _apply_yellow_then_green(from_phase, to_phase):
    yellow_state = _compute_yellow_state(GREEN_STATES[from_phase], GREEN_STATES[to_phase])
    sumo.trafficlight.setRedYellowGreenState(ts_id, yellow_state)
    for _ in range(YELLOW_TIME):
        sumo.simulationStep()
        sim_time += 1
    sumo.trafficlight.setRedYellowGreenState(ts_id, GREEN_STATES[to_phase])
```

### 3. Single SUMO query per step

```python
pressures = get_mp_pressures(sumo)
best_phase = max(pressures, key=pressures.get)
```

### 4. Removed dead `YELLOW_STATES` dict

---

## What Was NOT Changed

- The Max Pressure selection algorithm itself (`get_mp_pressures` and the `max(pressures, key=...)` logic)
- The phase state strings (GREEN_STATES)
- All metrics collection (queues, waiting times, arrived vehicles)
- The overall evaluation structure

The MP algorithm remains: **greedily jump to the phase with the highest incoming vehicle count**, but now subject to the same physical constraints (MIN_GREEN, MAX_GREEN, YELLOW_TIME) that all other controllers respect.
