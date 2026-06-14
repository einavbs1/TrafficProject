from __future__ import annotations

import os

import traci

from flowgrid.core.sumo_env import SumoEnv

BUSY_SNAPSHOT_TLS_TAG = "tls8bal"


def busy_snapshot_path(snap_dir: str, map_key: str, seed: int) -> str:
    return os.path.join(
        snap_dir,
        f"train_busy_{map_key}_seed{seed}_{BUSY_SNAPSHOT_TLS_TAG}.xml",
    )


def ensure_busy_training_snapshot(
    env: SumoEnv,
    snapshot_path: str,
    *,
    seed: int,
    warmup_sim_seconds: float,
    route_files: str | None = None,
    force_rebuild: bool = False,
) -> str:
    path = str(snapshot_path)
    if force_rebuild and os.path.isfile(path):
        os.remove(path)
    if os.path.isfile(path):
        return path

    reset_opts = {"route_files": route_files} if route_files else None
    env.reset(seed=seed, options=reset_opts)
    target = float(warmup_sim_seconds)
    while env.sim_time < target:
        traci.simulationStep()
        env.sim_time = float(traci.simulation.getTime())

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    traci.simulation.saveState(path)
    return path


def reset_from_busy_snapshot(
    env: SumoEnv,
    snapshot_path: str,
    *,
    seed: int,
    warmup_sim_seconds: float,
    route_files: str | None = None,
):
    path = str(snapshot_path)
    try:
        return env.reset(options={"load_busy_snapshot": path})
    except (traci.exceptions.FatalTraCIError, traci.exceptions.TraCIException):
        try:
            env.close()
        except Exception:
            pass
        if os.path.isfile(path):
            os.remove(path)
        ensure_busy_training_snapshot(
            env,
            path,
            seed=seed,
            warmup_sim_seconds=warmup_sim_seconds,
            route_files=route_files,
        )
        return env.reset(options={"load_busy_snapshot": path})