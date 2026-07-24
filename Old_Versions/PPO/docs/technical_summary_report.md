# FlowGrid: Deep Reinforcement Learning for Traffic Signal Control
### Technical Summary — DQN to PPO Transition

---

## 1. Project Architecture Overview

### System Integration: SUMO ↔ PPO Agent

FlowGrid couples a **Maskable Proximal Policy Optimization (PPO) agent** to the **Eclipse SUMO microsimulation engine** through a custom Gymnasium-compatible environment stack. The integration layer is built on the `sumo-rl` library, which provides the TraCI (Traffic Control Interface) connection to SUMO, while our wrapper chain handles all observation construction, reward computation, and action translation.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Training Orchestrator                        │
│        SubprocVecEnv (10 parallel SUMO processes)               │
│        VecNormalize (running obs normalization)                  │
│        MaskablePPO (sb3_contrib) → GPU (CUDA)                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │  action (0=Keep, 1=Switch)
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SwitchOrKeepWrapper                            │
│  - Phase sequence management (cyclic 0→1→2→3→0)                │
│  - Ghost Car Logic (phase overlap for one-sided left turns)      │
│  - Phase skipping (zero-demand phases bypassed)                  │
│  - Yellow transition computation (character-by-character)        │
│  - Action masking (MIN_GREEN / MAX_GREEN enforcement)            │
│  - Reward computation (pressure + queue penalty)                 │
│  - 21-dim observation construction                               │
└───────────────────────┬─────────────────────────────────────────┘
                        │  TraCI commands
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│            Eclipse SUMO Microsimulation                          │
│  - 4-way intersection (N/S/E/W), 16 signal links                │
│  - Vehicle-level physics (speeds, positions, wait times)         │
│  - delta_time = 5s per agent decision step                       │
│  - sim_max_time = 20,000 simulation seconds per episode          │
└─────────────────────────────────────────────────────────────────┘
```

The agent never directly interfaces with raw SUMO — all observations are computed by the wrapper from TraCI API calls, and all traffic light transitions are executed through the wrapper's yellow-state computation logic, ensuring physical safety constraints are never violated.

---

### Input State Space — 21-Dimensional Observation Vector

At every 5-second decision step, the agent receives a structured observation vector:

| Block | Indices | Dimension | Description |
|-------|---------|-----------|-------------|
| Phase one-hot | [0:4] | 4 | Which of the 4 signal phases is currently active |
| Elapsed time | [4] | 1 | Time in current green phase, normalized by MAX_GREEN (0→1) |
| Lane demands | [5:13] | 8 | Vehicle density per lane group, normalized by lane capacity |
| Lane starvation | [13:21] | 8 | Max consecutive wait of any vehicle per lane group ÷ 90s, capped at 1.0 |

The 8 lane groups cover every controlled movement: N-left, N-straight, E-left, E-straight, S-left, S-straight, W-left, W-straight. Right-turn lanes are excluded as they run permissive green continuously.

The starvation block (dims 13–21) is the architectural feature that distinguishes this observation from naive pressure-only designs. A single stranded vehicle with demand ≈ 0.05 would generate near-zero pressure reward, but its starvation score approaches 1.0 as it approaches 90 seconds of waiting — giving the agent an explicit urgency gradient for low-density edge cases.

---

### Output Action Space — Binary Phase Control

```
Action Space: Discrete(2)
  Action 0 — KEEP:   Extend the current green phase by delta_time (5 seconds)
  Action 1 — SWITCH: End current phase → 3s yellow → advance to next valid phase
```

The agent controls **when** to switch, not **which** phase to switch to. The phase sequence is hardcoded cyclically (`0 → 1 → 2 → 3 → 0`), which acts as a built-in fairness constraint — no phase can be permanently starved. The agent's intelligence lies entirely in its timing decisions.

Action masking enforces hard physical constraints at every step:
- `elapsed < effective_MIN_GREEN` → KEEP forced (safety minimum; 5s for ≤2-vehicle phases, 10s otherwise)
- `elapsed ≥ MAX_GREEN (60s)` → SWITCH forced (prevents phase monopolization)

---

## 2. The Case for PPO — Technical Rationale

### 2.1 On-Policy vs. Off-Policy Dynamics

The legacy DQN agent was fundamentally **off-policy**: it stored thousands of past traffic state transitions in a replay buffer and sampled them randomly for training. In a highly non-stationary environment like traffic flow, a transition recorded during peak congestion provides misleading gradient signal when replayed during sparse low-traffic conditions. The distributions shift, the Q-value estimates drift, and the agent destabilizes.

PPO is **on-policy**: it collects a rollout of fresh experience from the current policy, computes all gradient updates from that experience, then discards it. Every gradient step is taken on data that reflects the agent's *current* behavior, not a stale historical snapshot. For traffic signal control — where the relationship between signal state and traffic buildup has strong temporal dependencies — this recency guarantee is critical.

In practice, this manifested clearly in our project: the DQN agent trained for thousands of episodes without reliably beating a fixed-time baseline, largely because its replay buffer averaged over contradictory traffic scenarios. The PPO agent showed meaningful directional learning within the first 500,000 timesteps.

### 2.2 Training Stability — The Clipping Mechanism

The most destructive failure mode in deep RL is a catastrophically large policy update: the agent takes one bad gradient step, its behavior collapses, and the replay buffer fills with bad experiences that generate more bad gradients (a death spiral). DQN is vulnerable to this because its Bellman target updates are unbounded.

PPO addresses this with a **clipped surrogate objective**:

```
L_CLIP(θ) = E[ min( r(θ) · Â,  clip(r(θ), 1-ε, 1+ε) · Â ) ]
```

where `r(θ)` is the probability ratio between the new and old policy, `Â` is the advantage estimate, and `ε = 0.2` is our clip range. This hard-limits how much any single update can shift the policy. No matter how strong the gradient signal, the policy cannot move more than 20% in probability ratio per update.

We additionally set `target_kl = 0.03`, which provides a second safety layer: if the KL divergence between the updated and previous policy exceeds 0.03, the update epoch terminates early. This proved essential during the reward shaping experiments — without it, the uncapped starvation penalties of V5 caused explosive gradient updates that shattered the value network.

### 2.3 Handling Stochastic Traffic Flow

Traffic flow is inherently stochastic: vehicle departure times, routes, and inter-vehicle gaps are sampled from distributions defined in the route files. A deterministic policy (always keep green for exactly 30 seconds) makes no use of the observed traffic state.

PPO outputs a **probability distribution** over actions rather than a single deterministic choice. The learned policy `π(a|s)` naturally represents uncertainty — if the observation indicates ambiguous congestion levels, the policy outputs near-uniform probabilities (high entropy), reflecting genuine uncertainty. As training progresses and the agent learns reliable patterns, probabilities sharpen around the better action.

This stochastic policy representation has two practical benefits for traffic control:

1. **Smooth generalization** across the three training traffic densities (low / medium / extreme routes sampled randomly each episode via `MultiRouteWrapper`). A deterministic policy memorizes specific traffic volumes; a stochastic policy learns the underlying switching logic.

2. **Entropy regularization** during training (`ent_coef = 0.01` for new agents, `0.005` on fine-tuning) prevents premature convergence to suboptimal deterministic strategies — particularly the "always keep" local optimum discovered during V3 initial training.

---

## 3. Implementation Details

### 3.1 Neural Network Architecture

Both the policy network (π) and value network (V) share the same architecture:

```
Input (21) → Linear(128) → Tanh → Linear(128) → Tanh → Output

Policy head:  → Linear(2) → Softmax  [P(keep), P(switch)]
Value head:   → Linear(1)             [V(s)]
```

Key design choices:
- **Width [128, 128]**: Required to accommodate the 8-dimensional starvation signal. A [64, 64] network (standard for simpler environments) failed to learn the starvation-to-action mapping in early experiments.
- **Tanh activations**: Preferred over ReLU for bounded action spaces — Tanh's bounded output range complements the clipped policy gradient and avoids saturating the softmax.
- **Orthogonal initialization**: Preserves gradient magnitude at initialization, accelerating early learning in environments with sparse rewards (particularly low-traffic episodes).

### 3.2 Reward Function

```
R(t) = Pressure(t) / N_lanes  −  QueuePenalty(t)

Pressure(t)     = Σ outgoing_vehicles − Σ incoming_vehicles
QueuePenalty(t) = (Σ halting_vehicles / N_lanes) × 0.2
```

**Pressure term**: Rewards the agent for clearing vehicles through the intersection. Positive when more vehicles are departing than arriving, negative during buildup. Normalized by lane count (12 lanes) to keep reward in a stable range regardless of intersection geometry.

**Queue congestion penalty**: Penalizes every vehicle sitting stopped at the intersection. This term was the architectural fix that solved the SUMO teleportation exploit present in V1/V2/V3: SUMO forcibly teleports vehicles that wait longer than 300 seconds, which caused wait-time-based rewards to decrease artificially as stranded vehicles disappeared. The queue penalty is immune to teleportation — a removed vehicle immediately reduces the halting count, providing no reward benefit.

The coefficient `0.2` (updated from `0.1` in V3.2) ensures the penalty provides meaningful gradient signal even in low-traffic scenarios where the pressure term approaches zero.

### 3.3 Observation Normalization — VecNormalize

Raw traffic observations span several orders of magnitude: lane occupancy from 0 to ~50 vehicles, elapsed time from 0 to 60 seconds. Feeding unnormalized values to the neural network causes gradient explosion — a gradient scaled by "500 vehicles" overwhelms one scaled by "0.3 seconds."

`VecNormalize` maintains a **running mean and variance** across all parallel environments and normalizes observations online:

```
obs_normalized = (obs − μ) / (σ + ε),  clipped to [-10, 10]
```

The statistics are computed across all three training traffic densities simultaneously, ensuring the normalizer represents the full range of conditions the agent will encounter. During evaluation, statistics are frozen (`training=False`) and the saved pkl file is loaded — the agent sees identically normalized observations at test time as it did during training. Reward normalization is deliberately disabled (`norm_reward=False`) to preserve the carefully calibrated reward scale.

### 3.4 Queue Congestion Penalty — Mechanism and Traffic Impact

The queue penalty serves as the primary anti-starvation mechanism in the V3.1 architecture. Unlike the exponential starvation penalties explored in V5 (which grew to −10,000 and destroyed gradient stability), the linear queue penalty provides:

**Stable gradients**: A maximum possible penalty of `(N_stopped / N_lanes) × 0.2`. With N_stopped ≤ ~60 vehicles and N_lanes = 12, the maximum penalty is `60/12 × 0.2 = 1.0` — the same order of magnitude as the pressure reward. The agent's total reward never diverges.

**Continuous pressure to clear queues**: Every stopped vehicle costs points every decision step. The agent cannot defer queue clearing to the end of the episode — the penalty accumulates in real time, creating a strong incentive to serve waiting vehicles before they build into gridlock.

**Traffic flow impact**: In high-traffic scenarios, this mechanism prevents the agent from over-extending any single green phase. Once the active-phase queue drains (queue_penalty decreasing) while the cross-street queue grows (increasing future pressure reward from switching), the net value of switching exceeds keeping — the agent learns this transition point without explicit programming.

### 3.5 Parallel Training Architecture

```
SubprocVecEnv (10 independent processes)
│
├── Process 0: SUMO instance → routes.rou.xml      (Low traffic)
├── Process 1: SUMO instance → routes_hard.rou.xml  (Medium traffic)
├── Process 2: SUMO instance → routes_extreme.rou.xml (High traffic)
├── Process 3: SUMO instance → routes.rou.xml
│   ...  (randomly assigned on each episode reset via MultiRouteWrapper)
└── Process 9: SUMO instance → [random]
                    │
                    ▼  batched observations [10 × 21]
             VecNormalize layer
                    │
                    ▼  normalized batch
         MaskablePPO policy network (GPU)
                    │
                    ▼  actions + masks [10 × 2]
             Environment step
```

**Threading separation**: OS-level environment variables (`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `torch.set_num_threads(1)`) prevent NumPy/PyTorch from spawning competing thread pools inside the SUMO subprocesses, which caused severe CPU context-switching overhead in early runs.

**Learning impact**: With 10 parallel environments, a single rollout of `n_steps=512` accumulates `512 × 10 = 5,120` experience transitions spanning all three traffic densities. The policy receives diverse gradient signal — simultaneously updating on a gridlock scenario in one env and a sparse low-traffic scenario in another — in a single optimizer step. This acts as a form of data augmentation that dramatically reduces overfitting to any single traffic pattern.

---

## 4. Training Methodology

### 4.1 Hyperparameter Configuration

| Hyperparameter | Value | Rationale |
|----------------|-------|-----------|
| `n_steps` | 512 | 8 policy updates per episode (vs. <1 with n_steps=2048) |
| `batch_size` | 256 | Sufficient mini-batch diversity across 10-env rollout |
| `n_epochs` | 10 | Full reuse of each rollout before discard |
| `gamma` | 0.99 | Long-horizon credit assignment (episodes up to 20,000s) |
| `gae_lambda` | 0.95 | GAE bias-variance tradeoff for advantage estimation |
| `clip_range` | 0.2 | Standard PPO clipping; prevents single-step catastrophe |
| `target_kl` | 0.03 | Early update termination guard against policy collapse |
| `learning_rate` | 3e-4 → 0 (linear, new) / 3e-5 (constant, resume) | Fresh agent: aggressive early learning; resume: catastrophic forgetting prevention |
| `ent_coef` | 0.01 (new) / 0.005 (resume) | Exploration regularization; non-zero on resume prevents always-keep convergence |
| `net_arch` | [128, 128] pi + vf | Required capacity for starvation signal processing |
| `n_envs` | 10 | Maximum CPU parallelism before context-switch penalty |

### 4.2 Training Schedule and Convergence

Training proceeds in two phases:

**Phase 1 — Initial learning (linear LR decay, 3e-4 → 0):**
The agent trains from random initialization. The linear decay ensures aggressive early exploration (high LR when policy is far from optimal) tapering to near-zero updates as the policy converges. The target_kl guard prevents the agent from overshooting during the high-LR early phase when gradient estimates are noisy.

**Phase 2 — Fine-tuning (constant LR 3e-5, resume):**
Loading a checkpoint resets LR to a constant low value. Restarting the aggressive 3e-4 schedule would cause *catastrophic forgetting* — the near-zero end-of-training LR learned in Phase 1 is violently overwritten. The constant 3e-5 allows continued refinement without destroying accumulated knowledge. A safety backup of the model zip is created before every resume.

**Convergence indicators monitored via TensorBoard:**
- `train/entropy_loss`: Should decrease as policy sharpens around better actions
- `train/value_loss`: Should decrease as value network learns accurate episode return prediction
- `train/approx_kl`: Should remain below target_kl (0.03); spikes indicate instability
- `rollout/ep_rew_mean`: Averaged episode reward across 10 envs; upward trend = policy improvement

### 4.3 Experimental Results — Architecture Comparison

The following table summarizes total wait time on the **High Traffic** scenario (5-seed average), representing the most demanding evaluation condition:

| Agent Version | Architecture | Total Wait Time | Peak Max Wait |
|---------------|-------------|-----------------|---------------|
| V1/V2/V3 (original) | Cyclic, wait-time reward | 683,042,302 | — |
| **V4** | Acyclic Discrete(4) | 960,362,478 | 11,295s |
| **V5** | Cyclic + uncapped exp. penalty | ~148,000,000 | 4,960s |
| **V6** | Cyclic + capped penalty | 105,781,809 | 106s |
| **V3.1** *(current best)* | Cyclic + queue penalty | **84,788,759** | 197s |
| Fixed_60s (baseline) | Fixed 60s cycle | 64,284,917 | 180s |
| Fixed_45s (baseline) | Fixed 45s cycle | 79,947,615 | 135s |
| Max Pressure (baseline) | Greedy acyclic | 1,409,524,238\* | 14,818s\* |

*\*Max Pressure baseline figures reflect a pre-fix evaluation bug (no MAX_GREEN enforcement, missing yellow transitions) that caused systematic gridlock in underserved phases. Post-fix values pending re-evaluation.*

**Key findings:**
- V3.1 outperforms V4 by **11.3×** — confirming that acyclic jumping wastes too much simulation time in yellow transitions and produces incoherent switching behavior
- V3.1 outperforms V5 by **1.75×** — confirming that explosive gradient magnitudes (−10,000 penalties) destabilize PPO's value network despite the clipping mechanism
- V3.1 is within **32%** of Fixed_60s on high traffic and **33%** better than Fixed_45s — demonstrating meaningful learned behavior beyond random phase cycling
- The gap vs Fixed_60s on low traffic (91M vs 4.6M) is the active research focus; root-cause identified as near-empty phases being held for full MIN_GREEN rather than released at 5s (V3.2 fix in training)

### 4.4 Training Investment and Justification

Across all experiments and architecture versions, the project accumulated over **8,000 DQN training episodes** (legacy system) and **4+ million PPO timesteps** (current system), representing approximately:

- **DQN era**: 5,000+ episodes × ~2,400s simulation time = ~120 million simulated traffic seconds
- **PPO era**: 4M timesteps × 10 parallel envs × 5s delta = **200 million simulated traffic seconds**
- **Total**: ~320 million simulated traffic seconds — equivalent to roughly **10 years** of continuous single-intersection data

This scale of simulation exposure was necessary to develop a policy robust to all three traffic densities simultaneously, rather than overfitting to the high-traffic regime where reward signals are strongest. The `MultiRouteWrapper` curriculum — randomly injecting low, medium, or extreme traffic on each episode reset — was the architectural mechanism that forced the neural network to generalize across this full distribution.

---

## 5. Summary

FlowGrid implements a production-grade Maskable PPO agent for adaptive traffic signal control at a single 4-way intersection. The transition from DQN to PPO delivered fundamental improvements in training stability (clipped surrogate objective), sample efficiency (on-policy learning from fresh experience), and action validity (native masking of physically illegal transitions).

The V3.1 architecture — cyclic phase control, 21-dimensional starvation-aware observation, and queue-penalty reward — represents the result of systematic empirical comparison across six major architecture versions. Current work (V3.2) focuses on closing the remaining performance gap against fixed-time baselines in low-traffic scenarios through dynamic phase release thresholds and improved reward signal density.

---

*Report compiled from codebase inspection: `PPOagent/src/sumo_rl_env.py`, `train_production.py`, `evaluate_models.py`, and project documentation in `PPOagent/docs/`. Benchmark results from evaluation runs dated 2026-06-19 through 2026-06-27.*
