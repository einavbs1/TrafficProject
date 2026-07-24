"""Configurable signal phase rings (Israeli-style options)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass
class PhaseCandidate:
    id: str
    movements: frozenset[str]
    description: str
    baseline_cap: str = "through"  # through | left | full_arm


class PhasingScheme(str, Enum):
    """User-selectable timing plans (per map)."""

    PER_ARM_FULL = "per_arm_full"
    """Option 1: full green per arm (left + thru + right if not separate)."""
    OPPOSITE_THRU_RT_THEN_THRU = "opposite_thru_rt_then_thru"
    """Option 2: opposite thru+right, then opposite thru only, then opposite lefts."""
    OPPOSITE_THRU_THEN_THRU_RT = "opposite_thru_then_thru_rt"
    """Option 3: opposite thru only, then opposite thru+right, then opposite lefts."""


def _arm_phase(
    arm: str,
    *,
    left: bool,
    thru: bool,
    right: bool,
    separate_right: bool,
    baseline_cap: str,
) -> PhaseCandidate:
    moves: set[str] = set()
    if thru:
        moves.add(f"{arm}_TH")
    if left:
        moves.add(f"{arm}_LT")
    if right:
        moves.add(f"{arm}_RT")
    parts = []
    if left:
        parts.append("left")
    if thru:
        parts.append("thru")
    if right and not separate_right:
        parts.append("right")
    label = f"{arm}: " + " + ".join(parts) if parts else arm
    return PhaseCandidate(
        f"{arm}_ALL",
        frozenset(moves),
        label,
        baseline_cap=baseline_cap,
    )


def _opposite_phase(
    arm_a: str,
    arm_b: str,
    *,
    left: bool,
    thru: bool,
    right: bool,
    separate_right: bool,
    suffix: str,
    baseline_cap: str,
) -> PhaseCandidate:
    moves: set[str] = set()
    for arm in (arm_a, arm_b):
        if thru:
            moves.add(f"{arm}_TH")
        if left:
            moves.add(f"{arm}_LT")
        if right:
            moves.add(f"{arm}_RT")
    parts = []
    if thru:
        parts.append("thru")
    if right:
        parts.append("right")
    if left:
        parts.append("left")
    desc = f"{arm_a}+{arm_b} " + "+".join(parts)
    return PhaseCandidate(
        f"{arm_a}{arm_b}_{suffix}",
        frozenset(moves),
        desc,
        baseline_cap=baseline_cap,
    )


def build_baseline_balanced_ring(separate_right_turn: bool = True) -> list[PhaseCandidate]:
    return [
        _opposite_phase(
            "N",
            "S",
            left=True,
            thru=False,
            right=False,
            separate_right=separate_right_turn,
            suffix="LEFT",
            baseline_cap="left",
        ),
        _opposite_phase(
            "N",
            "S",
            left=False,
            thru=True,
            right=False,
            separate_right=separate_right_turn,
            suffix="THRU",
            baseline_cap="through",
        ),
        _opposite_phase(
            "E",
            "W",
            left=True,
            thru=False,
            right=False,
            separate_right=separate_right_turn,
            suffix="LEFT",
            baseline_cap="left",
        ),
        _opposite_phase(
            "E",
            "W",
            left=False,
            thru=True,
            right=False,
            separate_right=separate_right_turn,
            suffix="THRU",
            baseline_cap="through",
        ),
    ]


def build_phase_ring(scheme: str | PhasingScheme, separate_right_turn: bool = True) -> list[PhaseCandidate]:
    """Build the ordered phase ring for actuated / baseline control."""
    if isinstance(scheme, str):
        try:
            scheme = PhasingScheme(scheme)
        except ValueError:
            scheme = PhasingScheme.PER_ARM_FULL

    if scheme == PhasingScheme.PER_ARM_FULL:
        cap = "full_arm" if separate_right_turn else "full_arm"
        return [
            _arm_phase("N", left=True, thru=True, right=True, separate_right=separate_right_turn, baseline_cap=cap),
            _arm_phase("S", left=True, thru=True, right=True, separate_right=separate_right_turn, baseline_cap=cap),
            _arm_phase("E", left=True, thru=True, right=True, separate_right=separate_right_turn, baseline_cap=cap),
            _arm_phase("W", left=True, thru=True, right=True, separate_right=separate_right_turn, baseline_cap=cap),
        ]

    if scheme == PhasingScheme.OPPOSITE_THRU_RT_THEN_THRU:
        return [
            _opposite_phase(
                "N",
                "S",
                left=False,
                thru=True,
                right=True,
                separate_right=separate_right_turn,
                suffix="THRU_RT",
                baseline_cap="through",
            ),
            _opposite_phase(
                "E",
                "W",
                left=False,
                thru=True,
                right=True,
                separate_right=separate_right_turn,
                suffix="THRU_RT",
                baseline_cap="through",
            ),
            _opposite_phase(
                "N",
                "S",
                left=False,
                thru=True,
                right=False,
                separate_right=separate_right_turn,
                suffix="THRU",
                baseline_cap="through",
            ),
            _opposite_phase(
                "E",
                "W",
                left=False,
                thru=True,
                right=False,
                separate_right=separate_right_turn,
                suffix="THRU",
                baseline_cap="through",
            ),
            _opposite_phase(
                "N",
                "S",
                left=True,
                thru=False,
                right=False,
                separate_right=separate_right_turn,
                suffix="LEFT",
                baseline_cap="left",
            ),
            _opposite_phase(
                "E",
                "W",
                left=True,
                thru=False,
                right=False,
                separate_right=separate_right_turn,
                suffix="LEFT",
                baseline_cap="left",
            ),
        ]

    if scheme == PhasingScheme.OPPOSITE_THRU_THEN_THRU_RT:
        return [
            _opposite_phase(
                "N",
                "S",
                left=False,
                thru=True,
                right=False,
                separate_right=separate_right_turn,
                suffix="THRU",
                baseline_cap="through",
            ),
            _opposite_phase(
                "E",
                "W",
                left=False,
                thru=True,
                right=False,
                separate_right=separate_right_turn,
                suffix="THRU",
                baseline_cap="through",
            ),
            _opposite_phase(
                "N",
                "S",
                left=False,
                thru=True,
                right=True,
                separate_right=separate_right_turn,
                suffix="THRU_RT",
                baseline_cap="through",
            ),
            _opposite_phase(
                "E",
                "W",
                left=False,
                thru=True,
                right=True,
                separate_right=separate_right_turn,
                suffix="THRU_RT",
                baseline_cap="through",
            ),
            _opposite_phase(
                "N",
                "S",
                left=True,
                thru=False,
                right=False,
                separate_right=separate_right_turn,
                suffix="LEFT",
                baseline_cap="left",
            ),
            _opposite_phase(
                "E",
                "W",
                left=True,
                thru=False,
                right=False,
                separate_right=separate_right_turn,
                suffix="LEFT",
                baseline_cap="left",
            ),
        ]

    return build_phase_ring(PhasingScheme.PER_ARM_FULL, separate_right_turn)


SCHEME_LABELS: dict[str, str] = {
    PhasingScheme.PER_ARM_FULL.value: "1 — Full green per direction (N, S, E, W)",
    PhasingScheme.OPPOSITE_THRU_RT_THEN_THRU.value: "2 — Opposite thru+right, then opposite thru, then lefts",
    PhasingScheme.OPPOSITE_THRU_THEN_THRU_RT.value: "3 — Opposite thru, then opposite thru+right, then lefts",
}

DEFAULT_SCHEME = PhasingScheme.PER_ARM_FULL.value

DUAL_PEEL_PHASES = frozenset({"NS_LEFT", "NS_THRU", "EW_LEFT", "EW_THRU"})

_DUAL_PEEL_ARMS: dict[str, tuple[str, str]] = {
    "NS_LEFT": ("N", "S"),
    "NS_THRU": ("N", "S"),
    "EW_LEFT": ("E", "W"),
    "EW_THRU": ("E", "W"),
}

_DIRECTIONAL_RESUME: dict[tuple[str, str], str] = {
    ("NS_LEFT", "N_ALL"): "NS_THRU",
    ("NS_LEFT", "S_ALL"): "NS_THRU",
    ("NS_THRU", "N_ALL"): "EW_LEFT",
    ("NS_THRU", "S_ALL"): "EW_LEFT",
    ("EW_LEFT", "E_ALL"): "EW_THRU",
    ("EW_LEFT", "W_ALL"): "EW_THRU",
    ("EW_THRU", "E_ALL"): "NS_LEFT",
    ("EW_THRU", "W_ALL"): "NS_LEFT",
}


def build_directional_arm_phases(separate_right_turn: bool = True) -> list[PhaseCandidate]:
    cap = "full_arm"
    return [
        _arm_phase("N", left=True, thru=True, right=False, separate_right=separate_right_turn, baseline_cap=cap),
        _arm_phase("S", left=True, thru=True, right=False, separate_right=separate_right_turn, baseline_cap=cap),
        _arm_phase("E", left=True, thru=True, right=False, separate_right=separate_right_turn, baseline_cap=cap),
        _arm_phase("W", left=True, thru=True, right=False, separate_right=separate_right_turn, baseline_cap=cap),
    ]


def build_actuated_ring_with_directionals(base_ring: list[PhaseCandidate]) -> list[PhaseCandidate]:
    by_id = {phase.id: phase for phase in base_ring}
    merged = list(base_ring)
    for phase in build_directional_arm_phases(separate_right_turn=True):
        if phase.id not in by_id:
            merged.append(phase)
            by_id[phase.id] = phase
    return merged


def dual_phase_arms(phase_id: str) -> tuple[str, str] | None:
    return _DUAL_PEEL_ARMS.get(phase_id)


def directional_resume_id(source_dual_id: str, directional_id: str) -> str | None:
    return _DIRECTIONAL_RESUME.get((source_dual_id, directional_id))
