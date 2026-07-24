"""Verify new-format checkpoints load for Compare (weights + eval epsilon)."""

from __future__ import annotations



import os

import sys

import tempfile

from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:

    sys.path.insert(0, str(ROOT))



from flowgrid.core.intersection_graph import IntersectionTopology

from flowgrid.eval.evaluate import _try_load_policy

from flowgrid.rl.dqn_agent import DQNAgent

from flowgrid.rl.policy_checkpoint_io import load_agent_checkpoint, save_agent_checkpoint

from flowgrid.rl.policy_config import PolicyConfig





def main() -> None:

    topo = IntersectionTopology.standard_four_way()

    n_mov = len(topo.movements)

    n_arms = len(topo.arms)

    in_dim = n_mov + n_arms + n_arms + 1 + 1 + n_arms

    path = os.path.join(tempfile.gettempdir(), "flowgrid_verify_ckpt.pth")



    agent = DQNAgent(in_dim, 2)

    agent.epsilon = 0.42

    save_agent_checkpoint(agent, path, episode=99)

    agent2 = DQNAgent(in_dim, 2)

    ok, err = _try_load_policy(agent2, path)

    if not ok:

        print(f"FAIL: eval load: {err}")

        sys.exit(1)

    if agent2.epsilon != 0.0:

        print(f"FAIL: epsilon should be 0 for eval, got {agent2.epsilon}")

        sys.exit(1)



    agent3 = DQNAgent(in_dim, 2)

    agent3.epsilon = 0.037

    agent3.episodes_done = 512

    agent3.steps_done = 48000

    agent3.epsilon_decay = 0.993

    save_agent_checkpoint(agent3, path, episode=agent3.episodes_done)

    agent4 = DQNAgent(in_dim, 2)

    cfg = PolicyConfig.load()

    result = load_agent_checkpoint(agent4, path, fine_tune=cfg.fine_tune)

    if not result.loaded:

        print("FAIL: resume load returned loaded=False")

        sys.exit(1)

    if abs(agent4.epsilon - 0.037) > 1e-6:

        print(f"FAIL: resume epsilon expected 0.037, got {agent4.epsilon}")

        sys.exit(1)

    if agent4.episodes_done != 512:

        print(f"FAIL: episodes_done expected 512, got {agent4.episodes_done}")

        sys.exit(1)

    if agent4.steps_done != 48000:

        print(f"FAIL: steps_done expected 48000, got {agent4.steps_done}")

        sys.exit(1)

    if abs(agent4.epsilon_decay - 0.993) > 1e-6:

        print(f"FAIL: epsilon_decay expected 0.993, got {agent4.epsilon_decay}")

        sys.exit(1)



    os.remove(path)

    print("OK — Compare loader and resume checkpoint round-trip.")





if __name__ == "__main__":

    main()

