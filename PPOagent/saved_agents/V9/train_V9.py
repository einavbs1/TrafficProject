"""
V9 Training Script -- run from THIS folder.

    cd PPOagent/saved_agents/V9
    python train_V9.py --timesteps 6000000

V9 changes over V8 (camera stays 150m -- real-world sensor limit):
    - Observation 21 -> 29 dims: wait signals log-scaled + 8 new total-wait dims
    - Fixes observation saturation in heavy congestion (queues > 150m)
    - Reward and hard mask unchanged from V8

Outputs:
    ./models/       -- final model + vec_normalize + safety backups
    ./checkpoints/  -- checkpoint every 100k steps (model + vecnormalize stats)
"""
import os, re, sys, glob, shutil
from datetime import datetime
import torch
import torch.nn as nn
import argparse
from stable_baselines3.common.callbacks import CheckpointCallback

os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
torch.set_num_threads(2)  # 2 spare cores (10 SUMO + 2 PyTorch = 12 logical)

_HERE      = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(_HERE, "models")
CKPT_DIR   = os.path.join(_HERE, "checkpoints")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(CKPT_DIR,   exist_ok=True)

sys.path.insert(0, _HERE)
from sumo_rl_env_V9 import create_sumo_env, SwitchOrKeepWrapper, MultiRouteWrapper

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
                        help="Path to .zip to resume (default: auto-find in ./models/)")
    parser.add_argument("--fresh", action="store_true",
                        help="Force fresh training; ignore existing models and checkpoints")
    args = parser.parse_args()

    resume_path = None
    agent_id    = None

    if args.resume:
        resume_path = args.resume
    elif not args.fresh:
        zips = [z for z in glob.glob(os.path.join(MODELS_DIR, "ppo_model_*.zip"))
                if "_backup_" not in os.path.basename(z)]
        if zips:
            resume_path = max(zips, key=os.path.getmtime)

    # -- Crash recovery: no final model in ./models/ but checkpoints exist ----
    # Continue the interrupted run from the latest checkpoint (model zip keeps
    # optimizer state, LR schedule and step counter; matching vecnormalize pkl
    # keeps the observation stats). Nothing is lost on a crash or kill.
    crash_ckpt, crash_stats = None, None
    if resume_path is None and not args.fresh:
        ckpts = glob.glob(os.path.join(CKPT_DIR, "ppo_model_*_steps.zip"))
        if ckpts:
            def _ckpt_steps(p):
                m = re.search(r"_(\d+)_steps\.zip$", os.path.basename(p))
                return int(m.group(1)) if m else -1
            crash_ckpt = max(ckpts, key=_ckpt_steps)
            steps = _ckpt_steps(crash_ckpt)
            base  = os.path.basename(crash_ckpt)[:-len(f"_{steps}_steps.zip")]
            crash_stats = os.path.join(CKPT_DIR, f"{base}_vecnormalize_{steps}_steps.pkl")
            if not os.path.exists(crash_stats):
                sys.exit(f"FATAL: found checkpoint {crash_ckpt}\n"
                         f"but its VecNormalize stats are missing: {crash_stats}\n"
                         f"Cannot recover safely. Use --fresh to start over.")
            agent_id = base.replace("ppo_model_", "")

    if resume_path:
        basename = os.path.basename(resume_path).replace(".zip", "")
        agent_id = basename.replace("ppo_model_", "") if basename.startswith("ppo_model_") else basename
        print(f"Resuming: {resume_path}  (agent_id={agent_id})")
    elif crash_ckpt:
        print(f"CRASH RECOVERY: continuing from {crash_ckpt}  (agent_id={agent_id})")
    else:
        agent_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"Fresh V9 agent: {agent_id}")

    net_file = r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\network.net.xml"
    route_files = [
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml",
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_hard.rou.xml",
        r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes_extreme.rou.xml",
    ]
    num_cpu = 10
    vec_env = SubprocVecEnv([make_env(net_file, route_files) for _ in range(num_cpu)])

    stats_path = os.path.join(MODELS_DIR, f"vec_normalize_{agent_id}.pkl")
    if resume_path:
        # HARD GUARD: never resume without the matching VecNormalize stats.
        # Fresh stats shift the observation distribution under a trained policy
        # and collapse it (V7 resume incident, 2026-07-02).
        if not os.path.exists(stats_path):
            vec_env.close()
            sys.exit(f"FATAL: resuming {resume_path}\n"
                     f"but VecNormalize stats are missing: {stats_path}\n"
                     f"Restore the matching .pkl (checkpoints save one per 100k steps), "
                     f"or move the model out of ./models/ to train fresh.")
        vec_env = VecNormalize.load(stats_path, vec_env)
        vec_env.training = True
        vec_env.norm_reward = False
    elif crash_ckpt:
        vec_env = VecNormalize.load(crash_stats, vec_env)
        vec_env.training = True
        vec_env.norm_reward = False
    else:
        vec_env = VecNormalize(vec_env, norm_obs=True, norm_reward=False, clip_obs=10.)

    if resume_path and os.path.exists(resume_path):
        backup = os.path.join(MODELS_DIR,
            os.path.basename(resume_path).replace(".zip",
            f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"))
        shutil.copy(resume_path, backup)
        print(f"Backup saved: {backup}")
        model = MaskablePPO.load(resume_path, env=vec_env, device="cuda")
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
    elif crash_ckpt:
        # Continue the interrupted run exactly where it stopped: keep the saved
        # LR schedule and step counter (no lr override, no counter reset).
        model = MaskablePPO.load(crash_ckpt, env=vec_env, device="cuda")
        print(f"Continuing from {model.num_timesteps:,} steps with original LR schedule")
    else:
        print("Building fresh V9 agent...")
        model = MaskablePPO(
            "MlpPolicy", vec_env,
            learning_rate=get_linear_fn(start=3e-4, end=0.0, end_fraction=1.0),
            n_steps=512, batch_size=512, n_epochs=10,
            gamma=0.99, gae_lambda=0.95, clip_range=0.2,
            ent_coef=0.02, target_kl=0.03,
            policy_kwargs=dict(
                activation_fn=nn.Tanh,
                net_arch=dict(pi=[128, 128], vf=[128, 128]),
                ortho_init=True),
            device="cuda", verbose=1,
            tensorboard_log=os.path.join(_HERE, "tensorboard"))
        model.policy.optimizer.param_groups[0]["eps"] = 1e-5

    # Resume runs get their own checkpoint prefix so they never overwrite
    # the original run's checkpoints (that erased V7's 100k-1.2M checkpoints).
    ckpt_prefix = f"ppo_model_{agent_id}"
    if resume_path:
        ckpt_prefix += "_resume" + datetime.now().strftime("%m%d_%H%M")
    checkpoint_callback = CheckpointCallback(
        save_freq=max(args.save_freq // num_cpu, 1),
        save_path=CKPT_DIR,
        name_prefix=ckpt_prefix,
        save_vecnormalize=True)

    print(f"Training V9 for {args.timesteps} steps")
    print(f"Checkpoints -> {CKPT_DIR}")
    remaining = args.timesteps
    reset_counters = True
    if crash_ckpt:
        remaining = max(args.timesteps - model.num_timesteps, 0)
        reset_counters = False
        print(f"Remaining to target {args.timesteps:,}: {remaining:,} steps")
    if remaining > 0:
        model.learn(total_timesteps=remaining, callback=checkpoint_callback,
                    progress_bar=True, reset_num_timesteps=reset_counters)

    out_model = os.path.join(MODELS_DIR, f"ppo_model_{agent_id}.zip")
    out_stats = os.path.join(MODELS_DIR, f"vec_normalize_{agent_id}.pkl")
    model.save(out_model)
    vec_env.save(out_stats)
    print(f"Saved -> {out_model}")
    vec_env.close()


if __name__ == "__main__":
    main()
