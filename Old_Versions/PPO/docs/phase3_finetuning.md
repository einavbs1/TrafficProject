# Phase 3: Online Fine-Tuning

## Objective
Transition the agent from purely supervised imitation to active reinforcement learning so it can discover optimizations beyond the baseline algorithm.

## Execution
Run the online PPO training script:
```bash
python train_ppo.py
```

## What Happens Under the Hood
1. The `stable_baselines3` PPO algorithm is initialized.
2. The agent is connected live to the `sumo-rl` simulation environment.
3. Crucially, the agent loads `bc_policy.zip` from Phase 2. Instead of random weights, it starts with the behavioral cloning weights.
4. The agent interacts with the environment. It occasionally explores new actions, receiving the `presslight_reward` (Max-Pressure reward) we defined. It updates its policy to maximize this reward, fine-tuning its decisions.

## Output
This phase produces `ppo_sumo_finetuned.zip`. The agent has now optimized itself dynamically and is ready for harder challenges.
