import os
_MAPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SharedData", "maps", "flowgrid")
import pickle
import numpy as np
from imitation.algorithms import bc
from imitation.data.types import Transitions
from sumo_rl_env import create_sumo_env

def train_behavioral_cloning():
    with open("expert_data.pkl", "rb") as f:
        expert_data = pickle.load(f)

    obs = np.array([step["obs"] for step in expert_data])
    acts = np.array([step["acts"] for step in expert_data])
    infos = np.array([{} for _ in expert_data])
    next_obs = np.roll(obs, shift=-1, axis=0)
    next_obs[-1] = obs[-1]
    dones = np.zeros(len(obs), dtype=bool)
    dones[-1] = True

    transitions = Transitions(
        obs=obs,
        acts=acts,
        infos=infos,
        next_obs=next_obs,
        dones=dones
    )

    env = create_sumo_env(
        net_file=os.path.join(_MAPS_DIR, "network.net.xml"),
        route_file=os.path.join(_MAPS_DIR, "routes.rou.xml")
    )

    bc_trainer = bc.BC(
        observation_space=env.observation_space,
        action_space=env.action_space,
        demonstrations=transitions,
        rng=np.random.default_rng(0),
    )

    bc_trainer.train(n_epochs=5)
    bc_trainer.policy.save("bc_policy.zip")

if __name__ == "__main__":
    train_behavioral_cloning()
