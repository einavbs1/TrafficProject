# FlowGrid — DQN priority and fairness

What the agent is taught to prioritize, and how that relates to **empty green** vs **queued red** approaches.

**Policy change history:** [CHANGELOG.md](CHANGELOG.md) · **Fresh training after ~20k old policy:** [FRESH_START.md](FRESH_START.md)

## Previous policy era (for reference)

Before the **balanced** update (see changelog), training used:

- `transit_delay_multiplier: 2.5` on **weighted** delay (buses dominated the delay signal).
- **Instant** emergency preemption (phase could switch as soon as an emergency was on red).
- Compare often showed: **better bus/emergency**, **worse all-vehicle wait** than fixed-time baseline.

The sections below describe the **current** policy unless noted.

## Priority order (reward)

From `dqn_policy_config.yaml` (highest influence first):

1. **Spillback** — avoid gridlock (`spillback_penalty`).
2. **Delay change** — reduce waiting time step by step:
   - **All vehicles (cars + buses + emergency)** count **equally** in the base term (`delay_delta_scale`).
   - **Extra** terms: `transit_priority_scale` × bus wait change, `emergency_priority_scale` × emergency wait change.
   - Default: buses ≈ **1.4×** influence on delay (not 2.5× on the whole network).
3. **Throughput** — reward vehicles that finish their trip.
4. **Fairness** — balance wait across N / S / E / W; penalize **starving** approaches.
5. **Switch / invalid action** — small costs for phase changes and illegal holds.

Older checkpoints trained with `transit_delay_multiplier: 2.5` on **weighted** delay will keep favoring buses until you **resume train** with the new reward shape.

### Tune cars vs buses

| Goal | `transit_priority_scale` | `emergency_priority_scale` |
|------|--------------------------|----------------------------|
| **More like baseline on total wait** | `0.2` – `0.3` | `0.2` |
| **Balanced (default)** | `0.4` | `0.35` |
| **Bus focus (old behavior)** | `1.5` | `0.5` |

After any change, run **`--resume`** for 300–500 episodes and Compare again.

## Empty green → serve other arms (what you asked for)

**Goal:** If the current green direction has **no real demand**, give service to approaches that **do** have vehicles waiting.

### Built-in behavior (no Compare-specific hack)

| Layer | Behavior |
|-------|----------|
| **Actuated controller** | `best_inactive_arm_to_serve()` picks a red arm with enough queue/wait and switches the ring toward it. |
| **Action mask** | When a switch is **required**, the agent must **advance** (cannot hold). |
| **Reward — inactive wait** | Penalty when red arms wait a long time while green demand is low (`inactive_wait_weight`, `inactive_wait_threshold`). |
| **Reward — starving arms** | Extra penalty when one arm waits much more than others. |
| **Reward — empty green** | Extra penalty when green has no queue but a red arm does (`starving_arms_weight × red queue`). |

### Code change (DQN only)

After minimum green time, if **green demand is 0** and another arm has at least **`switch_min_vehicles`** (default 3) queued, the environment **requires** a phase switch. Fixed-time baseline is unchanged (still uses fixed 60 s / 25 s rotation).

### Tuning knobs (`dqn_policy_config.yaml`)

```yaml
reward:
  delay_delta_scale: 1.0
  transit_priority_scale: 0.4      # lower = cars matter more in training
  emergency_priority_scale: 0.35
  throughput_per_vehicle: 0.75     # clearing the junction helps everyone
  starving_arms_weight: -0.4
  inactive_wait_weight: -0.05
  inactive_wait_threshold: 30

constraints:
  switch_min_vehicles: 3
  switch_min_wait_seconds: 25
  min_green_cap_seconds: 60
  # compare.dqn_max_green_seconds: 60  # aligns with baseline-like rotation
```

To push **even more** “don’t hold empty green”: increase `|starving_arms_weight|`, lower `inactive_wait_threshold`.

To push **lower car wait**: lower `transit_priority_scale` to `0.25`, raise `throughput_per_vehicle` slightly, then **`--resume`**.

## Plan 2 signals (what you see in SUMO)

On **Plan 2** (`opposite_thru_rt_then_thru`) with `separate_right_turn: true`:

| Movement | Signal in GUI |
|----------|----------------|
| **Right turn** | **Always green** on its own lane (does not wait for the DQN ring) |
| **Through (straight)** | Green only during **through** phases (`N+S thru`, `N+S thru+right`, etc.) |
| **Left turn** | Green only during **LEFT** phases (`N+S left`, `E+W left`) |

If Compare looks like “only left and right are green,” **right is normal** — check whether **through** lanes ever get a green arrow. If through stays red for a long time, the controller was over-serving LEFT-only phases.

**Fix (2026-05-31):** LEFT is chosen only when **left queue > through queue** on that approach (not when a single left car is waiting). Through phases are preferred when straight demand is equal or higher.

Re-run Compare after updating; collapsed policies may still need `--fresh` training.

## Bus and emergency — next green (not instant cut)

When a bus or emergency vehicle is waiting on **red**, FlowGrid does **not** flip the signal immediately (by default). Instead:

1. **Finish minimum green** on the current phase (and normal empty-green / fairness rules still apply).
2. On the **next allowed switch**, route the phase ring to that arm first — **if** other approaches are not being starved.

Configured in `priority_service` (`dqn_policy_config.yaml`):

```yaml
priority_service:
  instant_emergency_preempt: false   # true = old behavior (cut green as soon as emg seen)
  defer_emergency_to_next_green: true
  defer_transit_to_next_green: true
  starvation_queue_margin: 2       # skip priority if another arm has many more cars
  starvation_wait_ratio: 1.5       # skip priority if another arm waited much longer
```

- **`is_emergency_active`** in the observation still means “emergency on a red approach” — not “we just preempted.”
- Reward still adds modest **`emergency_priority_scale`** / **`transit_priority_scale`** on delay deltas so the agent learns to clear everyone, not only buses.

## Observation (what the agent sees)

Includes per-movement queues, per-arm empty/red-wait flags, time in phase, emergency flag, and **transit counts per arm** — so it can learn where buses are waiting.

## Fixed-time baseline (Compare reference)

- Rotates phases on a **fixed schedule** (~60 s through, ~25 s left per Plan 2 step).
- Does **not** use the DQN reward.
- Strong on **total wait** because rotation is predictable and never “holds empty green” too long.

## Did fair Compare injection hurt DQN?

**No.** Fair Compare:

1. Baseline: random inject until **Inject until (s)** → drain to **0 vehicles** → record every departure.  
2. DQN: **same** vehicles (same routes, lanes, depart times) → drain to **0 vehicles**.

Both see the **same fleet** (e.g. 437/437). Different **wait totals** come from **different signal timing**, not from extra cars on the DQN side.

If DQN total wait is higher, the policy is **worse at clearing everyone**, not cheated by injection.

## Related docs

- [COMPARE.md](COMPARE.md)  
- [TRAINING.md](TRAINING.md)  
- [FRESH_START.md](FRESH_START.md)  
- [CHANGELOG.md](CHANGELOG.md)
