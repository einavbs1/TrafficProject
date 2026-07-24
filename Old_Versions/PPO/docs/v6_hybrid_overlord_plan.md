# V6 Implementation Plan: Diagnostics & Hybrid Architecture

Before we permanently change the AI's logic, we need to definitively prove *why* the V5 agent lost to the Fixed 30s timer, and then implement a structural fix to prevent it from happening again.

## Part 1: Advanced Diagnostics (The "Why")
To understand exactly how the PPO agent is failing compared to the Fixed Timer, we will add three new metrics to `evaluate_models.py` and output them in the CSV:

1. **Total Phase Switches**: We will track `total_switches` during the episode. Every time the agent changes the light, it forces a 3-second yellow light where no cars move. By comparing the AI's switch count to the Fixed Timer's switch count, we can prove if the AI is losing 20%+ of its capacity to yellow lights.
2. **Total Cars Cleared (Throughput)**: We will use SUMO's `getArrivedNumber()` to track the total number of cars that successfully crossed the intersection. If the AI clears fewer cars than the Fixed timer, it proves the AI is fundamentally choking the intersection's flow rate.
3. **Average Queue Length**: Tracking the average number of stopped cars per step to measure overall congestion.

## Part 2: The V6 Hybrid Architecture (The "Fix")
If the advanced diagnostics prove that the AI is panicking and switching too often, or that the exploding `-10,000` penalty destroyed its learning stability, we will implement the **V6 Hybrid Architecture**:

### 1. Reward Re-capping (Fixing Exploding Gradients)
**Why it's needed**: In V5, we let the starvation penalty explode to `-10,000`. Neural networks cannot process sudden massive numbers; it shatters the mathematical gradients (Catastrophic Variance) and makes the AI behave randomly.
**The Fix**: We will re-cap the maximum starvation penalty to `-20.0`. This is enough to hurt the AI's score, but small enough that the neural network can stably learn how to avoid it over 4 million steps.

### 2. The Gridlock Overlord (The Safety Net)
**Why it's needed**: If a simple 30-second cycle clears extreme gridlock flawlessly, we shouldn't force the AI to stumble around in the dark trying to randomly reinvent the wheel. 
**The Fix**: We will add a "Gridlock Overlord" intercept to the environment wrapper. 
- If `total_queued_cars < 50`: The PPO AI is in complete control and can dynamically manage the light.
- If `total_queued_cars >= 50`: The Overlord forcefully overrides the AI and forces a perfect 30-second cycle (`0 -> 1 -> 2 -> 3 -> 0`) until the gridlock drops below 50. 
This gives us the best of both worlds: dynamic AI optimization during normal traffic, and guaranteed, flawless mathematical cycling during rush hour.

## Proposed Steps
1. Update `evaluate_models.py` to extract and print the advanced diagnostics.
2. Implement the Overlord override and Reward re-capping in `sumo_rl_env.py`.
3. Train the new V6 Agent.
