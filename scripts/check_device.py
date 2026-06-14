import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from flowgrid.rl.device import directml_available, resolve_training_device_or_fallback
from flowgrid.rl.dqn_agent import DQN, DQNAgent
from flowgrid.rl.policy_config import PolicyConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify FlowGrid DQN training device resolution")
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda", "directml"],
    )
    args = parser.parse_args()

    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"DirectML available: {directml_available()}")

    device, label = resolve_training_device_or_fallback(args.device)
    print(f"Resolved preference={args.device!r} -> {label} ({device})")

    cfg = PolicyConfig.load()
    in_dim = 26
    out_dim = 2
    agent = DQNAgent(in_dim, out_dim, policy_config=cfg, device_preference=args.device)
    print(f"DQNAgent device: {agent.device_label} ({agent.device})")

    batch = min(8, cfg.training.batch_size)
    states = torch.randn(batch, in_dim, device=agent.device)
    with torch.no_grad():
        q = agent.policy_net(states)
    print(f"Forward pass OK: output shape {tuple(q.shape)} on {agent.device}")

    agent.memory.push(
        [0.0] * in_dim,
        0,
        1.0,
        [0.0] * in_dim,
        False,
        [True, True],
        [True, True],
    )
    for i in range(batch):
        agent.memory.push(
            [float(i)] * in_dim,
            i % 2,
            float(i),
            [float(i + 1)] * in_dim,
            False,
            [True, True],
            [True, True],
        )
    agent.optimize_model()
    print("optimize_model() OK")


if __name__ == "__main__":
    main()
