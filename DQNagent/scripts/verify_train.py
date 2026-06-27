"""Quick check that Plan 2 map + training loop run (2 episodes, prints summary)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.core.sumo_env import SumoEnv
from flowgrid.maps.map_env import sumo_env_extras
from flowgrid.maps.map_registry import list_maps_for_gui
from flowgrid.rl.dqn_agent import DQNAgent
from flowgrid.rl.policy_config import PolicyConfig


def main():
    maps = list_maps_for_gui()
    from flowgrid.maps.map_registry import DEFAULT_MAP_ID

    m = next((x for x in maps if x["id"] == DEFAULT_MAP_ID), maps[0])
    extras = sumo_env_extras(m)
    phase_ring = extras.pop("phase_ring", None)
    topology = extras.pop("topology", None)

    print(f"Map: {m['display_name']} ({m['id']})")
    print(f"Phasing: {m.get('phasing_scheme')}")
    print(f"Phase ring: {[p.id for p in phase_ring]}")

    env = SumoEnv(
        m["sumocfg"],
        gui=False,
        quit_on_end=True,
        live_updates=False,
        step_length=PolicyConfig.load().training.step_length,
        topology=topology,
        phase_ring=phase_ring,
        **extras,
    )
    agent = DQNAgent(env.observation_space.shape[0], env.action_space.n)

    for ep in range(1, 3):
        state, info = env.reset(seed=42 + ep)
        mask = info["action_mask"]
        steps = 0
        reward_sum = 0.0
        teleports = 0
        while steps < 1000:
            action = agent.select_action(state, mask)
            state, reward, done, trunc, info = env.step(action)
            mask = info["action_mask"]
            reward_sum += reward
            steps += 1
            if done or trunc:
                break
        print(
            f"Episode {ep}: steps={steps} sim_time={env.sim_time:.0f}s "
            f"phase={env.controller.current_phase_id} reward={reward_sum:.1f} "
            f"hold/advance ok"
        )

    env.close()
    print("OK — training environment is working.")


if __name__ == "__main__":
    main()
