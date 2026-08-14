"""CLI training entry point."""

import os

import sys



ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, ROOT)

os.chdir(ROOT)



from flowgrid.paths import PROJECT_ROOT

import matplotlib.pyplot as plt

from flowgrid.core.sumo_env import SumoEnv

from flowgrid.rl.dqn_agent import DQNAgent

from flowgrid.rl.policy_checkpoint_io import save_agent_checkpoint





def train(sumocfg: str | None = None, episodes: int = 50, policy_path: str | None = None):

    sumocfg = sumocfg or str(PROJECT_ROOT / "data" / "defaults" / "flowgrid.sumocfg")

    policy_path = policy_path or str(PROJECT_ROOT / "data" / "defaults" / "dqn_policy.pth")

    env = SumoEnv(sumocfg_file=sumocfg, gui=False)

    agent = DQNAgent(env.observation_space.shape[0], env.action_space.n)

    rewards = []

    for ep in range(episodes):

        state, _ = env.reset()

        done = truncated = False

        reward_sum = 0

        steps = 0

        while not (done or truncated):

            action = agent.select_action(state)

            state, reward, done, truncated, _ = env.step(action)

            agent.memory.push(state, action, reward, state, done)

            agent.optimize_model()

            reward_sum += reward

            steps += 1

            if steps > 1000:

                truncated = True

        agent.update_epsilon()

        agent.episodes_done += 1

        agent.steps_done += steps

        if ep % 10 == 0:

            agent.update_target_network()

        rewards.append(reward_sum)

        print(f"Episode {ep + 1}/{episodes} reward={reward_sum:.1f}")

    env.close()

    os.makedirs(os.path.dirname(policy_path) or ".", exist_ok=True)

    save_agent_checkpoint(agent, policy_path, episode=agent.episodes_done)

    print("Saved", policy_path)





if __name__ == "__main__":

    train()

