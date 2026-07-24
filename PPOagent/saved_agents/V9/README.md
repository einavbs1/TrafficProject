# V9 — HYPOTHESIS REJECTED (V8 remains champion)

**Status:** COMPLETE — 6M steps, model `20260702_...`, evaluated 2026-07-02  
**Goal:** Improve V8's weakest margin — High traffic (-7.9% vs Fixed_60s)  
**Result:** No improvement on High, slight regression on Low. **Observation saturation was NOT the high-traffic bottleneck.**
**Key innovation (tested):** De-saturated observation — same 150m camera, more information extracted

## The problem V9 solves

Approach lanes are 467m; the camera sees the last 150m (~20 vehicles/lane max).
In extreme traffic every lane's demand hits 1.0 and every starvation score hits
1.0 (45s cap) — **all 16 traffic dims flatline to identical values exactly when
prioritization matters most.** V8 degrades into a near-fixed cycler there:
only -7.9% vs Fixed_60s on High, while winning -36%/-50% on Medium/Low where
the observation still has contrast.

Camera range stays 150m — that's the real-world sensor limit and a hard
product constraint. V9 extracts more from the same view.

## Architecture changes from V8

| Change | V8 | V9 |
|--------|-----|-----|
| Camera range | 150m | 150m (**unchanged — real-world limit**) |
| Starvation obs | `min(max_wait/45s, 1)` — saturates at 45s | **`log(1+max_wait)/log(1+300s)`** — contrast to 5 min |
| Total-wait obs | — | **NEW 8 dims**: `log(1+sum_wait)/log(1+6000s)` per group |
| Observation | 21-dim | **29-dim** |
| Reward | diff_wait − starvation@45s | unchanged (45s score computed separately) |
| Hard empty mask | Yes | Yes (unchanged) |

Why log scale: waiting time is the only camera-measurable signal that keeps
growing when the picture stops changing (window visually full). Log keeps
resolution at both small and large waits without exploding the value range.

## Smoke test evidence (extreme traffic, 10 sim-minutes)

```
demands      : [0.95, 0.65, 1.0, 0.9, 0.95, 0.68, 1.0, 0.9]
starvation   : [0.52, 0.71, 0.71, 0.65, 0.52, 0.71, 0.71, 0.64]
waitsum (new): [0.55, 0.66, 0.78, 0.78, 0.55, 0.66, 0.78, 0.78]
```
Under V8's encoding most of these dims would read a flat 1.0. V9 keeps contrast.

## Target results

| Scenario | V8 | V9 target | Fixed_60s |
|----------|-----|-----------|-----------|
| Low      | 2.29M ✅ | hold ~2.3M | 4.61M |
| Medium   | 17.3M ✅ | hold ~17M | 27.0M |
| High     | 59.2M ✅ (-7.9%) | **< 57M (-11%+)** | 64.3M |

## Results (5-seed average, eval_20260702_124522)

| Scenario | V9 | V8 (champion) | Fixed_60s | V9 vs V8 |
|----------|-----|---------------|-----------|----------|
| Low      | 2.78M | **2.29M** | 4.61M | ❌ 21% worse |
| Medium   | 17.29M | 17.30M | 27.0M | ≈ tie |
| High     | 59.38M | 59.19M | 64.3M | ≈ tie (within seed noise) |

### Why the hypothesis was rejected

**High traffic per-seed, V9 vs V8 — nearly identical:**
```
V9 High: 57.8  56.2  56.8  62.8  63.3   (mean 59.38)
V8 High: 57.4  56.8  57.0  62.3  62.5   (mean 59.19)
```
Both show the SAME bimodal split — 3 seeds ≈57M, 2 seeds ≈63M. The de-saturated
observation changed nothing on High. Giving the agent more perceptual contrast
did not translate into better decisions.

**The bimodality is demand-driven, not policy-driven.** The 57M/63M split
follows the SUMO traffic seed (the demand realization), not the agent. This
means the high-traffic wait is dominated by **demand approaching intersection
capacity** — a queuing-theory limit, not a perception or timing limit. When
demand ~ capacity, no signal policy can do much; you're fighting physics.

**Low regressed** (2.29M → 2.78M, consistent on every seed, outside the ±3%
noise): the 8 extra observation dims added input noise to an already-solved,
near-empty scenario where they carry no useful signal.

### Verdict
V8 stays champion. V9's environment change is kept for the record but not
promoted. **Conclusion: V8's -7.9% on High is likely near the practical
ceiling for signal control on this map's saturated-demand scenario.**

## Hyperparameters (same as V8)

| Param | Value |
|-------|-------|
| learning_rate | 3e-4 → 0.0 linear |
| ent_coef | 0.02 |
| n_steps | 512 |
| batch_size | 512 |
| net_arch | [128, 128] Tanh |
| num_cpu | 10 SUMO + 2 PyTorch threads |
| device | cuda |

## Scripts

| File | Purpose |
|------|---------|
| `sumo_rl_env_V9.py` | Environment with 29-dim de-saturated observation |
| `sumo_rl_env.py` | Shim for evaluate_models.py import resolution |
| `train_V9.py` | Fresh 6M training (crash recovery + resume guards built in) |
| `evaluate_V9.py` | Evaluation script |

## How to train and evaluate

```
cd PPOagent/saved_agents/V9
python train_V9.py --timesteps 6000000
python evaluate_V9.py --seeds 5
```
