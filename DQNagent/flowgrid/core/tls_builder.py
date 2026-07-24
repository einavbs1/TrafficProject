"""Build SUMO traffic-light state strings from active movement sets."""
from __future__ import annotations

from flowgrid.core.intersection_graph import IntersectionTopology, MovementType

SIXTEEN_LANE_NUM_LINKS = 16

SIXTEEN_LANE_RIGHT_INDICES = (0, 4, 8, 12)

SIXTEEN_LANE_MOVEMENT_INDICES: dict[str, tuple[int, ...]] = {
    "N_RT": (0,),
    "N_TH": (1, 2),
    "N_LT": (3,),
    "E_RT": (4,),
    "E_TH": (5, 6),
    "E_LT": (7,),
    "S_RT": (8,),
    "S_TH": (9, 10),
    "S_LT": (11,),
    "W_RT": (12,),
    "W_TH": (13, 14),
    "W_LT": (15,),
}


def _blank_sixteen_lane_tls() -> list[str]:
    return ["r"] * SIXTEEN_LANE_NUM_LINKS


def _apply_always_green_rights(chars: list[str]) -> None:
    for link_idx in SIXTEEN_LANE_RIGHT_INDICES:
        chars[link_idx] = "g"


def _apply_through_or_left(chars: list[str], movement_id: str) -> None:
    for link_idx in SIXTEEN_LANE_MOVEMENT_INDICES.get(movement_id, ()):
        if movement_id.endswith("_TH") or movement_id.endswith("_LT"):
            chars[link_idx] = "G"


def build_sixteen_lane_state(active_movements: set[str], topology: IntersectionTopology) -> str:
    chars = _blank_sixteen_lane_tls()
    _apply_always_green_rights(chars)
    for movement_id in active_movements:
        if movement_id not in topology.movements:
            continue
        if movement_id.endswith("_RT"):
            continue
        _apply_through_or_left(chars, movement_id)
    return "".join(chars)


def build_tls_state(
    topology: IntersectionTopology,
    active_movements: set[str],
    *,
    separate_right_always: bool = False,
) -> str:
    if topology.num_links == SIXTEEN_LANE_NUM_LINKS:
        return build_sixteen_lane_state(set(active_movements), topology)

    chars = ["r"] * topology.num_links
    active = set(active_movements)
    if separate_right_always:
        for mid, mov in topology.movements.items():
            if mov.kind == MovementType.RIGHT:
                active.add(mid)
    else:
        active = topology.expand_free_rights(active)

    for mid in active:
        mov = topology.movements[mid]
        for link_idx in mov.links:
            if link_idx >= len(chars):
                continue
            if mov.kind == MovementType.RIGHT:
                chars[link_idx] = "g"
            elif mov.kind in (MovementType.LEFT, MovementType.THROUGH):
                chars[link_idx] = "G"
            else:
                chars[link_idx] = "g"

    return "".join(chars)


def build_all_yellow(topology: IntersectionTopology, previous: str) -> str:
    return "".join("y" if c.upper() in ("G", "Y") or c == "g" else "r" for c in previous)


def build_all_red(topology: IntersectionTopology) -> str:
    return "r" * topology.num_links


def baseline_left_duration(through_seconds: float, left_to_through_ratio: float) -> int:
    return int(float(through_seconds) * float(left_to_through_ratio))


def build_baseline_tls_phases(
    topology: IntersectionTopology,
    *,
    through_seconds: float,
    left_to_through_ratio: float,
    yellow_seconds: float = 3.0,
) -> list[tuple[float, str]]:
    if topology.num_links != SIXTEEN_LANE_NUM_LINKS:
        return []
    from flowgrid.core.phasing_schemes import build_baseline_balanced_ring

    left_seconds = baseline_left_duration(through_seconds, left_to_through_ratio)
    phases: list[tuple[float, str]] = []
    for candidate in build_baseline_balanced_ring(separate_right_turn=True):
        duration = float(left_seconds) if candidate.baseline_cap == "left" else float(through_seconds)
        phases.append((duration, build_sixteen_lane_state(set(candidate.movements), topology)))
        phases.append((float(yellow_seconds), build_all_yellow(topology, phases[-1][1])))
    return phases


DIRECTIONAL_ARM_PHASE_IDS = ("N_ALL", "S_ALL", "E_ALL", "W_ALL")

DIRECTIONAL_ARM_PREFIXES = ("N", "S", "E", "W")


def build_directional_arm_state(arm: str, topology: IntersectionTopology) -> str:
    return build_sixteen_lane_state({f"{arm}_TH", f"{arm}_LT"}, topology)


def verify_directional_tls_states(topology: IntersectionTopology) -> dict[str, str]:
    states = {f"{arm}_ALL": build_directional_arm_state(arm, topology) for arm in DIRECTIONAL_ARM_PREFIXES}
    for phase_id, state in states.items():
        if len(state) != SIXTEEN_LANE_NUM_LINKS:
            raise ValueError(f"{phase_id} TLS length {len(state)} != {SIXTEEN_LANE_NUM_LINKS}")
        arm = phase_id[0]
        rt_idx = {"N": 0, "E": 4, "S": 8, "W": 12}[arm]
        if state[rt_idx] != "g":
            raise ValueError(f"{phase_id} right-turn link {rt_idx} expected g got {state[rt_idx]!r}")
        for idx in SIXTEEN_LANE_MOVEMENT_INDICES.get(f"{arm}_TH", ()):
            if state[idx] != "G":
                raise ValueError(f"{phase_id} thru link {idx} expected G got {state[idx]!r}")
        for idx in SIXTEEN_LANE_MOVEMENT_INDICES.get(f"{arm}_LT", ()):
            if state[idx] != "G":
                raise ValueError(f"{phase_id} left link {idx} expected G got {state[idx]!r}")
        for idx, ch in enumerate(state):
            if idx in SIXTEEN_LANE_RIGHT_INDICES:
                continue
            if idx in SIXTEEN_LANE_MOVEMENT_INDICES.get(f"{arm}_TH", ()):
                continue
            if idx in SIXTEEN_LANE_MOVEMENT_INDICES.get(f"{arm}_LT", ()):
                continue
            if ch != "r":
                raise ValueError(f"{phase_id} link {idx} expected r got {ch!r}")
    return states


def baseline_tls_phase_elements(
    topology: IntersectionTopology,
    *,
    through_seconds: float,
    left_to_through_ratio: float,
    yellow_seconds: float = 3.0,
) -> list[tuple[str, str]]:
    return [
        (str(int(round(duration))), state)
        for duration, state in build_baseline_tls_phases(
            topology,
            through_seconds=through_seconds,
            left_to_through_ratio=left_to_through_ratio,
            yellow_seconds=yellow_seconds,
        )
    ]
