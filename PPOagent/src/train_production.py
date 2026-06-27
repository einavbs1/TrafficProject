import os
import glob
import shutil
from datetime import datetime
import torch
import torch.nn as nn
import argparse
from stable_baselines3.common.callbacks import CheckpointCallback

# --- OS-LEVEL THREADING CONSTRAINTS ---
# Prevent catastrophic context-switching when using SubprocVecEnv
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
torch.set_num_threads(1)

from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize
from stable_baselines3.common.utils import get_linear_fn
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from sumo_rl_env import create_sumo_env, SwitchOrKeepWrapper, MultiRouteWrapper

def make_env(net_file, route_files, use_gui=False):
    def _init():
        # Start with the first route file; MultiRouteWrapper will randomize it on reset
        initial_route = route_files[0] if isinstance(route_files, list) else route_files
        base_env = create_sumo_env(net_file, initial_route, use_gui)
        
        # Wrap in MultiRouteWrapper for curriculum map randomization
        if isinstance(route_files, list):
            base_env = MultiRouteWrapper(base_env, route_files)
            
        env = SwitchOrKeepWrapper(base_env)
        return ActionMasker(env, lambda e: e.action_masks())
    return _init

def main():
    parser = argparse.ArgumentParser(description="Train PPO Agent")
    parser.add_argument("--timesteps", type=int, default=2000000, help="Total timesteps to train")
    parser.add_argument("--save-freq", type=int, default=100000, help="Timestep interval to save checkpoints")
    parser.add_argument("--resume", type=str, default=None, help="Path to a .zip model to resume training from")
    parser.add_argument("--newAgent", action="store_true", help="Start a brand new agent and do not resume")
    args = parser.parse_args()

    resume_path = None
    agent_id = None

    if args.newAgent:
        agent_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"--- NEW AGENT MODE --- Generating new ID: {agent_id}")
    else:
        # Resume mode (default)
        if args.resume:
            resume_path = args.resume
        else:
            # Auto-find latest PPO zip in the models folder
            zips = glob.glob(os.path.join("models", "ppo_*.zip")) + glob.glob("ppo_*.zip")
            if zips:
                resume_path = max(zips, key=os.path.getmtime)
                print(f"--- AUTO-RESUME MODE --- Found latest model: {resume_path}")
            else:
                agent_id = datetime.now().strftime("%Y%m%d_%H%M%S")
                print(f"--- AUTO-RESUME MODE --- No models found. Starting fresh as: {agent_id}")
        
        if resume_path:
            # Extract agent ID from filename so we continue saving to the same ID
            basename = os.path.basename(resume_path).replace(".zip", "")
            if basename.startswith("ppo_model_"):
                agent_id = basename.replace("ppo_model_", "")
            elif basename == "ppo_production_final":
                agent_id = "production_final"
            else:
                agent_id = basename
            print(f"Resuming Agent ID: {agent_id}")

    net_file = r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\network.net.xml"
    route_files = [
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml",
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_hard.rou.xml",
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_extreme.rou.xml"
    ]
    
    # 1. PARALLEL EXECUTION ARCHITECTURE WITH CURRICULUM TRAINING
    num_cpu = 10
    env_fns = [make_env(net_file, route_files, use_gui=False) for _ in range(num_cpu)]
    
    print(f"Initializing SubprocVecEnv with {num_cpu} parallel SUMO instances...")
    vec_env = SubprocVecEnv(env_fns)
    
    # 2. STATE NORMALIZATION
    if resume_path and os.path.exists(os.path.join("models", f"vec_normalize_{agent_id}.pkl")):
        print(f"Loading existing normalization statistics from models/vec_normalize_{agent_id}.pkl...")
        vec_env = VecNormalize.load(os.path.join("models", f"vec_normalize_{agent_id}.pkl"), vec_env)
        vec_env.training = True
        vec_env.norm_reward = False
    elif resume_path and os.path.exists(f"vec_normalize_{agent_id}.pkl"):
        print(f"Loading existing normalization statistics from vec_normalize_{agent_id}.pkl...")
        vec_env = VecNormalize.load(f"vec_normalize_{agent_id}.pkl", vec_env)
        vec_env.training = True
        vec_env.norm_reward = False
    elif resume_path and os.path.exists("vec_normalize_stats.pkl"):
        print("Loading fallback normalization statistics from vec_normalize_stats.pkl...")
        vec_env = VecNormalize.load("vec_normalize_stats.pkl", vec_env)
        vec_env.training = True
        vec_env.norm_reward = False
    else:
        print("Initializing new VecNormalize environment...")
        vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=False, clip_obs=10.)

    if resume_path and os.path.exists(resume_path):
        # CREATE A SAFETY BACKUP BEFORE LOADING
        backup_name = resume_path.replace(".zip", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
        shutil.copy(resume_path, backup_name)
        print(f"--- SAFETY BACKUP CREATED --- Original model protected at: {backup_name}")
        
        print(f"Resuming training from existing model: {resume_path}")
        model = MaskablePPO.load(resume_path, env=vec_env, device="cuda")
        # Fine-tuning LR: use a low constant rate (3e-5) instead of restarting
        # the aggressive 3e-4 schedule. Restarting from 3e-4 causes catastrophic
        # forgetting — the near-zero end-of-training LR is violently overwritten.
        model.learning_rate = 3e-5
        model.ent_coef = 0.0   # No entropy injection: agent is already converged
        model.policy.optimizer.param_groups[0]["lr"] = 3e-5
        model.policy.optimizer.param_groups[0]["eps"] = 1e-5

    else:
        print("Building brand new MaskablePPO Model with GPU Acceleration...")
        # 3. ALGORITHMIC FIDELITY (The 37 Implementation Details)
        policy_kwargs = dict(
            activation_fn=nn.Tanh,
            # Use plain dict (not list-of-dict) — required by SB3 >= v1.8.0
            net_arch=dict(pi=[128, 128], vf=[128, 128]),
            ortho_init=True
        )

        lr_schedule = get_linear_fn(start=3e-4, end=0.0, end_fraction=1.0)

        model = MaskablePPO(
            "MlpPolicy",
            vec_env,
            learning_rate=lr_schedule,
            n_steps=2048,
            batch_size=256,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,       # Entropy bonus: prevents premature convergence in binary action space
            target_kl=0.03,
            policy_kwargs=policy_kwargs,
            device="cuda",
            verbose=1,
            tensorboard_log="./tensorboard/production_run/"
        )
        
        # Explicitly set Adam Epsilon after initialization to prevent violent spikes
        model.policy.optimizer.param_groups[0]["eps"] = 1e-5

    # 4. AUTO-SAVE CHECKPOINTS
    # SB3's save_freq is per environment, so we divide by num_cpu
    checkpoint_callback = CheckpointCallback(
        save_freq=max(args.save_freq // num_cpu, 1),
        save_path="./checkpoints/",
        name_prefix=f"ppo_model_{agent_id}"
    )

    print(f"Beginning Big Time Production Training for {args.timesteps} timesteps...")
    print(f"Will save a checkpoint every {args.save_freq} timesteps.")
    
    model.learn(total_timesteps=args.timesteps, callback=checkpoint_callback, progress_bar=True)
    
    os.makedirs("models", exist_ok=True)
    final_model_path = os.path.join("models", f"ppo_model_{agent_id}.zip")
    final_stats_path = os.path.join("models", f"vec_normalize_{agent_id}.pkl")
    model.save(final_model_path)
    vec_env.save(final_stats_path)
    print(f"Training complete! Model saved to {final_model_path}")

    vec_env.close()

if __name__ == "__main__":
    main()
