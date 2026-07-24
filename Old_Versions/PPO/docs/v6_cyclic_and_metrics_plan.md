# V6 Implementation Plan: Return to Cyclic & Advanced Diagnostics

Based on our discussion, we have realized that the Acyclic jumping logic was the root cause of the starvation bug. We will abandon the "Overlord" concept and simply revert the action space to our old cyclic structure, which naturally guarantees starvation prevention while allowing the AI to dynamically hold green lights for as long as traffic demands (e.g., 60s or 30s).

## 1. Return to the Cyclic Safety Net
- **Update Execution Scripts**: Revert `train_production.py` and `evaluate_models.py` to import and instantiate `SwitchOrKeepWrapper` instead of `AcyclicWrapper`.
- **Baseline Fixes**: Revert the Fixed Timer baseline algorithms in `evaluate_models.py` to use `Discrete(2)` logic (Action 0 to keep green until `cycle_time` is reached, then Action 1 to switch).
- **Environment Logic**: `sumo_rl_env.py` already contains the `SwitchOrKeepWrapper`. It will automatically inherit the uncapped starvation penalty and dynamic `MIN_GREEN` logic we built during V5.

## 2. Advanced Diagnostic Metrics
To ensure we have total visibility into the AI's performance, we will update `evaluate_models.py` to extract three new parameters and print them in the final CSV table:
1. **Total Light Switches**: Tracks how many times the agent changes the phase. High numbers prove the agent is wasting simulation time on Yellow Lights.
2. **Total Cars Cleared (Throughput)**: Extracts `sumo.vehicle.getArrivedNumber()` to show exactly how many cars successfully finished their route.
3. **Average Queue Length**: Tracks the average number of stopped cars per step, showing overall intersection congestion.

> [!WARNING]
> Because we are reverting the action space from `Discrete(4)` back to `Discrete(2)`, the neural network architecture fundamentally changes. We must train a brand new agent for 4,000,000 timesteps.

## Verification Plan
1. Apply the code changes to `evaluate_models.py` and `train_production.py`.
2. Launch the 4 million timestep training run (`--newAgent`).
3. Run the evaluation benchmark to test the Cyclic PPO agent against the baselines, ensuring the new CSV table includes the 3 new advanced metrics.
