from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from flowgrid.maps.map_builder import DEFAULT_FLOWS, write_routes_file
from flowgrid.rl.policy_config import PhaseBandParams, RandomTrafficTrainingParams

PHASE_LABELS = ("easy", "medium", "hard")

DEFAULT_RANDOM_TRAFFIC = RandomTrafficTrainingParams()


@dataclass(frozen=True)
class TrafficEpisodeSpec:
    phase: str
    flow_scale: float
    bus_probability: float
    emergency_probability: float
    busy_snapshot: bool
    route_path: str


def default_phase_counts() -> dict[str, int]:
    return {label: 0 for label in PHASE_LABELS}


def rebalance_phase_weights(
    phase_counts: dict[str, int],
    *,
    rebalance: bool = True,
) -> dict[str, float]:
    if not rebalance:
        return {label: 1.0 for label in PHASE_LABELS}
    total = sum(int(phase_counts.get(label, 0)) for label in PHASE_LABELS) + len(PHASE_LABELS)
    target = total / len(PHASE_LABELS)
    return {
        label: max(0.05, target - int(phase_counts.get(label, 0)))
        for label in PHASE_LABELS
    }


def scale_flows(base_flows: dict[str, float], scale: float) -> dict[str, float]:
    factor = max(0.0, float(scale))
    return {key: max(0.0, float(value) * factor) for key, value in base_flows.items()}


def _uniform(rng: random.Random, low: float, high: float) -> float:
    if high <= low:
        return float(low)
    return float(rng.uniform(low, high))


def _sample_band_params(
    band: PhaseBandParams,
    rng: random.Random,
) -> tuple[float, float, float, float]:
    flow_scale = _uniform(rng, band.flow_min, band.flow_max)
    busy_min = float(band.busy_min)
    busy_max = float(band.busy_max)
    busy_p = _uniform(rng, busy_min, busy_max) if busy_max > 0.0 else 0.0
    bus_prob = _uniform(rng, band.bus_min, band.bus_max) if band.bus_max > 0.0 else 0.0
    emg_prob = _uniform(rng, band.emg_min, band.emg_max) if band.emg_max > 0.0 else 0.0
    return flow_scale, busy_p, bus_prob, emg_prob


def _pick_phase(
    phase_counts: dict[str, int],
    rng: random.Random,
    config: RandomTrafficTrainingParams,
) -> str:
    weights = rebalance_phase_weights(phase_counts, rebalance=config.rebalance_phases)
    labels = list(PHASE_LABELS)
    w = [weights[label] for label in labels]
    return rng.choices(labels, weights=w, k=1)[0]


def write_episode_routes(
    path: Path,
    base_flows: dict[str, float],
    lanes_per_approach: int,
    *,
    flow_scale: float,
    bus_probability: float,
    emergency_probability: float,
) -> str:
    flows = {**DEFAULT_FLOWS, **base_flows}
    write_routes_file(
        path,
        scale_flows(flows, flow_scale),
        lanes_per_approach,
        bus_probability=bus_probability,
        emergency_probability=emergency_probability,
    )
    return str(path.resolve())


def ensure_hard_warmup_routes(
    cache_dir: str | Path,
    map_key: str,
    base_flows: dict[str, float] | None,
    lanes_per_approach: int,
    config: RandomTrafficTrainingParams | None = None,
) -> str:
    cfg = config or DEFAULT_RANDOM_TRAFFIC
    band = cfg.phase_bands["hard"]
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"train_routes_{map_key}_warmup_hard.rou.xml"
    write_episode_routes(
        path,
        base_flows or {},
        lanes_per_approach,
        flow_scale=band.flow_max,
        bus_probability=band.bus_max,
        emergency_probability=band.emg_max,
    )
    return str(path.resolve())


def sample_traffic_episode(
    *,
    cache_dir: str | Path,
    map_key: str,
    base_flows: dict[str, float],
    lanes_per_approach: int,
    phase_counts: dict[str, int],
    episode_index: int,
    rng: random.Random,
    busy_fraction_override: float | None = None,
    config: RandomTrafficTrainingParams | None = None,
) -> TrafficEpisodeSpec:
    cfg = config or DEFAULT_RANDOM_TRAFFIC
    phase = _pick_phase(phase_counts, rng, cfg)
    band = cfg.phase_bands[phase]
    flow_scale, busy_p, bus_prob, emg_prob = _sample_band_params(band, rng)

    if busy_fraction_override is not None:
        busy_p = max(0.0, min(1.0, float(busy_fraction_override)))

    busy_snapshot = busy_p > 0.0 and rng.random() < busy_p

    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    route_path = root / f"train_routes_{map_key}_ep{episode_index}.rou.xml"
    route_file = write_episode_routes(
        route_path,
        base_flows,
        lanes_per_approach,
        flow_scale=flow_scale,
        bus_probability=bus_prob,
        emergency_probability=emg_prob,
    )

    return TrafficEpisodeSpec(
        phase=phase,
        flow_scale=flow_scale,
        bus_probability=bus_prob,
        emergency_probability=emg_prob,
        busy_snapshot=busy_snapshot,
        route_path=route_file,
    )
