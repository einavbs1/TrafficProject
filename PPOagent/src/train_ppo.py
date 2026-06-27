import argparse
import torch
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.policies import ActorCriticPolicy
from sumo_rl_env import create_sumo_env, ActionMaskerWrapper

def mask_fn(env):
    return env.action_masks()

def train_online_ppo():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Run with SUMO GUI")
    args = parser.parse_args()

    base_env = create_sumo_env(
        net_file=r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\network.net.xml",
        route_file=r"C:\Users\Einavs_PC\Documents\TrafficProject\SharedData\maps\flowgrid\routes.rou.xml",
        use_gui=args.gui
    )
    env = ActionMaskerWrapper(base_env)

    policy_kwargs = dict(net_arch=dict(pi=[32, 32], vf=[32, 32]))
    model = MaskablePPO("MlpPolicy", env, verbose=1, policy_kwargs=policy_kwargs)
    
    try:
        bc_policy = ActorCriticPolicy.load("bc_policy.zip")
        # MaskablePPO policy has a slightly different architecture, we might not be able to direct load
        # Let's try loading it anyway
        model.policy.load_state_dict(bc_policy.state_dict(), strict=False)
    except Exception as e:
        print("Could not load BC weights into MaskablePPO, starting fresh or re-train BC:", e)

    model.learn(total_timesteps=50000)
    model.save("ppo_sumo_finetuned")

if __name__ == "__main__":
    train_online_ppo()
