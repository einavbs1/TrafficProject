import os
import argparse
import shutil
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
from sb3_contrib import MaskablePPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from sumo_rl_env import create_sumo_env, SwitchOrKeepWrapper

def run_evaluation_task(args):
    model_name, model_type, route_file, seed, cycle_time, model_path, use_gui = args
    df = evaluate_model_on_seed(model_name, model_type, route_file, seed, cycle_time, model_path, use_gui)
    return model_name, seed, df

def evaluate_mp_on_seed(route_file, seed, use_gui=False):
    """
    Max-Pressure baseline with camera constraints, matching the PPO agent's field of view.

    Parameters
    ----------
    CAMERA_RANGE : metres from the stop line within which vehicles are visible.
    MIN_GREEN    : minimum green duration before a switch is allowed.
    MAX_GREEN    : safety cap -- forces a phase change after this many seconds.
    YELLOW_TIME  : fixed yellow-transition duration.

    Pressure formula (per phase j):
        P_j = Σ ( V_in(lane) − V_out(lane) )
    where V_in  = vehicles in incoming green lanes within CAMERA_RANGE of stop line
          V_out = vehicles in downstream (outgoing) lanes within CAMERA_RANGE of the
                  intersection entry point.
    Only vehicles within the camera's field of view are counted; all others are
    treated as invisible, exactly as in the PPO agent's observation.

    Phase -> lane mapping (derived from connections.con.xml):
        Phase 0 -- N/S left-turns
            in : n_to_center_3, s_to_center_3
            out: center_to_e_3, center_to_w_3
        Phase 1 -- N/S straight
            in : n_to_center_1, n_to_center_2, s_to_center_1, s_to_center_2
            out: center_to_s_1, center_to_s_2, center_to_n_1, center_to_n_2
        Phase 2 -- E/W left-turns
            in : e_to_center_3, w_to_center_3
            out: center_to_s_3, center_to_n_3
        Phase 3 -- E/W straight
            in : e_to_center_1, e_to_center_2, w_to_center_1, w_to_center_2
            out: center_to_w_1, center_to_w_2, center_to_e_1, center_to_e_2
    """
    # -- Parameters --------------------------------------------------------------
    CAMERA_RANGE = 100        # metres
    MIN_GREEN    = 10         # seconds
    MAX_GREEN    = 60         # seconds (safety cap)
    YELLOW_TIME  = 3          # seconds
    DELTA_TIME   = 5          # seconds per decision step

    GREEN_STATES = {
        0: "grrGgrrrgrrGgrrr",
        1: "gGGrgrrrgGGrgrrr",
        2: "grrrgrrGgrrrgrrG",
        3: "grrrgGGrgrrrgGGr",
    }

    # Incoming and outgoing lanes for each valid phase (from connections.con.xml)
    PHASE_LANES = {
        0: {
            "in":  ["n_to_center_3", "s_to_center_3"],
            "out": ["center_to_e_3", "center_to_w_3"],
        },
        1: {
            "in":  ["n_to_center_1", "n_to_center_2", "s_to_center_1", "s_to_center_2"],
            "out": ["center_to_s_1", "center_to_s_2", "center_to_n_1", "center_to_n_2"],
        },
        2: {
            "in":  ["e_to_center_3", "w_to_center_3"],
            "out": ["center_to_s_3", "center_to_n_3"],
        },
        3: {
            "in":  ["e_to_center_1", "e_to_center_2", "w_to_center_1", "w_to_center_2"],
            "out": ["center_to_w_1", "center_to_w_2", "center_to_e_1", "center_to_e_2"],
        },
    }

    # -- SUMO setup ---------------------------------------------------------------
    base_env = create_sumo_env(
        net_file=r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\network.net.xml",
        route_file=route_file,
        use_gui=use_gui,
        sumo_seed=seed
    )
    base_env.reset()
    sumo    = base_env.unwrapped.sumo
    ts_id   = list(base_env.unwrapped.traffic_signals.keys())[0]
    ts_obj  = base_env.unwrapped.traffic_signals[ts_id]

    # Cache lane lengths to avoid repeated TraCI calls
    _lane_len_cache = {}

    def _lane_length(lane_id):
        if lane_id not in _lane_len_cache:
            _lane_len_cache[lane_id] = sumo.lane.getLength(lane_id)
        return _lane_len_cache[lane_id]

    # -- Camera-filtered vehicle counts -------------------------------------------
    def _count_incoming(lane_id):
        """Vehicles within CAMERA_RANGE of the stop line on an incoming lane.

        Stop line is at the far end of the lane (position = lane_length).
        A vehicle at position p is (lane_length - p) metres from the stop line.
        Visible if: lane_length - p <= CAMERA_RANGE  ->  p >= lane_length - CAMERA_RANGE
        """
        threshold = max(0.0, _lane_length(lane_id) - CAMERA_RANGE)
        return sum(
            1 for v in sumo.lane.getLastStepVehicleIDs(lane_id)
            if sumo.vehicle.getLanePosition(v) >= threshold
        )

    def _count_outgoing(lane_id):
        """Vehicles within CAMERA_RANGE of the intersection entry on an outgoing lane.

        Outgoing lanes start at the intersection (position 0).
        A vehicle at position p is p metres from the entry point.
        Visible if: p <= CAMERA_RANGE
        """
        return sum(
            1 for v in sumo.lane.getLastStepVehicleIDs(lane_id)
            if sumo.vehicle.getLanePosition(v) <= CAMERA_RANGE
        )

    # -- Pressure computation -----------------------------------------------------
    def _compute_pressures():
        """P_j = Σ(V_in − V_out) for each phase, camera-range constrained."""
        result = {}
        for phase, lanes in PHASE_LANES.items():
            v_in  = sum(_count_incoming(l) for l in lanes["in"])
            v_out = sum(_count_outgoing(l) for l in lanes["out"])
            result[phase] = v_in - v_out
        return result

    # -- Yellow-transition helpers -------------------------------------------------
    def _compute_yellow_state(from_state, to_state):
        yellow = []
        for f, t in zip(from_state, to_state):
            if f.lower() in ('g', 'y') and t == 'r':
                yellow.append('y')
            else:
                yellow.append(f)
        return ''.join(yellow)

    def _apply_yellow_then_green(from_phase, to_phase):
        nonlocal sim_time
        yellow_state = _compute_yellow_state(GREEN_STATES[from_phase], GREEN_STATES[to_phase])
        sumo.trafficlight.setRedYellowGreenState(ts_id, yellow_state)
        for _ in range(YELLOW_TIME):
            sumo.simulationStep()
            sim_time += 1
        sumo.trafficlight.setRedYellowGreenState(ts_id, GREEN_STATES[to_phase])

    # -- State --------------------------------------------------------------------
    current_phase = 0
    elapsed_green = 0
    sim_time      = 0
    sim_end       = base_env.unwrapped.sim_max_time

    sumo.trafficlight.setRedYellowGreenState(ts_id, GREEN_STATES[current_phase])

    queues         = []
    waiting_times  = []
    max_wait_times = []
    episode_peak   = 0.0
    total_switches = 0
    total_arrived  = 0

    # -- Main simulation loop ------------------------------------------------------
    while sim_time < sim_end:
        # Step 1 -- Re-assert current green state so SUMO's internal TL timer
        #          cannot override our manually set state between decisions.
        sumo.trafficlight.setRedYellowGreenState(ts_id, GREEN_STATES[current_phase])

        # Step 2 -- Safety check: only consider switching after MIN_GREEN has elapsed.
        if elapsed_green >= MIN_GREEN:
            # Step 3 -- Sensor read + pressure computation (camera-constrained).
            pressures = _compute_pressures()

            # Step 4 -- Select action: phase with maximum pressure score.
            best_phase = max(pressures, key=pressures.get)

            # Step 5 -- Execute transition.
            force_switch = elapsed_green >= MAX_GREEN

            # Only switch on genuine pressure advantage -- ties keep the current phase.
            # Without this guard, dict ordering makes max() always return phase 0 on
            # equal pressures, starving phases 1-3 to just MIN_GREEN each.
            want_switch = (
                best_phase != current_phase
                and pressures[best_phase] > pressures[current_phase]
            )

            if force_switch or want_switch:
                if not want_switch:
                    # Force-switch: cycle to next phase in round-robin order so all
                    # phases are guaranteed service when pressures are equal.
                    best_phase = (current_phase + 1) % 4
                _apply_yellow_then_green(current_phase, best_phase)
                current_phase = best_phase
                elapsed_green = 0
                total_switches += 1

        # Advance simulation by one DELTA_TIME window
        for _ in range(DELTA_TIME):
            if sim_time >= sim_end:
                break
            sumo.simulationStep()
            sim_time += 1
        elapsed_green += DELTA_TIME

        # -- Metrics collection ------------------------------------------------
        try:
            total_queued  = sum(ts_obj.get_lanes_queue())
            total_wait    = sum(ts_obj.get_accumulated_waiting_time_per_lane())
            all_waits     = [sumo.vehicle.getWaitingTime(v) for v in sumo.vehicle.getIDList()]
            step_max_wait = max(all_waits) if all_waits else 0.0
        except Exception:
            total_queued  = 0
            total_wait    = 0
            step_max_wait = 0.0

        try:
            total_arrived += sumo.simulation.getArrivedNumber()
        except Exception:
            pass

        episode_peak = max(episode_peak, step_max_wait)
        queues.append(total_queued)
        waiting_times.append(total_wait)
        max_wait_times.append(step_max_wait)

    base_env.close()
    return pd.DataFrame({
        "step":                      range(0, len(queues) * DELTA_TIME, DELTA_TIME),
        "system_total_stopped":      queues,
        "system_total_waiting_time": waiting_times,
        "system_max_wait_time":      max_wait_times,
        "episode_peak_max_wait":     [episode_peak]   * len(queues),
        "total_switches":            [total_switches]  * len(queues),
        "total_arrived":             [total_arrived]   * len(queues),
    })


def evaluate_model_on_seed(model_name, model_type, route_file, seed, cycle_time=None, model_path=None, use_gui=False):
    if model_type == "mp":
        return evaluate_mp_on_seed(route_file, seed, use_gui)

    base_env = create_sumo_env(
        net_file=r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\network.net.xml",
        route_file=route_file,
        use_gui=use_gui,
        sumo_seed=seed
    )

    env = SwitchOrKeepWrapper(base_env)
    
    time_in_phase = 0
    current_phase = 0
    step_count = 0
    
    queues = []
    waiting_times = []
    max_wait_times = []
    episode_peak_max_wait = 0.0
    total_switches = 0
    total_arrived = 0

    if model_type == "ppo" and model_path and os.path.exists(model_path):
        vec_env = DummyVecEnv([lambda: env])
        # Auto-detect normalization stats path matching the model filename or falling back
        stats_path = "vec_normalize_stats.pkl"
        model_dir = os.path.dirname(model_path)
        base_name = os.path.basename(model_path).replace(".zip", "")
        agent_id = None
        if base_name.startswith("ppo_model_"):
            agent_id = base_name.replace("ppo_model_", "")
        elif base_name == "ppo_production_final":
            agent_id = "production_final"
        
        if agent_id:
            candidate_stats = os.path.join(model_dir, f"vec_normalize_{agent_id}.pkl")
            if os.path.exists(candidate_stats):
                stats_path = candidate_stats
            else:
                candidate_stats = f"vec_normalize_{agent_id}.pkl"
                if os.path.exists(candidate_stats):
                    stats_path = candidate_stats
        else:
            if os.path.exists("models/vec_normalize_production_final.pkl"):
                stats_path = "models/vec_normalize_production_final.pkl"
            
        if os.path.exists(stats_path):
            vec_env = VecNormalize.load(stats_path, vec_env)
            vec_env.training = False
            vec_env.norm_reward = False
        
        model = MaskablePPO.load(model_path, env=vec_env, device="cuda")
        obs = vec_env.reset()
        done_flag = False
    elif model_type == "ppo":
        print(f"Warning: Model path {model_path} not found.")
        return None
    else:
        obs, info = env.reset()
        done_flag = False
        
    while not done_flag:
        if model_type == "fixed":
            action = 0  # Keep current phase
            if time_in_phase >= cycle_time:
                action = 1  # Switch to next phase
                time_in_phase = 0
            obs, reward, done, truncated, info = env.step(action)
            done_flag = done or truncated
            if action == 1:
                total_switches += 1
        elif model_type == "ppo":
            masks = env.action_masks()
            action, _ = model.predict(obs, deterministic=True, action_masks=[masks])
            obs, reward, dones, infos = vec_env.step(action)
            done_flag = dones[0]
            scalar_action = action[0] if isinstance(action, (list, np.ndarray)) else action
            if scalar_action == 1:
                total_switches += 1
        # Unified info extraction -- handles both raw env and VecEnv (list of dicts)
        if model_type == "fixed":
            current_max_wait = info.get("max_vehicle_wait_time", 0.0)
        elif model_type == "ppo":
            raw_info = infos[0] if isinstance(infos, (list, tuple)) else infos
            current_max_wait = raw_info.get("max_vehicle_wait_time", 0.0)
        else:
            current_max_wait = 0.0
        episode_peak_max_wait = max(episode_peak_max_wait, current_max_wait)
        max_wait_times.append(current_max_wait)

        time_in_phase += 5
        step_count += 5
        
        # Manually track queue + accumulated wait metrics
        ts = base_env.unwrapped.traffic_signals["center"]
        total_queued = sum(ts.get_lanes_queue())
        total_wait = sum(ts.get_accumulated_waiting_time_per_lane())
        
        # Track arrived vehicles
        total_arrived += base_env.unwrapped.sumo.simulation.getArrivedNumber()
        
        queues.append(total_queued)
        waiting_times.append(total_wait)

    env.close()
    
    # Return as a pandas DataFrame
    return pd.DataFrame({
        "step": range(0, len(queues) * 5, 5),
        "system_total_stopped": queues,
        "system_total_waiting_time": waiting_times,
        "system_max_wait_time": max_wait_times,
        "episode_peak_max_wait": [episode_peak_max_wait] * len(queues),
        "total_switches": [total_switches] * len(queues),
        "total_arrived": [total_arrived] * len(queues),
    })

def evaluate_scenario(map_name, route_file, seeds, models_to_test, eval_dir, use_gui=False):
    print(f"\n=========================================", flush=True)
    print(f"BENCHMARKING SCENARIO: {map_name}", flush=True)
    print(f"=========================================", flush=True)
    
    # Dict to hold averaged results: model_name -> DataFrame
    avg_results = {}
    
    # List to hold numerical records for the CSV table
    csv_records = []
    
    print(f"--- Firing up parallel evaluation tasks using {os.cpu_count()} CPU Cores ---", flush=True)
    
    tasks = []
    for m in models_to_test:
        for seed in seeds:
            tasks.append((m["name"], m["type"], route_file, seed, m.get("cycle_time"), m.get("path"), use_gui))
            
    model_results = {m["name"]: [] for m in models_to_test}
    
    # Force single-process execution if GUI is enabled to avoid window conflicts
    workers = 1 if use_gui else 10
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_task = {executor.submit(run_evaluation_task, t): t for t in tasks}
        
        for future in as_completed(future_to_task):
            try:
                model_name, seed, df = future.result()
                if df is not None:
                    df["seed"] = seed
                    df["model"] = model_name
                    model_results[model_name].append(df)
                    
                    total_wait = df["system_total_waiting_time"].sum()
                    peak_max_wait = df["episode_peak_max_wait"].max()
                    total_switches = df["total_switches"].max()
                    total_arrived = df["total_arrived"].max()
                    avg_queue = df["system_total_stopped"].mean()
                    
                    csv_records.append({
                        "Model": model_name,
                        "Seed": seed,
                        "Total_Wait_Time": total_wait,
                        "Peak_Max_Wait_s": peak_max_wait,
                        "Total_Switches": total_switches,
                        "Total_Arrived": total_arrived,
                        "Avg_Queue_Len": avg_queue,
                    })
                    print(f"    [Finished] {model_name} (Seed {seed}) -> Wait: {total_wait:.0f}s | Peak Max: {peak_max_wait:.0f}s | Switches: {total_switches} | Arrived: {total_arrived} | Avg Queue: {avg_queue:.1f}", flush=True)
            except Exception as exc:
                print(f"    [Error] Task generated an exception: {exc}", flush=True)

    for model_name, dfs in model_results.items():
        if len(dfs) > 0:
            combined = pd.concat(dfs)
            avg_df = combined.groupby("step")[
                ["system_total_stopped", "system_total_waiting_time", "system_max_wait_time"]
            ].mean().reset_index()
            avg_results[model_name] = avg_df

    if not avg_results:
        return

    # ---------------------------------------------------------
    # 1. EXPORT NUMERICAL CSV TABLES
    # ---------------------------------------------------------
    results_df = pd.DataFrame(csv_records)
    # Calculate the average wait time for each model across all seeds
    avg_table = results_df.groupby("Model")[["Total_Wait_Time", "Peak_Max_Wait_s"]].mean().reset_index()
    avg_table = avg_table.sort_values("Total_Wait_Time")
    
    # Save raw seed-by-seed data
    results_df.to_csv(os.path.join(eval_dir, f"eval_{map_name.lower()}_raw_data.csv"), index=False)
    # Save the averaged summary table
    avg_table.to_csv(os.path.join(eval_dir, f"eval_{map_name.lower()}_summary.csv"), index=False)
    
    print(f"\n--- {map_name} FINAL RESULTS TABLE ---", flush=True)
    print(avg_table.to_string(index=False), flush=True)
    print("--------------------------------------\n", flush=True)

    # Plot Total Waiting Time Comparison (Summed over the whole episode, then averaged by seed)
    plt.figure(figsize=(10, 6))
    names = list(avg_results.keys())
    wait_times = [avg_results[name]["system_total_waiting_time"].sum() for name in names]
    
    plt.bar(names, wait_times, color=['red', 'orange', 'yellow', 'blue', 'green'])
    plt.title(f"[{map_name}] Cumulative Waiting Time (Averaged over {len(seeds)} Seeds)")
    plt.ylabel("Total Seconds Waited")
    plt.savefig(os.path.join(eval_dir, f"eval_{map_name.lower()}_waiting_time.png"))
    plt.close()

    # Plot Queue Length Over Time
    plt.figure(figsize=(12, 6))
    for name, df in avg_results.items():
        plt.plot(df["step"], df["system_total_stopped"], label=name)
        
    plt.title(f"[{map_name}] System Stopped Vehicles Over Time")
    plt.xlabel("Simulation Step (s)")
    plt.ylabel("Average Stopped Vehicles")
    plt.legend()
    plt.savefig(os.path.join(eval_dir, f"eval_{map_name.lower()}_queue.png"))
    plt.close()

    # NEW: Plot Peak Single-Vehicle Wait Time Over Time
    plt.figure(figsize=(12, 6))
    for name, df in avg_results.items():
        plt.plot(df["step"], df["system_max_wait_time"], label=name)
    plt.axhline(y=90, color='red', linestyle='--', linewidth=1, label='90s Starvation Threshold')
    plt.axhline(y=30, color='orange', linestyle='--', linewidth=1, label='30s Penalty Start')
    plt.title(f"[{map_name}] Peak Single-Vehicle Wait Time Over Episode")
    plt.xlabel("Simulation Step (s)")
    plt.ylabel("Max Consecutive Wait (s)")
    plt.legend()
    plt.savefig(os.path.join(eval_dir, f"eval_{map_name.lower()}_max_wait.png"))
    plt.close()
    
    print(f"[{map_name}] Graphs saved successfully.", flush=True)

def main():
    parser = argparse.ArgumentParser(description="Evaluate Traffic Models")
    parser.add_argument("--gui", action="store_true", help="Run evaluation with SUMO GUI")
    parser.add_argument("--seeds", type=int, default=5, help="Number of seeds to run (set to 1 when using GUI for quicker tests)")
    args = parser.parse_args()

    # Create a unique timestamped folder in PPOagent/results/ (one level up from src/)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _ppo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    eval_dir = os.path.join(_ppo_root, "results", f"eval_{timestamp}")
    os.makedirs(eval_dir, exist_ok=True)
    
    # Save the seeds configuration for future reproducibility
    # If GUI is enabled, we usually just want a single seed to watch, unless user explicitly specifies
    if args.gui and args.seeds == 5:
        seeds = [42] # Default to 1 seed if GUI enabled
    else:
        all_seeds = [42, 123, 1337, 2026, 9999]
        seeds = all_seeds[:args.seeds]
    with open(os.path.join(eval_dir, "evaluation_config.txt"), "w") as f:
        f.write(f"Evaluation Run: {timestamp}\n")
        f.write(f"Seeds Used: {seeds}\n")
        
    print(f"=========================================")
    print(f"STARTING EVALUATION SUITE")
    print(f"Results will be saved to: {eval_dir}")
    print(f"=========================================\n", flush=True)

    maps = [
        {"name": "Low_Traffic", "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml"},
        {"name": "Medium_Traffic", "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_hard.rou.xml"},
        {"name": "High_Traffic", "route": r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_extreme.rou.xml"}
    ]
    
    import glob
    # Search BOTH models/ and checkpoints/ -- always take the most recently written file
    # so the evaluator uses the current run's 21-dim model, not an old 13-dim checkpoint.
    all_zips = (
        glob.glob(os.path.join("models", "ppo_model_*.zip")) +
        glob.glob(os.path.join("checkpoints", "ppo_model_*.zip"))
    )
    latest_model_path = None
    if all_zips:
        latest_model_path = max(all_zips, key=os.path.getmtime)
        print(f"Auto-detected latest PPO model for evaluation: {latest_model_path}")
    else:
        root_zips = glob.glob("ppo_*.zip")
        if root_zips:
            latest_model_path = max(root_zips, key=os.path.getmtime)
            print(f"Auto-detected root PPO model for evaluation: {latest_model_path}")
    
    if latest_model_path is None:
        print("WARNING: No PPO model found. PPO evaluation will be skipped.")
        latest_model_path = "ppo_production_final.zip"  # Will safely fail and skip

    models_to_test = [
        {"name": "Maskable_PPO", "type": "ppo", "path": latest_model_path},
        {"name": "Fixed_30s", "type": "fixed", "cycle_time": 30},
        {"name": "Fixed_45s", "type": "fixed", "cycle_time": 45},
        {"name": "Fixed_60s", "type": "fixed", "cycle_time": 60},
        {"name": "Max_Pressure", "type": "mp"}
    ]
    
    # Backup the evaluated PPO model files to the result folder
    for m in models_to_test:
        if m["type"] == "ppo" and m.get("path") and os.path.exists(m["path"]):
            shutil.copy(m["path"], os.path.join(eval_dir, os.path.basename(m["path"])))
            # Also backup the normalization stats
            stats_path = "vec_normalize_stats.pkl"
            model_dir = os.path.dirname(m["path"])
            base_name = os.path.basename(m["path"]).replace(".zip", "")
            agent_id = None
            if base_name.startswith("ppo_model_"):
                agent_id = base_name.replace("ppo_model_", "")
            elif base_name == "ppo_production_final":
                agent_id = "production_final"
            
            if agent_id:
                candidate_stats = os.path.join(model_dir, f"vec_normalize_{agent_id}.pkl")
                if os.path.exists(candidate_stats):
                    stats_path = candidate_stats
                else:
                    candidate_stats = f"vec_normalize_{agent_id}.pkl"
                    if os.path.exists(candidate_stats):
                        stats_path = candidate_stats
            else:
                if os.path.exists("models/vec_normalize_production_final.pkl"):
                    stats_path = "models/vec_normalize_production_final.pkl"
            
            if os.path.exists(stats_path):
                shutil.copy(stats_path, os.path.join(eval_dir, "vec_normalize_stats.pkl"))
    
    for map_scenario in maps:
        evaluate_scenario(map_scenario["name"], map_scenario["route"], seeds, models_to_test, eval_dir, args.gui)
        
    print("\nAll Scenarios Complete! Evaluation benchmark finished.")

if __name__ == "__main__":
    main()
