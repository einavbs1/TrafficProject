# Upgrading PPO to V4 Acyclic Architecture

The PPO agent showed promising capability but ultimately lost to the fixed 60s timers and got bogged down in heavy traffic. Analyzing the environment logic (`sumo_rl_env.py`) reveals two massive bottlenecks holding the AI back. To dominate the baseline, we need to completely restructure the agent's action space and reward scaling.

## Proposed Changes

### 1. V4 Architecture: Acyclic Phase Selection
**The Problem**: The current `SwitchOrKeepWrapper` forces the AI into a strict cycle (`0 -> 1 -> 2 -> 3`). Even with phase-skipping logic, if the AI is in Phase 0 and desperately needs Phase 2, it is trapped.
**The Fix**: Create a new `AcyclicWrapper` with `spaces.Discrete(4)`. The AI will directly output the phase index it wants (0, 1, 2, or 3).
- If `action == current_phase`, it extends the green light.
- If `action != current_phase`, it immediately switches to the requested phase (bypassing the cycle entirely).
- We will use `ActionMasker` to block invalid jumps (e.g. if `MIN_GREEN` hasn't been met, mask out all actions except the current phase).

### 2. Fixing the Starvation Reward Curve
**The Problem**: The math behind the starvation penalty is far too weak. At 90 seconds of wait time, the penalty is only `-0.56`. But the pressure reward for letting 20 cars through is `+1.66`. The AI will happily let a single car starve for 2 minutes because the math mathematically encourages it!
**The Fix**: Redesign `_compute_reward()` to enforce a draconian penalty for starvation.
- `60s` wait = `-1.0` penalty
- `90s` wait = `-5.0` penalty (explicitly overrides pressure)
- `120s` wait = `-20.0` penalty
- This forces the AI to clear out stranded cars rather than greedily chasing bulk pressure.

## Verification Plan
1. Implement `AcyclicWrapper` in `sumo_rl_env.py`
2. Run `evaluate_models.py` with random actions using the new wrapper to ensure transitions and masking work without crashing SUMO.
3. Train a fresh PPO agent (`train_production.py`) for 1,000,000 steps using the V4 architecture and observe if it avoids the cyclic trap.
