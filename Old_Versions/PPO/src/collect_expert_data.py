import os
_MAPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SharedData", "maps", "flowgrid")
import pickle
from sumo_rl_env import create_sumo_env

def get_expert_action(ts):
    best_action = 0
    max_weight = -1
    queues = ts.get_lanes_queue()
    for i, phase in enumerate(ts.green_phases):
        state = phase.state
        weight = 0
        for j, char in enumerate(state):
            if char.lower() == 'g':
                if j < len(queues):
                    weight += queues[j]
        if weight > max_weight:
            max_weight = weight
            best_action = i
    return best_action

def collect_data():
    env = create_sumo_env(
        net_file=os.path.join(_MAPS_DIR, "network.net.xml"),
        route_file=os.path.join(_MAPS_DIR, "routes.rou.xml")
    )
    obs, info = env.reset()
    expert_data = []
    ts_id = list(env.traffic_signals.keys())[0]
    ts = env.traffic_signals[ts_id]
    
    done = False
    while not done:
        action = get_expert_action(ts)
        expert_data.append({"obs": obs, "acts": action})
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        
    with open("expert_data.pkl", "wb") as f:
        pickle.dump(expert_data, f)
    env.close()

if __name__ == "__main__":
    collect_data()
