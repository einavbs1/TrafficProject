# Phase 4: Curriculum Learning

## Objective
Ensure the agent generalizes well and can handle edge cases by subjecting it to increasingly complex and difficult traffic scenarios.

## Execution
Run the curriculum learning script:
```bash
python train_curriculum.py
```

## What Happens Under the Hood
1. The script contains an ordered list of progressively harder `.rou.xml` files (e.g., standard, asymmetric load, extreme rush hour).
2. It loads the `ppo_sumo_finetuned.zip` model from Phase 3.
3. It launches the environment with the first difficulty level and trains the agent for a set number of timesteps.
4. Once stabilized, it saves the weights, loads them into a new environment featuring the next difficulty level, and resumes training.
5. This process iteratively builds a robust, generalized policy.

## Output
This phase produces incremental saves (`ppo_curriculum_level_1.zip`, `ppo_curriculum_level_2.zip`, etc.). The final output is your production-ready Traffic AI.
