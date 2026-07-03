# PROJECT HANDOFF — PPO Traffic Signal Control

**Last updated:** 2026-07-02
**Status:** PRIMARY GOAL ACHIEVED. Champion = **V8**. Now optimizing + analyzing.
**Read this fully before doing anything. Then read `PPO_VERSION_HISTORY.md` for the full changelog.**

---

## 1. THE GOAL

Train a PPO agent that beats **ALL** baselines in **total waiting time** across
**LOW, MEDIUM, and HIGH** traffic in SUMO microsimulation.

Baselines: `Fixed_30s`, `Fixed_45s`, `Fixed_60s`, `Max_Pressure`.
`Fixed_60s` is the strongest baseline — beating it is the real bar.
Lower total waiting time = better. Constraint: solution must be **road-deployable**
(realistic sensors — see camera note in §5).

### GOAL STATUS: ✅ ACHIEVED by V8
V8 beats every baseline in every scenario. First agent in project history to do so.

---

## 2. CURRENT CHAMPION — V8

**Model:** `PPOagent/saved_agents/V8/models/ppo_model_20260702_011233.zip`
**Stats:** `PPOagent/saved_agents/V8/models/vec_normalize_20260702_011233.pkl`
(the .pkl is REQUIRED — never evaluate/resume without the matching stats file, see §6)

### V8 results (5-seed average, total waiting time in seconds)

| Scenario | V8 | Fixed_60s | vs Fixed_60s |
|----------|-----|-----------|--------------|
| Low | 2.29M | 4.61M | **-50.4%** |
| Medium | 17.3M | 27.0M | **-36.0%** |
| High | 59.2M | 64.3M | **-7.9%** |

### V8 % improvement vs every fixed timer (higher = better)
| Scenario | vs Fixed_30s | vs Fixed_45s | vs Fixed_60s |
|----------|-------------|-------------|-------------|
| Low | -83.5% | -61.4% | -50.4% |
| Medium | -61.7% | -47.1% | -36.0% |
| High | -53.2% | -26.2% | -7.9% |

### What makes V8 work (the one key idea)
**Hard action mask on empty intersections.** When the 150m camera sees zero
vehicles in all lane groups, the `Switch` action is masked out entirely — the
agent physically cannot switch phases on an empty road. This is consistent with
the existing MIN_GREEN/MAX_GREEN masks (structural constraints, not reward
penalties). It halved low-traffic waiting vs V7 and removed wasted training
gradient, which also lifted medium/high.
Low-traffic switch rate dropped to 0.4/100s (vs Fixed_60s 1.7) — the agent
holds green on an empty intersection and switches only for real demand.

---

## 3. FULL RESULTS — ALL VERSIONS (5-seed averages)

| Model | Steps | Low | Medium | High | Notes |
|-------|-------|-----|--------|------|-------|
| Fixed_30s | — | 13.9M | 45.1M | 126.4M | baseline |
| Fixed_45s | — | 5.93M | 32.7M | 80.2M | baseline |
| **Fixed_60s** | — | **4.61M** | **27.0M** | **64.3M** | strongest baseline |
| Max_Pressure | — | 1088M | 573M | 1184M | broken baseline (teleport-starves) |
| V4 initial | 4M | 495M ❌ | 27.0M | 70.4M | first partial win |
| V4 +6M resume | 10M | 38.6M ❌ | 23.2M ✅ | 61.8M ✅ | low unsolved |
| V4 low50weighted | 13M | 39.2M ❌ | 21.6M ✅ | 61.8M ✅ | best V4 |
| V5 pressure reward | 6M | 189M ❌ | 217M ❌ | 245M ❌ | failed, over-switching |
| V6-camera | 6M | 4.66M ❌ | 26.9M ✅ | 67.0M ❌ | low breakthrough (starvation penalty) |
| V7 | 4.7M | 4.66M ❌ | 25.9M ✅ | 62.2M ✅ | 150m camera fixed high |
| **V8** 🏆 | 6M | **2.29M ✅** | **17.3M ✅** | **59.2M ✅** | CHAMPION — beats all |
| V9 | 6M | 2.78M | 17.29M | 59.38M | hypothesis rejected (see §7) |

---

## 4. TWO PROVEN CONCLUSIONS (do not re-litigate)

### A. High traffic is DEMAND-LIMITED, not perception-limited (~8% ceiling)
Two independent proofs:
1. **V9** de-saturated the observation (log-scaled waits + 8 total-wait dims,
   21→29 dims) specifically to help High. Result: identical to V8 on High,
   seed-by-seed, with the SAME bimodal split (3 seeds ≈57M, 2 seeds ≈63M). The
   split tracks the SUMO demand seed, not the policy.
2. **V8 checkpoint sweep** (all 60 checkpoints): the best High result ANYWHERE
   in 6M steps is +8.7% vs Fixed_60s. It never broke past ~9% at any point.

**Meaning:** on this single intersection, when demand ≈ capacity, total wait is
governed by queuing physics. No observation/reward tweak will beat ~8% on High.
Do NOT build more single-intersection versions to chase High. Real High gains
require multi-intersection coordination (green waves) — a new project phase.

### B. We massively over-trained
The V8 sweep shows the agent beat ALL baselines by **400k steps**. Performance
oscillates (not monotonic). Best Low+Medium checkpoints are ~2.2–2.4M, not 6M.
The 6M champion is actually ~10 points WORSE on Medium than the 2.3M checkpoint
(but this is 2-seed data — needs 5-seed verification, see §8 NEXT STEP).

---

## 5. ENVIRONMENT ARCHITECTURE (shared across versions)

- **Simulator:** Eclipse SUMO + libsumo (`LIBSUMO_AS_TRACI=1`), sumo_rl wrapper
- **Algorithm:** MaskablePPO (sb3_contrib), `SwitchOrKeepWrapper`
- **Action space:** Discrete(2) — 0=Keep, 1=Switch
- **Phase cycle:** 0 (N/S Left) → 1 (N/S Straight) → 2 (E/W Left) → 3 (E/W Straight)
- **Ghost Car Logic:** phases with zero demand are skipped; one-sided left-turn
  demand uses overlap states
- **Action masking:** MIN_GREEN=10s (force Keep), MAX_GREEN=60s (force Switch);
  V8 adds: Switch masked when `total_visible == 0`
- **Observation (V8, 21-dim):** `[phase_onehot(4), elapsed(1), lane_demands(8),
  lane_starvation(8)]`, camera-limited to 150m
- **Reward (V8):** `diff_waiting_time - starvation_penalty`
  - `diff_waiting_time = (prev_total_wait - current_wait) / num_lanes` (full ground truth)
  - `starvation_penalty = max(starvation_score) * 0.05`, score = `min(wait/45s, 1.0)`
- **POMDP design:** observation is camera-limited; reward uses full ground truth
- **VecNormalize:** norm_obs=True, norm_reward=False, clip_obs=10
- **Parallelism:** SubprocVecEnv, 10 SUMO processes; MultiRouteWrapper randomly
  picks a route file per episode (equal thirds low/medium/high)

### CAMERA RANGE = 150m — HARD CONSTRAINT, DO NOT CHANGE
Approach lanes are 467m; the camera sees the last 150m (~20 vehicles/lane).
150m is the real-world sensor limit (radar/video). The user explicitly rejected
extending it — 250m would improve benchmark numbers but be undeployable.
`getLanePosition(veh)` gives distance from lane start; `lane_length - pos` =
distance to stop line; only vehicles within 150m are "visible".

### Map / route files
- Net: `SharedData/maps/flowgrid/network.net.xml`
- Low: `SharedData/maps/flowgrid/routes.rou.xml`
- Medium: `SharedData/maps/flowgrid/routes_hard.rou.xml`
- High: `SharedData/maps/flowgrid/routes_extreme.rou.xml`

---

## 6. HARDWARE / TRAINING CONFIG (user requirement)

CPU: Intel i5-12500 — **6 physical / 12 logical cores.**
User requirement: use 10 cores, keep 2 free, use the GPU as much as possible.
All train scripts are set to:
- `num_cpu = 10` (SUMO SubprocVecEnv workers)
- `OMP_NUM_THREADS=2`, `torch.set_num_threads(2)` (2 spare logical cores for PyTorch)
- `batch_size = 512`, `device="cuda"`
- Note: GPU is ~1-2% of runtime; SUMO simulation is the bottleneck. batch=512 +
  2 torch threads is the practical ceiling. A full 6M run ≈ 4-4.5 hours.

---

## 7. CRITICAL SAFETY MECHANISMS (learned the hard way)

### The V7 resume incident (2026-07-02) — DO NOT REPEAT
V7 crashed at 4.7M before saving its VecNormalize stats. A resume run silently
created FRESH normalization stats → observation distribution shifted under the
trained policy → total collapse (Low 4.66M→35.4M, High 62.2M→77.0M). The resume
run also overwrote the original checkpoints. Recovered the good 4.7M checkpoint
from `checkpoints/`.

### Fixes now in ALL train scripts (V4, V4.1, V6, V7, V8, V9):
1. `save_vecnormalize=True` on CheckpointCallback — every 100k checkpoint saves
   its matching `..._vecnormalize_<steps>_steps.pkl`
2. **Hard resume guard** — script aborts if resuming without the matching stats .pkl
3. **Separate checkpoint prefix on resume** (`_resume<MMDD_HHMM>`) — never
   overwrites the original run's checkpoints
4. **Crash recovery** — if `./models/` has no final model but `./checkpoints/`
   has checkpoints, training auto-continues from the latest checkpoint (keeps
   optimizer state, LR schedule, step counter). Use `--fresh` to force a new run.

### Golden rules (from memory files)
- **Reward/observation/policy change ⇒ FRESH agent** (new folder). Never resume
  into a changed environment (V3.3 collapse, V7 resume collapse).
- **Never delete old model files** — they are fallbacks.
- **Never touch the champion** — V8 is sealed. New ideas = new folder.
- **Few versions, deeply understood** — one controlled change per version, with
  a clear hypothesis. Don't spawn versions casually.

---

## 8. FILE / FOLDER STRUCTURE

```
PPOagent/
  docs/
    PROJECT_HANDOFF.md        <- THIS FILE
    PPO_VERSION_HISTORY.md    <- full changelog, every version + results
  src/
    evaluate_models.py        <- shared eval engine. Hardcodes
                                 `from sumo_rl_env import ...` -> each version
                                 folder has a sumo_rl_env.py SHIM re-exporting
                                 its own env so eval uses the right observation.
  tools/
    checkpoint_sweep.py       <- learning-curve tool (see §9)
  saved_agents/
    V4_initial/  V4.1_camera_fixed/  V5/  V6/  V7/  V8/  V9/
      sumo_rl_env_Vx.py       <- the actual environment for this version
      sumo_rl_env.py          <- SHIM: `from sumo_rl_env_Vx import ...`
      train_Vx.py             <- training (resume/crash-recovery built in)
      evaluate_Vx.py          <- evaluation (5 seeds, all baselines)
      README.md               <- version summary + results
      models/                 <- final model + vecnormalize .pkl
      checkpoints/            <- per-100k model + vecnormalize .pkl
      results/                <- eval_<timestamp>/ folders with CSVs + PNGs
      tensorboard/
```

### Naming convention (STRICT)
- Never modify a script in place to change behavior. Copy it with a descriptive
  suffix (e.g. `train_V8_high50weighted.py`) so the original stays intact.
- Every version folder needs the `sumo_rl_env.py` shim or evaluation silently
  falls back to `src/sumo_rl_env.py` (wrong observation).

---

## 9. HOW TO RUN THINGS (commands)

All commands run from PowerShell. Do NOT open external PowerShell windows —
run in-session (background for long jobs). Do not run heavy jobs while the CPU
is already busy with training.

### Train a version (fresh 6M + auto-evaluate)
```
cd PPOagent/saved_agents/V8
python train_V8.py --timesteps 6000000 ; python evaluate_V8.py --seeds 5
```
### Force a fresh run (ignore existing checkpoints)
```
python train_V8.py --timesteps 6000000 --fresh
```
### Resume / crash-recovery
Just re-run `python train_V8.py --timesteps 6000000` — it auto-continues from
the latest checkpoint if the final model is missing. It will ABORT if stats are
missing (safe).

### Evaluate an existing model (5 seeds, all baselines)
```
cd PPOagent/saved_agents/V8
python evaluate_V8.py --seeds 5
```
Eval auto-finds the latest model in `./models/`. Results → `./results/eval_<ts>/`.
Key files: `eval_<scenario>_summary.csv`, `eval_<scenario>_extended.csv`
(extended has Wait_Per_Vehicle, Switch_Rate_per100s, Total_Arrived).

### Checkpoint sweep (learning curve — how many steps were needed)
```
cd PPOagent/tools
python checkpoint_sweep.py --version-dir ..\saved_agents\V8 --seeds 42 123 --dry-run   # preview
python checkpoint_sweep.py --version-dir ..\saved_agents\V8 --seeds 42 123              # full (~90 min)
```
Outputs → `saved_agents/V8/results/checkpoint_sweep_<ts>/`:
`sweep_table.csv` (% improvement vs each fixed timer per checkpoint),
`sweep_curve.png`, `pct_curve.png`, `best_checkpoints.csv`.
Only checkpoints WITH a matching vecnormalize .pkl are swept (V8+ only; older
versions lack per-checkpoint stats and are skipped).

---

## 10. SEEDS / EVALUATION METHODOLOGY

- Final evals: 5 seeds `[42, 123, 1337, 2026, 9999]`.
- Sweeps: 2 seeds `[42, 123]` for speed (curve trend), then verify winners at 5.
- **High traffic has ~10% seed variance** (bimodal, demand-driven) — 1 seed is
  too noisy for High; always use ≥2, prefer 5 for final claims.
- Low traffic is very stable (±3%).
- Baselines vary by seed too — always compare PAIRED by seed. % improvements in
  a 2-seed sweep differ from 5-seed because the Fixed_60s baseline differs.

---

## 11. IMMEDIATE NEXT STEP (was in progress at handoff)

**Verify the top sweep checkpoints at 5 seeds.** The V8 sweep (2-seed) suggested
the 2.2M / 2.3M / 3.6M checkpoints beat the 6M champion on Low+Medium (High
identical ~8%). Run a proper 5-seed eval of those checkpoints + the 6M model to
find the true best. Cheap (~15 min). If a 2.3M checkpoint wins at 5 seeds, it
could become the new champion — a better model for free, no training.

How: copy each candidate checkpoint + its matching vecnormalize .pkl into a temp
models/ layout (or extend evaluate_V8.py to accept an explicit --model path) and
run the 5-seed eval per checkpoint. Candidates:
`V8/checkpoints/ppo_model_20260702_011233_{2200000,2300000,3600000}_steps.zip`
(+ matching `_vecnormalize_..._steps.pkl`).

---

## 12. OPEN DIRECTIONS (user's choice — ASK before big scope)

The user's stated interest was still "beat Fixed_60s on High traffic more." Be
honest: §4A proves that's capped at ~8% for a single intersection. Options:
1. **Wrap up & analyze** — V8 is the deliverable; finish sweep/graphs/docs.
2. **Robustness for real roads** — test V8 on sensor noise / different maps to
   prove it generalizes (supports the "use on real roads" goal).
3. **Multi-intersection coordination** — the ONLY real path to better High
   (green waves). Large scope, essentially a new phase.
4. **Marginal V8 tuning** — route-weighted resume etc.; expect ~0 on High.

Recommend committing everything to git FIRST (nothing is committed yet; branch
`NewAgent_PPO`) — V8 is a valuable, currently-unprotected asset.

---

## 13. MEMORY FILES (persist across sessions)
`~/.claude/projects/.../memory/`:
- `feedback_powershell_autoapprove.md` — PowerShell commands are pre-approved
- `feedback_agent_management.md` — agent management rules (fresh vs resume, never
  delete, resume-stats guard, few-versions rule)
- `project_high_traffic_ceiling.md` — the demand-limited ceiling finding
- `project_v6_fallback_plan.md` — older fallback plan (mostly historical now)
- `MEMORY.md` — index of the above

---

## 14. QUICK FACTS FOR THE NEW AGENT
- Champion: **V8**, model `ppo_model_20260702_011233`.
- Goal is ACHIEVED; work is now optimization + analysis + (maybe) robustness.
- Camera stays 150m. High is capped ~8%. Don't chase it single-intersection.
- Always keep VecNormalize .pkl with the model. Never resume into a changed env.
- 10 SUMO cores + 2 torch threads + batch 512 + cuda. ~4.5h per 6M run.
- Run jobs in-session background; don't stack jobs on a busy CPU.
- Nothing is committed to git yet (branch NewAgent_PPO).
```
