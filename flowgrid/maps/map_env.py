"""Build SumoEnv kwargs from a map preset / GUI map dict."""
from __future__ import annotations

from flowgrid.core.intersection_graph import IntersectionTopology
from flowgrid.core.phasing_schemes import DEFAULT_SCHEME, build_phase_ring
from flowgrid.maps.map_registry import MapPreset


def topology_for_map(map_info: dict | MapPreset) -> IntersectionTopology:
    lanes = int(_field(map_info, "lanes_per_approach", 2))
    if lanes >= 4:
        return IntersectionTopology.standard_four_way_four_lane()
    if lanes >= 3:
        return IntersectionTopology.standard_four_way_three_lane()
    return IntersectionTopology.standard_four_way()


def controller_ring_for_map(map_info: dict | MapPreset) -> list:
    scheme = str(_field(map_info, "phasing_scheme", DEFAULT_SCHEME))
    separate = bool(_field(map_info, "separate_right_turn", True))
    return build_phase_ring(scheme, separate_right_turn=separate)


def _field(obj: dict | MapPreset, key: str, default):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def sumo_env_extras(map_info: dict | MapPreset | None) -> dict:
    """Topology + controller ring + timing fields for SumoEnv."""
    if map_info is None:
        return {}
    return {
        "topology": topology_for_map(map_info),
        "phase_ring": controller_ring_for_map(map_info),
        "separate_right_turn": bool(_field(map_info, "separate_right_turn", True)),
        "baseline_through_seconds": float(_field(map_info, "baseline_through_seconds", 60)),
        "baseline_left_to_through_ratio": float(
            _field(map_info, "baseline_left_to_through_ratio", 0.60)
        ),
    }
