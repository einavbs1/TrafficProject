# FlowGrid Compare — fair baseline vs DQN

This document explains how the **Compare** tab runs two simulations and how waiting-time numbers are calculated.

## Goal

Compare answers: *On the **same** traffic demand, does the DQN signal policy reduce delay more than fixed-time control?*

To make that fair, both runs must use the **same vehicles** (same count, routes, lanes, and depart times). Only the **traffic-light policy** differs.

---

## Phases of a compare run

### Phase 1 — Fixed-time baseline (random injection, then drain)

1. **SUMO starts** with a copy of the map routes where every `<flow>` stops at `compare.inject_seconds` (default **450 s**). Before that time, vehicles are inserted randomly using the same probabilities as training (`routes.rou.xml`).

2. **While vehicles are injected**, each insertion is recorded:
   - vehicle id  
   - type (car / bus / emergency)  
   - route (defines **direction**, e.g. north→south straight)  
   - `depart` time  
   - `departLane` when the map defines it (Plan 2: lane 0 = through, lane 1 = left)

3. **After 450 s** — no new random vehicles. Flows have `end="450"` in the temporary route file.

4. **Drain** — simulation continues with fixed-time signals until:
   - **0 vehicles** on the network (`require_empty_network`), and  
   - approach **queues are clear** for 2 consecutive control steps (20 s each).

5. If vehicles are **still on the map** when the run stops, compare **does not start DQN** and shows an error (raise `max_drain_sim_seconds` if needed). An empty map is enough to continue—even if the internal end label is `max_time` instead of `drained`.

6. The list of recorded departures is written to  
   `data/maps/<map>/.compare_cache/compare_replay_seed<N>_n<K>.rou.xml`.

### Phase 2 — DQN (exact replay, then drain)

1. SUMO **restarts** (3D window may flicker) with **only** the replay file — **no** random flows.

2. Each saved `<vehicle>` uses the same id, type, route, depart time, and depart lane as baseline.

3. The DQN policy controls phases (exploration off, ε = 0). Buses and emergency vehicles get **the next green** when a switch is allowed (after min green), not an instant phase cut; other arms are served first if they would be starved (`priority_service` in config).

4. Episode ends under the **same drain rules** until **0 vehicles** remain.

5. If DQN does not drain in time, compare reports an error.

---

## Why you previously saw `1366/1302` vehicles

That meant:

- **1366** vehicles were **recorded** when they entered during baseline.  
- Only **1302** were counted as “seen” during coarse 20 s control steps (some had already left between steps), **or** the run ended on a **time limit** while cars were still on the map.

The updated logic:

- Stops injection at **450 s**.  
- Ends only when the network is **empty** (or fails clearly).  
- Fleet size for both panels = **number of recorded departures** (should match on baseline and DQN).

---

## What is held equal vs different

| Equal | Different |
|--------|-----------|
| Map, seed, SUMO config | Controller: fixed rotation vs DQN |
| Vehicle list, depart times, routes, lanes | Phase timing decisions (DQN) |
| Inject stop time (450 s) | — |
| Drain rule (0 cars) | — |

---

## Waiting time metrics

Each **control step** advances SUMO by **20 seconds** (`step_length`). After each step, metrics are sampled and **summed over all steps** in the episode.

### 1. All vehicles (`baseline_wait_all` / `dqn_wait_all`)

```text
sum over steps of  Σ  lane.getWaitingTime(lane)  on all approach lanes
```

SUMO’s lane waiting time accumulates while speed is below a threshold on that lane. This includes **cars, buses, and emergency** vehicles.

### 2. Bus / public transport (`baseline_transit_wait` / `dqn_transit_wait`)

Same idea, but only vehicles whose type/class is transit (e.g. `bus`):

```text
sum over steps of  Σ  vehicle.getWaitingTime(v)  for each bus on approach lanes
```

### 3. Emergency (`baseline_emergency_wait` / `dqn_emergency_wait`)

```text
sum over steps of  Σ  vehicle.getWaitingTime(v)  for each emergency vehicle on approach lanes
```

### 4. Bus + emergency (headline / priority sum)

```text
priority_wait_sum = transit_wait_sum + emergency_wait_sum
```

This is the **large number** shown in the main compare summary and used for “% improvement” in reports. **Cars are excluded** from that headline so buses and ambulances are visible in the score.

### Important details

- Wait is a **sum over the whole episode**, not an average per vehicle. More vehicles ⇒ larger totals.  
- Lower is better.  
- Charts color **green** for the side with **lower** wait on that metric, **red** for worse.

---

## Why baseline ~700 s but DQN ~4000 s?

Typical timeline for **baseline** (fixed-time):

| Phase | Sim time | What happens |
|--------|-----------|----------------|
| Injection | 0 → **450 s** | Random cars/buses/emergency spawn |
| Drain | 450 → **~700–900 s** | No new vehicles; fixed rotation clears the map |
| End | when **0 vehicles** | Episode stops |

So **~735 s is normal** for baseline — it finished draining. That is not “too fast”; it is “done.”

**DQN** used to share a **4050 s** ceiling (`450 + 3600` from config). If the policy **does not rotate** like fixed-time, buses sit at a red light for thousands of seconds until TraCI hits that cap — what you saw at **4054 s**.

After the fix, DQN time limit is roughly:

```text
baseline_sim_time + dqn_drain_extra_seconds   (default +600 s → ~1335 s if baseline was 735 s)
```

**Stall detection** is **off** by default (`stall_control_steps: 0`) so Compare does not stop while cars are still queued. DQN drain time is **baseline duration + 1500 s** (`dqn_drain_extra_seconds`) so the replay can finish clearing the map.

DQN also gets **`dqn_max_green_seconds: 60`** so one green phase cannot run unbounded (similar to baseline through phase length).

---

## Delay ms vs simulation seconds (important)

| Setting | What it changes |
|---------|------------------|
| **Inject until (s)** | SUMO **simulation time** while random cars/buses/emergency spawn. More seconds → **more vehicles** (~252 at 450 s, ~400+ at 800 s on Plan 2). |
| **Delay ms** | Only how long SUMO-GUI **pauses between micro-steps** so you can watch. **Does not change** sim time or vehicle count. |
| **0 ms delay** | Fastest run; one compare (baseline + DQN) is often **many minutes of sim time** but may finish in **~2–15 minutes wall-clock** on a typical PC (depends on traffic and CPU). |

Example with **inject 800 s** and **0 ms delay**:

- Baseline sim time often **~1000–1300 s** (800 s inject + ~200–500 s drain until empty).
- DQN sim time is capped near **baseline time + 600 s** (config `dqn_drain_extra_seconds`).
- Wall-clock time is **not** fixed to 50 s or 500 s — use **Inject until** for longer *simulation*.

---

## Configuration

In `data/defaults/dqn_policy_config.yaml` or the Compare tab **Inject until (s)** field:

```yaml
compare:
  inject_seconds: 800
  max_drain_sim_seconds: 3600      # baseline only: max drain after inject
  dqn_drain_extra_seconds: 600     # DQN max sim ≈ baseline_time + this
  dqn_max_green_seconds: 60        # force phase rotation during DQN
  stall_control_steps: 15            # end DQN if queue frozen 15×20s
```

- Increase **`max_drain_sim_seconds`** only if **baseline** fails to empty the map.  
- Increase **`dqn_drain_extra_seconds`** if DQN needs more time to clear than baseline (but policy is still poor if it stalls).  
- Longer injection: raise **`inject_seconds`** (e.g. 600) for both runs’ demand.

---

## Files involved

| File | Role |
|------|------|
| `routes.rou.xml` | Source probabilities and routes for the map |
| `.compare_cache/compare_baseline_inject450.rou.xml` | Flows with `end="450"` for baseline |
| `.compare_cache/compare_replay_seed42_n….rou.xml` | Exact `<vehicle>` list for DQN |
| `flowgrid/eval/evaluate.py` | Orchestrates baseline → replay → DQN |
| `flowgrid/eval/compare_replay.py` | Record departures, write replay XML |
| `flowgrid/core/episode_limits.py` | Drain-until-empty rules |

---

## Injection and “DQN worse on total wait”

Fair compare gives **both** methods the **same fleet** (e.g. 437/437). If DQN has **higher all-vehicle wait**, fixed-time handled that fleet better — **not** because DQN received more cars.

Raising **Inject until** only scales traffic for **both** sides. See [DQN_PRIORITY.md](DQN_PRIORITY.md) for reward vs baseline rotation.

---

## DQN does not start after baseline

Check the status line under the charts and the **DQN** panel:

| Symptom | Cause | Fix |
|--------|--------|-----|
| DQN panel **Skipped / failed**, message about vehicles on map | Baseline did not drain to 0 cars | Increase `compare.max_drain_sim_seconds` |
| Message **No trained model** | Missing `dqn_policy.pth` for this map | Train on the Train tab first |
| Message **wrong input size** | Old checkpoint vs current observation size | Train again (replaces incompatible model) |
| Baseline **Complete**, DQN stays **Waiting** | Job still running, or error not surfaced | Wait; re-run after fix above |

With **SUMO 3D** on, the baseline window closes and a **new** window opens for DQN (~1 s pause). That is normal.

---

## Quick checklist after a compare

- [ ] Baseline status: **Complete**, no error about vehicles left on map  
- [ ] DQN status: **Complete**  
- [ ] Vehicle counts: same `N/N` for cars, buses, emergencies on both sides  
- [ ] Green/red on each metric reflects **lower wait = green**

For training behavior (not compare), see [TRAINING.md](TRAINING.md). For priority and empty-green behavior, see [DQN_PRIORITY.md](DQN_PRIORITY.md). Policy changes: [CHANGELOG.md](CHANGELOG.md). Fresh training: [FRESH_START.md](FRESH_START.md).
