"""
V4 Initial Training Script -- LOW-TRAFFIC WEIGHTED route variant.

    cd PPOagent/saved_agents/V4_initial
    python train_V4_initial_low50weighted.py --timesteps 3000000

Difference from train_V4_initial.py:
    route_files duplicates routes.rou.xml (low traffic) so it's picked 50% of
    the time instead of the default equal-thirds (33% low / 33% med / 33% high).
    Intended for resuming an already-converged V4 model to give it more
    exposure to sparse-traffic episodes without abandoning medium/high.

Outputs:
    ./models/       -- final model + vec_normalize + safety backups
    ./checkpoints/  -- checkpoint every 100k steps
"""
import os, sys, glob, shutil
from datetime import datetime
import torch
import torch.nn as nn
import argparse
from stable_baselines3.common.callbacks import CheckpointCallback

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
torch.set_num_threads(1)

# -- Paths relative to this script --------------------------------------------
_HERE      = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(_HERE, "models")
CKPT_DIR   = os.path.join(_HERE, "checkpoints")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(CKPT_DIR,   exist_ok=True)

# -- Import env from same folder -----------------------------------------------
sys.path.insert(0, _HERE)
from sumo_rl_env_V4 import create_sumo_env, SwitchOrKeepWrapper, MultiRouteWrapper

from stable_baselines3.common.vec_env import SubprocVecEnv, VecNormalize
from stable_baselines3.common.utils import get_linear_fn
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker

def make_env(net_file, route_files, use_gui=False):
    def _init():
        initial_route = route_files[0] if isinstance(route_files, list) else route_files
        base_env = create_sumo_env(net_file, initial_route, use_gui)
        if isinstance(route_files, list):
            base_env = MultiRouteWrapper(base_env, route_files)
        env = SwitchOrKeepWrapper(base_env)
        return ActionMasker(env, lambda e: e.action_masks())
    return _init

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=6000000)
    parser.add_argument("--save-freq", type=int, default=100000)
    parser.add_argument("--resume", type=str, default=None,
                        help="Path to a .zip to resume from (default: auto-find in ./models/)")
    args = parser.parse_args()

    # -- Resolve model to load / start fresh ----------------------------------
    resume_path = None
    agent_id    = None

    if args.resume:
        resume_path = args.resume
    else:
        zips = [z for z in glob.glob(os.path.join(MODELS_DIR, "ppo_model_*.zip"))
                if "_backup_" not in os.path.basename(z)]
        if zips:
            resume_path = max(zips, key=os.path.getmtime)

    if resume_path:
        basename = os.path.basename(resume_path).replace(".zip", "")
        agent_id = basename.replace("ppo_model_", "") if basename.startswith("ppo_model_") else basename
        print(f"Resuming: {resume_path}  (agent_id={agent_id})")
    else:
        agent_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"Fresh agent: {agent_id}")

    # -- Environment -----------------------------------------------------------
    net_file = r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\network.net.xml"
    route_files = [
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml",
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml",      # 50% low
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_hard.rou.xml",
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_extreme.rou.xml",
    ]
    num_cpu = 10
    vec_env = SubprocVecEnv([make_env(net_file, route_files) for _ in range(num_cpu)])

    stats_path = os.path.join(MODELS_DIR, f"vec_normalize_{agent_id}.pkl")
    if resume_path and os.path.exists(stats_path):
        vec_env = VecNormalize.load(stats_path, vec_env)
        vec_env.training = True
        vec_env.norm_reward = False
    else:
        vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=False, clip_obs=10.)

    # -- Model -----------------------------------------------------------------
    if resume_path and os.path.exists(resume_path):
        backup = os.path.join(MODELS_DIR,
            os.path.basename(resume_path).replace(".zip", f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"))
        shutil.copy(resume_path, backup)
        print(f"Backup saved: {backup}")

        model = MaskablePPO.load(resume_path, env=vec_env, device="cuda")
        # Keep original V4 params -- ent_coef=0.02 same as fresh training.
        # lr=1e-5 (very small constant) because the 3e-4->0 schedule already
        # hit 0 at 6M steps; resetting too high destabilised V4 Resume.
        model.learning_rate = 1e-5
        model.ent_coef = 0.02
        model.policy.optimizer.param_groups[0]["lr"] = 1e-5
        model.policy.optimizer.param_groups[0]["eps"] = 1e-5
        from sb3_contrib.common.maskable.buffers import MaskableRolloutBuffer
        model.n_steps = 512
        model.rollout_buffer = MaskableRolloutBuffer(
            model.n_steps, model.observation_space, model.action_space,
            device=model.device, gae_lambda=model.gae_lambda,
            gamma=model.gamma, n_envs=model.n_envs)
    else:
        # V4 initial exact hyperparameters
        model = MaskablePPO(
            "MlpPolicy", vec_env,
            learning_rate=get_linear_fn(start=3e-4, end=0.0, end_fraction=1.0),
            n_steps=512, batch_size=256, n_epochs=10,
            gamma=0.99, gae_lambda=0.95, clip_range=0.2,
            ent_coef=0.02, target_kl=0.03,
            policy_kwargs=dict(
                activation_fn=torch.nn.Tanh,
                net_arch=dict(pi=[128, 128], vf=[128, 128]),
                ortho_init=True),
            device="cuda", verbose=1,
            tensorboard_log=os.path.join(_HERE, "tensorboard"))
        model.policy.optimizer.param_groups[0]["eps"] = 1e-5

    checkpoint_callback = CheckpointCallback(
        save_freq=max(args.save_freq // num_cpu, 1),
        save_path=CKPT_DIR,
        name_prefix=f"ppo_model_{agent_id}")

    print(f"Training {args.timesteps} steps  |  checkpoints -> {CKPT_DIR}")
    model.learn(total_timesteps=args.timesteps, callback=checkpoint_callback, progress_bar=True)

    out_model = os.path.join(MODELS_DIR, f"ppo_model_{agent_id}.zip")
    out_stats = os.path.join(MODELS_DIR, f"vec_normalize_{agent_id}.pkl")
    model.save(out_model)
    vec_env.save(out_stats)
    print(f"Saved -> {out_model}")
    vec_env.close()

if __name__ == "__main__":
    main()
