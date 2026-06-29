# PPO Agent Version History

Complete changelog — every version, the exact code changes made, and the results.

---

## V1 / V2 / V3 — Original Cyclic
**Total Wait (High Traffic):** ~683M  
**Status:** Failed

### Changes introduced
- SwitchOrKeepWrapper, cyclic phase sequence 0→1→2→3→0
- Discrete(2) action space: 0=Keep, 1=Switch
- Reward: accumulated waiting time of vehicles

### Why it failed
SUMO teleports vehicles waiting >300s. The reward metric counted waiting time, so when vehicles teleported they "disappeared" from the metric. The agent learned to starve lanes on purpose — waiting time dropped because vehicles were removed from simulation, not because they were served.

---

## V4 Acyclic — Agent picks any phase
**Total Wait (High Traffic):** ~960M  
**Status:** Failed

### Changes from V3
| What | Before (V3) | After (V4 Acyclic) |
|------|-------------|---------------------|
| Action space | Discrete(2) Keep/Switch | Discrete(4) — pick any phase directly |
| Wrapper | SwitchOrKeepWrapper | AcyclicWrapper |
| Phase sequence | Hardcoded cyclic 0→1→2→3 | Agent jumps to any phase freely |

### Why it failed
Every switch = 3s yellow. Agent jumped between phases constantly. Rapid switching wasted thousands of seconds in yellow transitions and crashed throughput.

---

## V5 — Exponential Starvation Penalty
**Total Wait (High Traffic):** ~148M  
**Status:** Partially improved, then abandoned

### Changes from V4 Acyclic
| What | Before | After |
|------|--------|-------|
| Wrapper | AcyclicWrapper | Back to SwitchOrKeepWrapper (cyclic) |
| Reward | Waiting time | Pressure + exponential starvation penalty: `0.05 × 1.5^((max_wait−30)/10)`, uncapped |
| Penalty trigger | None | Kicks in at 30s wait, grows exponentially |

### Why it failed
Uncapped exponential penalties reached values like −10,000. These extreme values exploded neural network gradients and destabilized training.

---

## V6 — Capped Starvation Penalty
**Total Wait (High Traffic):** ~106M  
**Status:** Partial improvement, then rolled back

### Changes from V5
| What | Before (V5) | After (V6) |
|------|-------------|------------|
| Starvation penalty | `0.05 × 1.5^(...)`, uncapped | Same formula, capped at 30.0 |
| Dynamic MIN_GREEN | None | Added — forces switch when phase served enough |

### Why it failed
Capped penalty was more stable but still disrupted gradient flow. Agent sacrificed throughput in favor of fairness. Overall wait time still worse than a fixed-time controller.

---

## V3.1 — Reverted Cyclic + Queue Penalty
**Date:** June 2026  
**Total Wait:** Low=91.5M | Medium=54.1M | High=84.8M  
**vs Fixed_60s (Low=4.6M / Med=27M / High=64M):** Losing all scenarios  
**Status:** Best pre-collapse model. Active production agent until V3.3 collapse.

### Changes from V6 (full revert + fixes)
| What | Before (V6) | After (V3.1) |
|------|-------------|--------------|
| Wrapper | AcyclicWrapper + capped penalty | Back to SwitchOrKeepWrapper cyclic |
| Reward | Pressure + exponential starvation (capped) | `pressure/num_lanes − queue_penalty` where `queue_penalty = sum_of_halting/num_lanes × 0.1` |
| Teleportation | SUMO default (teleports at 300s) | `time_to_teleport=-1` — disabled permanently |
| Phase skipping | None | Ghost Car Logic: empty left-turn phases skipped automatically |
| Observation | 13-dim | 21-dim: added 8 starvation score dimensions (max consecutive wait / 90s per lane group) |
| Starvation score | Not in observation | `min(max_wait_in_group / 90.0, 1.0)` per lane group |
| `min_green` | Variable | Fixed 10s |
| `max_green` | Variable | Fixed 60s |
| `delta_time` | Variable | Fixed 5s |
| `yellow_time` | Variable | Fixed 3s |

### Why it was the best
Stable queue penalty prevents teleportation exploit. Pressure reward gives positive gradient even with few vehicles. Phase skipping removes wasted green time.

### Why it didn't win vs baselines
Not enough training steps. Dynamic MIN_GREEN not yet added. Reward not aligned with evaluation metric.

---

## V3.2 — Dynamic MIN_GREEN + Faster Updates
**Date:** June 2026  
**Total Wait:** Low=49M ✅ | Medium=68M ❌ | High=125M ❌  
**Status:** Low traffic improved, medium/high regressed. Resumed from V3.1 checkpoint.

### Changes from V3.1
| What | Before (V3.1) | After (V3.2) |
|------|---------------|--------------|
| Training mode | Fresh | **Resume from V3.1 checkpoint** |
| `ent_coef` on resume | 0.0 (bug — zeroed on load) | 0.005 |
| `n_steps` | 2048 | **512** (faster gradient feedback) |
| `learning_rate` on resume | 3e-4 (restart schedule) | **3e-5** (constant fine-tune rate) |
| Dynamic MIN_GREEN | Not present | **Added**: if current phase has ≤2 vehicles → allow switch at 5s instead of 10s |
| `queue_penalty` coefficient | 0.1 | **0.2** |

### Why medium/high regressed
Dynamic MIN_GREEN fatal flaw: when a phase is GREEN, vehicles are actively moving through → `getLastStepVehicleNumber` on those lanes ≈ 0 → ≤2 condition is almost always true → agent could switch at 5s even in heavy traffic. Combined with queue_penalty=0.2 pushing rapid cycling, medium/high traffic degraded 25-47%.

---

## V3.3 — Total-Queue Guard + Reverted Penalty
**Date:** June 2026  
**Total Wait:** Low=899M ❌ | Medium=932M ❌ | High=963M ❌  
**Status:** Complete policy collapse. Worst result in project history.

### Changes from V3.2
| What | Before (V3.2) | After (V3.3) |
|------|---------------|--------------|
| Training mode | Resume from V3.1 | **Resume from V3.2 checkpoint** |
| Dynamic MIN_GREEN guard | `current_vehicles <= 2` only | Added `AND total_queued < 10` guard |
| `queue_penalty` coefficient | 0.2 | **Reverted to 0.1** |
| Additional training | 2M steps | +2M more steps |

### Why it collapsed
The `total_queued < 10` guard was also broken: when the current phase is GREEN, its vehicles are MOVING (not halting), so their halting count = 0. Other phases might have 8-9 halting vehicles — still below the < 10 threshold. The guard never fires in practice. Agent continued to switch at 5s in heavy traffic.

After 2M more training steps at fast update rate (n_steps=512), the agent fully committed to the exploit:
- Left-turn phases (0, 2): always switch at exactly 5s
- Straight phases (1, 3): hold for 60s
- Left-turn vehicles waited 17,000+ seconds

The exploit was so deeply reinforced that recovery via further training was impossible.

---

## V4 — Fresh Agent, diff_waiting_time Reward ← CURRENT
**Date:** 2026-06-28  
**Total Wait:** Low=68M ❌ | Medium=24.7M ✅ | High=61.8M ✅  
**vs Fixed_60s:** Medium −9% ✅ | High −4% ✅ | Low still losing  
**Status:** First agent to beat any baseline. Resume in progress for low traffic fix.

### Changes from V3.3 (FRESH TRAINING — V3.3 weights discarded)
| What | Before (V3.3) | After (V4) |
|------|---------------|------------|
| Training mode | Resume from V3.3 | **Fresh from random weights** |
| Dynamic MIN_GREEN | Present (broken) | **Removed entirely** — `action_masks()` uses `self.MIN_GREEN=10` always |
| `PHASE_LANES` dict | Present in SwitchOrKeepWrapper | **Removed** — was only used for broken dynamic MIN_GREEN |
| `_prev_total_wait` | Not present | **Added** to `__init__` and reset in `reset()` |
| Reward function | `pressure/num_lanes − queue_penalty×0.1` | **`(prev_accumulated_wait − current_accumulated_wait) / num_lanes`** |
| Reward alignment | Pressure (indirect proxy) | diff_waiting_time (directly = what evaluation measures) |
| `ent_coef` | 0.005 (resume) | **0.02** (fresh training, more exploration) |
| `learning_rate` | 3e-5 constant (resume) | **3e-4 → 0 linear decay over 6M steps** |
| Total training steps | ~2M per run | **6M from scratch** |
| `n_steps` | 512 | 512 (unchanged) |
| `batch_size` | 256 | 256 (unchanged) |

### Remaining issue
Low traffic: 68M vs Fixed_60s 4.6M (15x worse). Root cause: `diff_waiting_time` reward ≈ 0 in sparse traffic → near-zero gradient → agent doesn't converge for low-traffic episodes. Seed variance high (39M best seed vs 94M worst seed) confirms the policy hasn't converged for this scenario.

---

## V4 Resume — Additional Training (In Progress)
**Date:** 2026-06-28  
**Goal:** Close low-traffic gap without losing medium/high wins  
**Status:** Running

### Changes from V4 initial training
| What | V4 Training | V4 Resume |
|------|-------------|-----------|
| Training mode | Fresh | **Resume from V4 checkpoint** |
| `ent_coef` | 0.02 | **0.01** (reduced from fresh, more than old 0.005 default) |
| `learning_rate` | 3e-4 → 0 schedule | **3e-5 constant** (conservative, preserves wins) |
| Additional steps | 6M | **+6M** |
| Reward | diff_waiting_time (unchanged) | diff_waiting_time (unchanged) |
| Observation | 21-dim (unchanged) | 21-dim (unchanged) |
| Action masking | MIN_GREEN=10 fixed (unchanged) | MIN_GREEN=10 fixed (unchanged) |

---

---

## V5 (new) — Pressure Reward (halting-based) — saved_agents/V5/
**Date:** 2026-06-29
**Total Wait:** Low=189M ❌ | Medium=216M ❌ | High=245M ❌
**Switches:** ~1,148 / episode (massively over-switching vs 330 for V4)
**Status:** Failed. All scenarios lost to Fixed_60s by 40-300x.

### Changes from V4 (FRESH TRAINING)
| What | V4 | V5 (new) |
|------|-----|----------|
| Reward | diff_waiting_time | `(red_halting - green_halting) / num_lanes - total_halting/num_lanes*0.1` |
| Reward logic | diff in accumulated wait | pressure: difference in halting count between red and green lanes |

### Root cause of failure
When a phase FIRST turns green, vehicles haven't yet moved — green_halting stays high.
Pressure = (red - green) = negative. Agent immediately wants to switch. Trigger fires every 5s.
1148 switches/episode means 17% of episode time spent in yellow transitions — catastrophic.

---

## V6 (new) — diff_waiting_time + Starvation Penalty — saved_agents/V6/
**Date:** 2026-06-29
**Total Wait:** PENDING — training in progress
**Status:** Training

### Changes from V4 (FRESH TRAINING)
| What | V4 | V6 (new) |
|------|-----|----------|
| Reward | `diff_waiting_time` only | `diff_waiting_time - starvation_penalty` |
| starvation_penalty | — | `max(starvation_score_per_lane_group) * 0.05` |
| starvation_score | observation only | `min(max_consecutive_wait_in_group / 90s, 1.0)` |

### Why this should fix low-traffic failures
V4 low-traffic failures: diff_waiting_time ≈ 0 in sparse conditions → no gradient signal.
Agent sometimes locks onto one direction, starving others → seed variance 4M to 923M (23x!).
The starvation penalty fires proportionally to any vehicle's consecutive wait:
  - 1 vehicle waiting 45s  → penalty = -0.025 per step (non-zero gradient)
  - 1 vehicle waiting 90s  → penalty = -0.05 per step (max, clear push to serve that lane)
  - Dense traffic: diff_waiting_time = -1 to -10 per step → penalty is secondary (1-5%)
Hypothesis: adding this small, consistent signal will prevent catastrophic starvation
without disrupting the well-converged medium/high policy.

### New evaluation metrics added
- Wait_Per_Vehicle = Total_Wait_Time / Total_Arrived (volume-normalized)
- Switch_Rate_per100s = Total_Switches / 200 (diagnostic for over/under-switching)

---

## Key Lessons Learned

| Lesson | Version it bit us |
|--------|-------------------|
| Dynamic MIN_GREEN via live TraCI counts fires on green phases — always | V3.2 / V3.3 |
| Never resume into a changed reward/environment — policy collapse | V3.3 |
| `time_to_teleport=-1` is mandatory — teleportation breaks all reward signals | V1/V2/V3 |
| Exponential penalties explode gradients — linear/mild penalties only | V5/V6 |
| Acyclic (Discrete 4) loses to cyclic for this intersection topology | V4 Acyclic |
| diff_waiting_time has near-zero gradient in sparse (low) traffic | V4 |
| Changing reward OR observation semantics = fresh agent required | General rule |
| Never delete old model checkpoints — they are fallback options | General rule |
| ent_coef zeroes to 0.0 when loading a saved model — must re-set explicitly on resume | V3.2 fix |
