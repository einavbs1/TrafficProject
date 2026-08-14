import os
_MAPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SharedData", "maps", "flowgrid")
import torch
from sb3_contrib import MaskablePPO
from stable_baselines3.common.policies import ActorCriticPolicy
from sumo_rl_env import create_sumo_env, ActionMaskerWrapper
import argparse

def train_curriculum():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Run with SUMO GUI")
    args = parser.parse_args()

    curriculum = [
        os.path.join(_MAPS_DIR, "routes_hard.rou.xml"),
        os.path.join(_MAPS_DIR, "routes_extreme.rou.xml")
    ]
    
    net_file = os.path.join(_MAPS_DIR, "network.net.xml")
    
    model = None
    
    for i, route_file in enumerate(curriculum):
        print(f"--- Starting Curriculum Phase {i+1} with {route_file} ---")
        base_env = create_sumo_env(net_file, route_file, use_gui=args.gui)
        env = ActionMaskerWrapper(base_env)
        
        if model is None:
            model = MaskablePPO.load("ppo_sumo_finetuned", env=env)
        else:
            model.set_env(env)
            
        model.learn(total_timesteps=50000)
        model.save(f"ppo_curriculum_level_{i+1}")
        env.close()

if __name__ == "__main__":
    train_curriculum()
