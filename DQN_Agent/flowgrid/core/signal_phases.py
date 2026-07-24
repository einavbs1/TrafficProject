"""Compatibility layer for GUI / legacy imports."""
from flowgrid.core.actuated_controller import ActuatedController
from flowgrid.core.phasing_schemes import PhaseCandidate
from flowgrid.core.intersection_graph import IntersectionTopology
from flowgrid.core.tls_builder import build_tls_state

TOPOLOGY = IntersectionTopology.standard_four_way_four_lane()

LANES = {
    "N": ["n_to_center_0", "n_to_center_1", "n_to_center_2", "n_to_center_3"],
    "S": ["s_to_center_0", "s_to_center_1", "s_to_center_2", "s_to_center_3"],
    "E": ["e_to_center_0", "e_to_center_1", "e_to_center_2", "e_to_center_3"],
    "W": ["w_to_center_0", "w_to_center_1", "w_to_center_2", "w_to_center_3"],
}

MOVEMENTS = [
    ("N", "right", "n_to_center_0"),
    ("N", "straight", "n_to_center_1"),
    ("N", "straight", "n_to_center_2"),
    ("N", "left", "n_to_center_3"),
    ("S", "right", "s_to_center_0"),
    ("S", "straight", "s_to_center_1"),
    ("S", "straight", "s_to_center_2"),
    ("S", "left", "s_to_center_3"),
    ("E", "right", "e_to_center_0"),
    ("E", "straight", "e_to_center_1"),
    ("E", "straight", "e_to_center_2"),
    ("E", "left", "e_to_center_3"),
    ("W", "right", "w_to_center_0"),
    ("W", "straight", "w_to_center_1"),
    ("W", "straight", "w_to_center_2"),
    ("W", "left", "w_to_center_3"),
]

ARM_TO_MOVEMENTS = {
    "N": ("N_TH", "N_LT", "N_RT"),
    "S": ("S_TH", "S_LT", "S_RT"),
    "E": ("E_TH", "E_LT", "E_RT"),
    "W": ("W_TH", "W_LT", "W_RT"),
}


def approach_signal(
    state_str: str,
    arm: str,
    movement: str,
    topology: IntersectionTopology | None = None,
) -> str:
    topo = topology or TOPOLOGY
    if movement == "right":
        mid = f"{arm}_RT"
    elif movement == "straight":
        mid = f"{arm}_TH"
    else:
        mid = f"{arm}_LT"
    mov = topo.movements[mid]
    chars = [state_str[i] for i in mov.links if i < len(state_str)]
    if not chars:
        return "red"
    if any(c.upper() == "G" or c == "g" or c == "O" for c in chars):
        return "green"
    if any(c.upper() == "Y" for c in chars):
        return "yellow"
    return "red"


def movement_signal(
    state_str: str,
    lane_id: str,
    topology: IntersectionTopology | None = None,
) -> str:
    topo = topology or TOPOLOGY
    for arm in topo.arms:
        for kind, label in (
            (f"{arm}_RT", "right"),
            (f"{arm}_TH", "straight"),
            (f"{arm}_LT", "left"),
        ):
            mov = topo.movements.get(kind)
            if mov is None:
                continue
            if lane_id in mov.sensor_lanes:
                return approach_signal(state_str, arm, label, topo)
    return "red"


def phase_name(phase_id: str) -> str:
    return phase_id.replace("_", " ")
