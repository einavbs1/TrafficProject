# TrafficProject AI Agent Rules

Welcome to the TrafficProject. To ensure consistency, stability, and proper architecture, you must strictly follow the rules below when working in this workspace.

## 1. General Workflows
- **Context Gathering**: ALWAYS begin by reading `repomix-output.xml` in the root directory to gain a full understanding of the current codebase state before taking action.
- **Repomix Maintenance**: After making structural or significant code changes to the project, re-generate the `repomix-output.xml` file to ensure the context remains strictly up-to-date.
- **Relentless Documentation**: Document everything continuously. **CRITICAL:** Every time the agent creates an implementation plan, once it is approved and work begins, you must save a copy of that plan as a `.md` file inside the `docs/` folder of the respective agent (e.g., `PPOagent/docs/`) so it is tracked in the project repository.
- **Resume, Don't Restart**: Do NOT start a new agent from scratch; always attempt to resume training from the last saved agent checkpoint (`ppo_*.zip`) when continuing a run.
- **Chain Commands**: When running terminal commands for training and evaluation sequentially, chain them together using semicolons (`;`) so they run continuously without asking for permission between steps.
- **Strict Organization**: Do not store temporary or random scripts in the root directory. Keep the project strictly organized into `DQNagent/`, `PPOagent/`, and `SharedData/`.

## 2. Post-Evaluation Analysis (CRITICAL)
- **Review Raw Data**: After *every* evaluation comparing models, you MUST review the raw benchmark data. 
- **Analyze Deficits**: If any baseline or alternative algorithm outperforms our PPO agent, you must stop, analyze the traffic mechanics causing the failure, and propose architectural or hyperparameter improvements.
- **Push for Dominance**: Even if our agent wins by a small margin, we must brainstorm ways to make it significantly better. The goal is complete dominance over the baselines so we can confidently push the agent to production.

## 3. Architecture & File Paths
- **Separation of Concerns**: The repository is permanently split into two systems: legacy DQN (`DQNagent/`) and modern PPO (`PPOagent/`).
- **Execution Context**: The PPO Python scripts are strictly located in `PPOagent/src/`. All terminal execution for PPO should be run with `PPOagent` as the current working directory (e.g., `cd PPOagent && python src/train_production.py`).
- **Shared Data**: All traffic networks and map configurations are stored centrally in `SharedData/`. Do not hardcode absolute paths to `data/`, use `SharedData/` instead.

## 4. Reinforcement Learning (PPO) Mechanics
- **Observation Space**: The PPO model uses a 21-dimensional observation space containing 8 exponential starvation metrics.
- **Network Architecture**: Due to the starvation metrics, the PPO network size must be scaled to `[128, 128]` for both the policy and value networks.
- **Learning Rate Strategy**: For initial training, use linear learning rate decay. For fine-tuning existing models, use a constant LR of `3e-5` to avoid catastrophic forgetting.
- **The "Lonely Car" / Low Traffic Anomaly**: Be aware of the yellow light penalty flattening the pressure gradient in low traffic scenarios. A single waiting car can trigger massive wait times if not handled correctly by the reward function or starvation constraints.

## 5. Baseline Mechanics (Max Pressure)
- **Acyclic Evaluation**: Max Pressure is strictly an **acyclic, greedy algorithm**. It evaluates all four cyclic phases independently and jumps directly to the phase with the highest pressure. It completely bypasses the binary `SwitchOrKeepWrapper` sequential logic.
- **Physical Constraints**: `MIN_GREEN` is 10s, `YELLOW_TIME` is 3s. Ensure the acyclic jumps do not violate these physical safety constraints.
