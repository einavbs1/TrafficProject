# PPO V3.1 Architecture Summary

**Date:** June 2026
**Status:** The current active code in `sumo_rl_env.py` and the best performing model to date.

## Overview
After experimenting with Acyclic wrappers (V4) and extreme exponential starvation penalties (V5/V6) which successfully dropped peak wait times but destroyed overall throughput, we reverted to the V3 Cyclic architecture. We upgraded it to **V3.1** by patching the specific bugs that caused the original V3 to fail. 

## Architectural Features (V3.1)
1. **Cyclic Wrapper (`SwitchOrKeepWrapper`)**: The agent dictates when to move to the next phase in the sequence (0 -> 1 -> 2 -> 3), but cannot jump randomly.
2. **Smart Empty-Phase Skipping**: Added logic to `_resolve_phase_state()` so that if the *next* phase in the cycle has exactly 0 cars waiting in its designated lanes, it is seamlessly bypassed. This prevents the AI from being forced to waste a 10s `MIN_GREEN` on an empty road.
3. **Queue-Based Teleportation Fix**: Replaced the original wait-time metric with a physical `sum_of_queues` penalty in `_compute_reward()`. Because SUMO forcibly teleports cars that wait >300s, the original agent was being rewarded for letting cars disappear. The new queue penalty prevents this exploit while keeping the neural gradients stable (avoiding the explosions seen in V5).

## The Journey: Why We Reverted to V3
The path to V3.1 involved several failed experiments. We actively chose to roll back the architecture because each subsequent version (V4 through V6) drifted further away from the AI's core strength: maximizing traffic flow.

1. **Original V1/V2/V3 (683 Million Wait Time)**: The agent was trapped by a SUMO simulation bug. When cars waited over 300 seconds, they teleported. The AI learned it could "reduce" wait time by simply starving lanes until the cars disappeared.
2. **V4 Acyclic (960 Million Wait Time)**: We removed the strict phase cycle to give the AI total freedom to jump to any phase. It failed catastrophically because it spent too much time rapidly switching phases, losing critical seconds to yellow lights and crashing throughput.
3. **V5 Uncapped Starvation (~148 Million Wait Time)**: We added massive, exponential penalties (e.g. -10,000) for starving cars. This fixed the teleportation bug (because the AI was too terrified to let cars starve), but the extreme math exploded the neural network gradients, destabilizing the learning process.
4. **V6 Capped Starvation (105 Million Wait Time)**: We capped the penalties and forced a dynamic minimum green time. While it stabilized learning, it sacrificed too much raw throughput in the name of fairness.
5. **Improved V3.1 (84.7 Million Wait Time)**: We realized the original V3 cycle was structurally superior. By reverting to the V3 cycle, but replacing the wait-time metric with a simple, stable **Queue Penalty**, we fixed the teleportation bug *without* exploding gradients or sacrificing throughput. 

## Benchmark Results (High Traffic)
| Model | Total Wait Time | Peak Max Wait (s) | 
| :--- | :--- | :--- | 
| Fixed_60s (Baseline) | 64,284,917 | 180.0 | 
| **Maskable_PPO (V3.1)** | **84,788,759** | 197.8 | 
| V6 (Exponential Cap) | 105,781,809 | 106.0 | 
| V5 (Exponential Uncapped)| ~148,000,000 | 4,960.0 |
| V4 (Acyclic) | 960,362,478 | 11,295.6 |
| Original V1/V2/V3 | 683,042,302 | N/A |

## Conclusion
V3.1 is the undisputed champion of the PPO agent iterations. By prioritizing pure flow (Pressure) and fixing the teleportation bug with a stable linear penalty instead of extreme exponential math, the agent slashed its total wait time down to 84.7M. 

**Note on Current State:** The codebase is currently fully aligned with the V3.1 architecture. No further rollbacks are necessary.
