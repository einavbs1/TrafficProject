# Project Overview -- MDP Formulation, Reward Design, and Algorithm Choices

Reference document for explaining "how does this work" and "how did you
verify that" for both approaches tried in this project. **PPO is the main
subject and the shipped/champion approach.** DQN was an earlier/parallel
approach, kept as a smaller secondary section.

---

## 1. Is this an MDP? Yes -- here's the mapping

Every RL problem is formulated as a **Markov Decision Process**: a tuple
`(State, Action, Reward, Transition dynamics)` where the agent picks an
action based on the current state, the environment moves to a new state
and returns a reward, and (ideally) the next state depends only on the
current state + action, not on history. Both agents in this project fit
this frame directly:

| | State | Action | Reward | Transition |
|---|---|---|---|---|
| **PPO (V8)** | 21-dim camera-limited traffic observation | Discrete(2): Keep / Switch phase | `diff_waiting_time - starvation_penalty` | SUMO microsimulation, 5s per step |
| **DQN** | 10-dim queue/phase observation | Discrete(2): Hold / Request switch | Multi-term hand-tuned formula (12+ components) | SUMO microsimulation |

The rest of this document fills in each cell.

---

## 2. PPO (main subject) -- MDP formulation

**File:** `PPOagent/saved_agents/V8/sumo_rl_env_V8.py`

### 2.1 State / Observation -- 21 dimensions, all normalized to [0, 1]
```
[phase_onehot(4), elapsed_green_norm(1), lane_demands(8), lane_starvation(8)]
```
- **phase_onehot(4)**: which of the 4 traffic-light phases is currently green.
- **elapsed_green_norm(1)**: `elapsed_green_time / MAX_GREEN` -- how long the
  current phase has held green, as a fraction of the max allowed (60s).
- **lane_demands(8)**: for each of the 8 lane-groups, `visible_vehicle_count /
  visible_lane_capacity` -- occupancy density of **incoming** lanes only,
  camera-limited to `CAMERA_RANGE = 150m` from the stop line (an intentional
  design choice: this is meant to model what a real camera/sensor at the
  intersection could actually see, not omniscient simulator state).
- **lane_starvation(8)**: for each lane-group, `longest_single_vehicle_wait /
  STARVATION_THRESHOLD (45s)`, capped at 1.0 -- flags "someone has been
  waiting a long time here," independent of how many vehicles are present.

**Important, if asked "does it use pressure / in-vs-out flow":** No. Unlike
a classical Max-Pressure controller, the observation never counts *outgoing*
lane occupancy -- only incoming demand + starvation. This was a deliberate
architectural choice (see section 2.5) and is also why V8 doesn't inherit
Max-Pressure's known failure mode (see section 5).

### 2.2 Action space
`Discrete(2)`: `0 = Keep current phase`, `1 = Switch to the next phase`
(cyclic order 0→1→2→3→0, never a free jump to an arbitrary phase).

**Hard action masking** (`action_masks()`): the "Switch" action is
*structurally disabled* (not just penalized) whenever:
- fewer than `MIN_GREEN = 10s` have elapsed in the current phase, or
- the intersection is currently empty (no vehicles visible to any camera).

Switching is *forced* once `MAX_GREEN = 60s` is reached, regardless of the
policy's preference. A yellow transition (`YELLOW_TIME = 3s`) is inserted
automatically on every switch. Decisions are made every `DELTA_TIME = 5s`
of simulated time.

### 2.3 Reward function -- exact formula
```python
diff_wait = (prev_total_wait - current_total_wait) / num_lanes
starvation_penalty = max_starvation_score * STARVATION_PENALTY_COEF   # coef = 0.05
reward = diff_wait - starvation_penalty
```
- `current_total_wait` = **ground truth**, system-wide accumulated waiting
  time summed over every vehicle on every lane (via SUMO's
  `getAccumulatedWaitingTime`) -- not camera-limited, not an estimate. The
  reward directly measures the thing the project is ultimately evaluated
  on (reduction in total wait), rather than a proxy like queue length or
  pressure.
- `max_starvation_score` is the same starvation signal from the observation
  (camera-limited, threshold 45s) -- a small penalty (coefficient 0.05) so
  the agent doesn't ignore a single very-unlucky vehicle just because the
  aggregate wait number looks fine.
- **Why this design, if asked:** earlier versions (V4) used this same
  `diff_waiting_time` idea alone and it had near-zero gradient in sparse
  (low) traffic -- few cars means `diff_wait ≈ 0` almost every step, so the
  agent got almost no learning signal. Adding the starvation term (from V6
  onward) gave a non-zero gradient even when traffic is sparse, and fixed
  low-traffic performance by 15x in one version jump.

### 2.4 Algorithm: MaskablePPO (PPO + action masking), on-policy
**File:** `PPOagent/saved_agents/V8/train_V8.py`

| Hyperparameter | Value | Why (if asked) |
|---|---|---|
| Algorithm | `MaskablePPO` (sb3-contrib) | PPO's own action-masking-aware variant -- correctly excludes masked actions from the policy's probability distribution, not just from being taken |
| `learning_rate` | `3e-4 → 0`, linear decay over the full training horizon | Standard PPO practice: large steps early while the policy is far from good, near-zero steps late so it settles instead of overshooting |
| `ent_coef` | `0.02`, constant | Entropy bonus -- rewards keeping some randomness in the policy so it keeps exploring instead of collapsing to one action early. **Known limitation**: because this never decays (unlike the learning rate), it keeps nudging the policy with exploration noise even very late in training -- our leading hypothesis for why individual checkpoints can still be unstable near the end of a run (see section 5) |
| `gamma` (discount) | 0.99 | Standard; values future reward almost as much as immediate reward, appropriate for a continuing traffic-control task |
| `gae_lambda` | 0.95 | Standard GAE smoothing for advantage estimation |
| `clip_range` | 0.2 | Standard PPO trust-region clip |
| `n_steps` | 512 | Rollout length collected per environment before each update |
| `batch_size` | 512 | |
| `n_epochs` | 10 | Passes over each rollout batch per update |
| `target_kl` | 0.03 | Early-stops an update if the policy is changing too fast, an extra stability guard on top of the clip |
| Training mode | Fresh (random init), 6M steps | No fixed random seed anywhere in the training script -- every fresh run (including this one) starts from different random network weights and a different random training-traffic stream; **runs are not reproducible run-to-run** (confirmed empirically: two independent runs of this exact recipe, V8 and V8_replicate, produced very different stability profiles) |

### 2.5 Why PPO (on-policy) over DQN (off-policy) here, if asked
- **Action masking** integrates naturally into PPO's stochastic policy
  (mask the probability distribution before sampling); DQN needs an ad-hoc
  "mask invalid Q-values to -1e9 before argmax" workaround (see 3.3) that
  doesn't reshape the actual value function the same principled way.
- **Reward simplicity**: PPO's reward is 2 terms, both directly tied to the
  ground-truth evaluation metric. DQN's reward (12+ hand-tuned terms, see
  3.2) is harder to reason about and easier to have terms fight each other.
- **On-policy stability**: PPO's clip range + target_kl give two built-in
  guardrails against the policy changing too violently in one update --
  directly relevant given this project's history of catastrophic collapses
  under earlier (off-policy-adjacent / poorly-guarded) reward designs (see
  version history, V3.3).

---

## 3. DQN (secondary subject)

**Folder:** `DQNagent/flowgrid/` (separate codebase/package from `PPOagent/`)

### 3.1 MDP formulation
- **State (10-dim, normalized to [0,1])**: 8 queue counts (one per
  movement -- North/South/East/West x Left-turn/Through, capped at 20
  vehicles), + cycle position (`current_phase_index / 3`), + time-in-phase
  (normalized against roughly `2 x min_green`).
- **Action (Discrete(2))**: `0 = hold current phase`, `1 = request a switch`
  (subject to a minimum green time and safety constraints, same spirit as
  PPO's masking but enforced differently -- see 3.3).

### 3.2 Reward function -- many hand-tuned terms
Unlike PPO's 2-term reward, DQN's reward (`flowgrid/core/sumo_env.py`) sums
roughly a dozen components every step, including:
- `-delay_delta_scale x (current_wait - previous_wait)` (a diff-wait term,
  similar in spirit to PPO's)
- `-total_wait_scale x network_waiting_time` (an *absolute* wait penalty,
  not just a diff)
- **-1000** flat penalty per lane exceeding capacity (spillback)
- **+8.0** per vehicle cleared, scaled down by red-queue length
- Fairness terms penalizing imbalance between approaches
- An exponential-decay penalty specifically for vehicles waiting at red
- **-18** per phase switch (discourage rapid switching)
- **-40** if a switch interrupts an actively-flowing platoon of cars
- **+3.0 x (1 + 0.1 x consecutive_clears)**, up to a 3x multiplier, for
  consecutive clears
- **-8** for an attempted invalid action

**If asked "why so many terms":** this reward tries to directly encode
several distinct goals (throughput, fairness, anti-spillback, anti-flicker)
as separate shaped terms, rather than relying on one ground-truth signal
plus a small correction the way PPO's does. That's a reasonable design
philosophy, but it means many coefficients to hand-tune and more surface
area for terms to conflict -- a tradeoff worth being able to name if asked
to compare the two reward designs directly.

### 3.3 Algorithm: DQN, off-policy, with a replay buffer
- **Network**: small fully-connected net, `input(10) → 64 → ReLU → 64 →
  ReLU → output(2)`.
- **Replay buffer**: capacity 10,000 transitions, sampled in batches of 64.
- **Exploration**: epsilon-greedy, `epsilon_start=1.0 → epsilon_end=0.01`,
  decayed by a factor of 0.99 per step. Invalid actions are masked by
  setting their Q-value to `-1e9` before taking the argmax (a post-hoc
  mask on the output, rather than PPO's mask on the action-probability
  distribution itself).
- **Target network**: classic Double-DQN-style setup, synced from the
  policy network every 10 episodes, to stop the policy from chasing a
  constantly-moving target.
- **Optimizer**: Adam, `learning_rate=1e-3`, MSE loss, `gamma=0.99`.

### 3.4 Status, if asked "why isn't DQN the champion"
No formal, documented head-to-head comparison of DQN vs. PPO (or vs. the
fixed-timer baselines) exists in the DQN codebase -- there's evaluation
scaffolding (`batch_evaluate.py`, `compare_metrics.py`, `compare_guard.py`)
suggesting it was benchmarked during development, but no results file or
summary analogous to the PPO side's extensive, seed-verified comparison
tables. The honest answer here is: **PPO was carried forward as the
primary approach and received the full evaluation rigor; DQN was an
earlier/parallel exploration that was not brought to the same level of
verification**, not that DQN was rigorously proven worse.

---

## 4. How PPO's results were verified, if asked "how do you know it's good"

This is the part most likely to get pressed on, so it's worth having crisp:

1. **Baselines**: Fixed-timer controllers at 30s/45s/60s cycle times, plus
   (initially) a Max-Pressure controller -- later excluded after diagnosing
   it hits a genuine SUMO-level gridlock on this network's left-turn lane
   geometry (confirmed via an instrumented trace, not guessed).
2. **Paired-seed comparison**: every controller (PPO and every baseline)
   is evaluated on the *exact same* seeded traffic instance for a given
   row -- SUMO's vehicle generation is seeded, so "seed 42" produces a
   bit-identical vehicle stream regardless of which controller is driving
   the light. This was verified empirically (bit-identical re-runs across
   process restarts and different days).
3. **Checkpoint sweeps**: every saved checkpoint across training evaluated,
   not just the final one -- this is how we discovered V8's actual best
   checkpoint (2.3M steps) beats its own final 6M checkpoint on Medium
   traffic, and how "more training" was shown to not be monotonically
   better.
4. **Escalating seed counts to settle disputes**: 5 seeds → 50 seeds when a
   finding needed more confidence (e.g. verifying the 2.3M vs. 6M
   discrepancy held up).
5. **Fully random, unfiltered final check**: the most rigorous pass --
   every checkpoint tested against its own independently-drawn random seed
   and scenario (no reused seeds, nothing cherry-picked, no filtering out
   bad results). For V8's champion run: **53/60 checkpoints (88.3%) beat
   all 3 fixed timers outright** on this fully-random test, with the 7
   losses either early-training (expected) or narrow single-digit-percent
   losses specifically against the toughest baseline on Low traffic --
   not catastrophic failures.
6. **Documented, not hidden, limitations**: High-traffic performance
   (-7.9% vs Fixed_60s) was shown to be demand-limited (a queuing-physics
   ceiling, not a perception/observation problem) via a rejected hypothesis
   experiment (V9) that ruled out "the agent just can't see far enough."

---

## 5. Known limitations, if asked directly

- **High-traffic ceiling**: near the practical limit for a single
  intersection when demand approaches capacity; V9 specifically tested and
  ruled out "better observation would fix this."
- **Training instability, not fully solved**: an independently-seeded
  replication run (V8_replicate) showed far more checkpoint-to-checkpoint
  volatility than V8's own run -- current best explanation is the constant
  (non-decaying) entropy coefficient, not insufficient training length (a
  longer-horizon run, V8_12M, is testing this directly, but training is
  not reproducible run-to-run regardless of outcome).
- **Single intersection scope**: this project controls one intersection;
  multi-intersection coordination is future work, not yet attempted.
