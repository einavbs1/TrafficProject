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

## V6 Camera — diff_waiting_time + Starvation Penalty + 100m Camera — saved_agents/V6/
**Date:** 2026-07-01  
**Total Wait:** Low=4.66M ✅ | Medium=26.9M ✅ | High=67.0M ❌  
**vs Fixed_60s (Low=4.61M / Med=27.0M / High=64.3M):** Low −1% ❌ | Med +0.5% ✅ | High −4.3% ❌  
**Status:** Complete. Breakthrough on low traffic. High traffic regressed due to 100m camera cutoff.

### Changes from V4 (FRESH TRAINING, 6M steps)
| What | V4 | V6-camera |
|------|-----|-----------|
| Camera range | Full lane | **100m from stop line** |
| Reward | `diff_waiting_time` only | `diff_waiting_time - starvation_penalty` |
| starvation_penalty | — | `max(starvation_score_per_lane_group) * 0.05` |
| starvation_score | observation only | `min(max_consecutive_wait_in_group / 90s, 1.0)` |
| STARVATION_THRESHOLD | 90s (obs only) | 90s |

### Key results
- Low traffic: 68M → **4.66M** (15x improvement). Starvation penalty gave non-zero gradient in sparse traffic.
- High traffic: 61.8M → **67.0M** (regression). 100m camera blind to queue buildup beyond stop line vicinity.
- Switch rate: 5.7/100s vs Fixed_60s 1.7/100s — higher but still reasonable.

### New evaluation metrics added
- Wait_Per_Vehicle = Total_Wait_Time / Total_Arrived (volume-normalized)
- Switch_Rate_per100s = Total_Switches / 200 (diagnostic for over/under-switching)

### Root cause of high traffic regression
Dense queues extend beyond 100m from the stop line. V6-camera's observation misses the
full queue length — it "sees" a shorter queue and under-reacts to congestion building far back.
V7 raises camera to 150m to fix this.

---

## V7 — Starvation@45s + 150m Camera + Idle Switch Penalty — saved_agents/V7/
**Date:** 2026-07-01  
**Total Wait (best, 4.7M steps):** Low=4.66M ❌ | Medium=25.9M ✅ | High=62.2M ✅  
**Status:** Complete at 4.7M steps. Beat Fixed_60s on Medium+High; Low 1% behind.

### Changes from V6-camera (FRESH TRAINING)
| What | V6-camera | V7 |
|------|-----------|-----|
| Camera range | 100m | **150m** |
| Starvation threshold | 90s | **45s** (fires earlier, stronger early signal) |
| Idle switch penalty | — | **0.03 when intersection is empty** |

### Why each change
- **150m camera**: Fix V6-camera high traffic regression. 150m captures full near-intersection queue. WORKED — High 67.0M → 62.2M.
- **45s threshold**: Stronger early starvation gradient. Neutral — Low unchanged vs V6.
- **Idle switch penalty (-0.03)**: FAILED — too weak, absorbed into gradient noise. Low identical to V6 (4.66M). Led directly to V8's hard mask.

### V7 Resume Incident (2026-07-02) — CRITICAL LESSON
Original training crashed at 4.7M before saving VecNormalize stats. A resume
run silently created FRESH normalization stats → observation distribution
shifted under the trained policy → total collapse after 1.2M more steps
(Low 4.66M→35.4M, Med 25.9M→62.1M, High 62.2M→77.0M). The resume run's
checkpoints also overwrote the original run's 100k-1.2M checkpoints.
The good 4.7M checkpoint was restored from `checkpoints/`.

**Fixes applied to ALL training scripts:**
1. `save_vecnormalize=True` — every checkpoint saves matching stats
2. Hard abort if resuming without the matching stats .pkl
3. Resume runs get their own checkpoint filename prefix (no overwrites)
4. Crash recovery: if no final model but checkpoints exist, training
   auto-continues from the latest checkpoint with the original LR schedule
   and step counter (use `--fresh` to override)

---

## V8 — Hard Empty-Intersection Mask — saved_agents/V8/ ← CHAMPION 🏆
**Date:** 2026-07-02  
**Model:** 20260702_011233 (6M steps fresh)  
**Total Wait:** Low=2.29M ✅ | Medium=17.3M ✅ | High=59.2M ✅  
**vs Fixed_60s:** Low **-50%** | Medium **-36%** | High **-8%**  
**Status:** FIRST AGENT TO BEAT ALL BASELINES IN ALL SCENARIOS.

### Changes from V7 (FRESH TRAINING, 6M steps)
| What | V7 | V8 |
|------|-----|-----|
| Idle switch penalty | -0.03 (soft, in reward) | **Removed** |
| Empty intersection rule | Penalty only | **Hard mask: Switch blocked when total_visible == 0** |
| batch_size | 256 | 512 (hardware optimization) |

### Why the hard mask won where the penalty failed
The -0.03 penalty was invisible next to the diff_waiting_time signal. The hard
mask removes the action entirely — consistent with MIN_GREEN/MAX_GREEN philosophy
(structural constraints, not penalties). The policy never wastes a single
gradient step learning "don't switch at nothing."

### Behavioral evidence (low traffic, 5-seed avg)
| Metric | V8 | Fixed_60s |
|--------|-----|-----------|
| Switch rate /100s | **0.4** | 1.7 |
| Wait per vehicle | **3,293s** | 6,602s |

The agent holds green on an empty intersection indefinitely and switches only
when a real vehicle needs service — impossible for any fixed-cycle controller.

---

## V9 — De-saturated Observation — saved_agents/V9/ — HYPOTHESIS REJECTED
**Date:** 2026-07-02  
**Total Wait:** Low=2.78M | Medium=17.29M | High=59.38M  
**Status:** No improvement over V8. Kept for the record; V8 stays champion.

### Change from V8 (FRESH TRAINING, 6M steps, camera stays 150m)
| What | V8 | V9 |
|------|-----|-----|
| Starvation obs | `min(wait/45s, 1)` (saturates) | `log(1+wait)/log(1+300s)` |
| Total-wait obs | — | NEW 8 dims, log-normalized |
| Observation | 21-dim | 29-dim |
| Reward / mask | — | unchanged |

### Hypothesis (rejected)
In extreme traffic the 150m camera saturates → all demand+starvation dims read
1.0 → agent can't prioritize. De-saturating the observation should improve High.

### Why it failed — the key finding
V9 High is identical to V8 seed-by-seed, with the SAME bimodal split
(3 seeds ≈57M, 2 seeds ≈63M). The split tracks the SUMO demand seed, not the
policy. **The high-traffic ceiling is demand-driven (queuing physics when
demand ≈ capacity), not perception-driven.** Extra obs dims also slightly hurt
Low (2.29M→2.78M) by adding noise to an already-solved scenario.

**Implication:** V8's -7.9% on High is near the practical ceiling for signal
control on this map. Future high-traffic gains, if any, must come from the
demand/capacity side (e.g. coordinating multiple intersections), not from a
smarter single-intersection observation.

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
