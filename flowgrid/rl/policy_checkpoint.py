from __future__ import annotations

from pathlib import Path

import torch

from flowgrid.core.intersection_graph import IntersectionTopology


def expected_dims() -> tuple[int, int]:
    topo = IntersectionTopology.standard_four_way_four_lane()
    n_mov = len(topo.movements)
    n_arms = len(topo.arms)
    input_dim = n_mov + n_arms + n_arms + 1 + 1 + n_arms
    return input_dim, 2


def read_checkpoint_dims(policy_path: str | Path) -> tuple[int, int] | None:
    path = Path(policy_path)
    if not path.is_file():
        return None
    try:
        from flowgrid.rl.policy_checkpoint_io import _unwrap_state_dict, torch_load_checkpoint

        loaded = torch_load_checkpoint(path, map_location="cpu")
        if isinstance(loaded, dict):
            in_dim = loaded.get("input_dim")
            out_dim = loaded.get("output_dim")
            if in_dim is not None and out_dim is not None:
                return int(in_dim), int(out_dim)
        state, _, _ = _unwrap_state_dict(loaded)
        w_in = state.get("net.0.weight")
        w_out = state.get("net.4.weight")
        if w_in is None or w_out is None:
            return None
        return int(w_in.shape[1]), int(w_out.shape[0])
    except Exception:
        return None


def is_compatible(policy_path: str | Path, input_dim: int | None = None, output_dim: int | None = None) -> bool:
    if input_dim is None or output_dim is None:
        input_dim, output_dim = expected_dims()
    dims = read_checkpoint_dims(policy_path)
    return dims == (input_dim, output_dim)


def quarantine_incompatible(policy_path: str | Path, input_dim: int | None = None, output_dim: int | None = None) -> bool:
    path = Path(policy_path)
    if not path.is_file():
        return False
    if input_dim is None or output_dim is None:
        input_dim, output_dim = expected_dims()
    dims = read_checkpoint_dims(path)
    if dims is None:
        return False
    if dims == (input_dim, output_dim):
        return False
    backup = path.with_suffix(path.suffix + ".old")
    n = 0
    while backup.exists():
        n += 1
        backup = path.with_suffix(path.suffix + f".old{n}")
    path.replace(backup)
    return True
