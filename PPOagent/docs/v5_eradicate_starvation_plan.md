# V5 PPO Implementation Plan: Eradicating Starvation

Our V4 agent solved the throughput problem but completely failed at minimizing the maximum wait time for individual cars. It learned it could get a higher score by moving 100 cars on the highway while letting 1 car starve for 3 hours on a side street.

To force the agent to prioritize the maximum wait time of the longest-waiting car, we will implement the following changes in the V5 Architecture.

## 1. Uncapped Exponential Starvation (The Veto)
We are currently clamping the starvation penalty at `-100.0` and the total reward at `-100.0`. 
**The Fix**: We will remove the safety caps. If a car waits beyond 100 seconds, the penalty will explode exponentially (e.g., `-1000`, `-5000`). This ensures that the agent's reward is mathematically dominated by the highest waiting time of any single car. It will learn that if *even one car* waits too long, the penalty will wipe out thousands of points of pressure reward.

## 2. Dynamic `MIN_GREEN`
**The Problem**: The Acyclic wrapper allows the AI to switch phases every 10 seconds. In heavy traffic, it rapidly switches between the busiest lanes, losing 3 seconds of "yellow light downtime" every switch. Over time, it loses 20% of its total capacity just displaying yellow lights.
**The Fix**: We will make `MIN_GREEN` dynamic based on queue lengths.
- If total queued cars < 10: `MIN_GREEN` = 10s
- If total queued cars > 10: `MIN_GREEN` = 20s
- If total queued cars > 30: `MIN_GREEN` = 30s
This physically forces the agent to hold green lights longer during heavy traffic, drastically increasing throughput efficiency.

## 3. Metric Tracking
As requested, we will ensure that `Peak_Max_Wait_s` (the highest waiting time of any car in the camera range during the episode) is the primary metric we judge the models on in our benchmark CSV tables.

> [!IMPORTANT]
> Because we are drastically changing the mathematical scale of the reward (from `[-100, 100]` to potentially `-10,000`), we must train a brand new V5 agent from scratch.

## Verification Plan
1. Update `sumo_rl_env.py` (both the Base `SwitchOrKeep` and `Acyclic` wrappers) to use the new uncapped reward and dynamic `MIN_GREEN` logic.
2. Train a new V5 agent for 4,000,000 timesteps (`train_production.py --newAgent`).
3. Run `evaluate_models.py` and verify the `Peak_Max_Wait_s` metric against the Fixed 60s baseline.
