from __future__ import annotations

import logging
from itertools import combinations

from flowgrid.core.intersection_graph import IntersectionTopology
from flowgrid.core.phasing_schemes import (
    PhaseCandidate,
    PhasingScheme,
    build_baseline_balanced_ring,
    build_directional_arm_phases,
    build_phase_ring,
)

logger = logging.getLogger(__name__)

SIXTEEN_LANE_NUM_LINKS = 16

BASELINE_FALLBACK_PHASE_IDS = ("NS_LEFT", "NS_THRU", "EW_LEFT", "EW_THRU")

_OPPOSING_THROUGH_PROTECTED_SETS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"N_TH", "S_TH"}),
        frozenset({"E_TH", "W_TH"}),
    }
)

_EXPLICIT_HARD_FORBIDDEN_16: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"N_TH", "E_TH"}),
        frozenset({"N_TH", "W_TH"}),
        frozenset({"S_TH", "E_TH"}),
        frozenset({"S_TH", "W_TH"}),
        frozenset({"N_LT", "W_TH"}),
        frozenset({"S_LT", "E_TH"}),
        frozenset({"E_LT", "W_TH"}),
        frozenset({"N_LT", "S_TH"}),
        frozenset({"N_LT", "E_TH"}),
        frozenset({"N_TH", "S_LT"}),
        frozenset({"N_TH", "E_LT"}),
        frozenset({"S_LT", "N_TH"}),
        frozenset({"S_LT", "W_TH"}),
        frozenset({"S_TH", "W_LT"}),
        frozenset({"E_TH", "N_LT"}),
        frozenset({"E_TH", "S_LT"}),
        frozenset({"W_TH", "S_LT"}),
        frozenset({"W_TH", "N_LT"}),
        frozenset({"N_LT", "E_LT"}),
        frozenset({"N_LT", "W_LT"}),
        frozenset({"S_LT", "E_LT"}),
        frozenset({"S_LT", "W_LT"}),
        frozenset({"E_LT", "N_LT"}),
        frozenset({"E_LT", "S_LT"}),
        frozenset({"W_LT", "N_LT"}),
        frozenset({"W_LT", "S_LT"}),
    }
)


def protected_movements(movements: set[str] | frozenset[str]) -> frozenset[str]:
    return frozenset(mid for mid in movements if not mid.endswith("_RT"))


def build_forbidden_protected_pairs(topology: IntersectionTopology) -> frozenset[frozenset[str]]:
    pairs: set[frozenset[str]] = set()
    if topology.num_links == SIXTEEN_LANE_NUM_LINKS:
        pairs.update(_EXPLICIT_HARD_FORBIDDEN_16)
    movement_ids = [mid for mid in topology.movements if not mid.endswith("_RT")]
    for a, b in combinations(movement_ids, 2):
        if topology.movements_conflict(a, b):
            pairs.add(frozenset((a, b)))
    for allowed in _OPPOSING_THROUGH_PROTECTED_SETS:
        for a, b in combinations(allowed, 2):
            pairs.discard(frozenset((a, b)))
    for arm in topology.arms:
        thru_id = f"{arm}_TH"
        left_id = f"{arm}_LT"
        if thru_id in topology.movements and left_id in topology.movements:
            pairs.discard(frozenset((thru_id, left_id)))
    opposing_left = (
        frozenset({"N_LT", "S_LT"}),
        frozenset({"E_LT", "W_LT"}),
    )
    for allowed in opposing_left:
        for a, b in combinations(allowed, 2):
            pairs.discard(frozenset((a, b)))
    return frozenset(pairs)


def build_allowed_protected_sets(
    separate_right_turn: bool = True,
    ring: list[PhaseCandidate] | None = None,
) -> frozenset[frozenset[str]]:
    allowed: set[frozenset[str]] = set()
    rings: list[list[PhaseCandidate]] = [
        build_baseline_balanced_ring(separate_right_turn),
        build_directional_arm_phases(separate_right_turn),
        build_phase_ring(PhasingScheme.PER_ARM_FULL, separate_right_turn),
        build_phase_ring(PhasingScheme.OPPOSITE_THRU_RT_THEN_THRU, separate_right_turn),
        build_phase_ring(PhasingScheme.OPPOSITE_THRU_THEN_THRU_RT, separate_right_turn),
    ]
    if ring:
        rings.append(ring)
    for ring_entry in rings:
        for phase in ring_entry:
            allowed.add(protected_movements(phase.movements))
    allowed.add(frozenset())
    return frozenset(allowed)


class PhaseSafetyGate:
    def __init__(
        self,
        topology: IntersectionTopology,
        *,
        separate_right_turn: bool = True,
        ring: list[PhaseCandidate] | None = None,
    ) -> None:
        self.topology = topology
        self.enabled = topology.num_links == SIXTEEN_LANE_NUM_LINKS
        self._forbidden_pairs = (
            build_forbidden_protected_pairs(topology) if self.enabled else frozenset()
        )
        self._allowed_sets = (
            build_allowed_protected_sets(separate_right_turn, ring=ring)
            if self.enabled
            else frozenset()
        )

    @property
    def forbidden_protected_pairs(self) -> frozenset[frozenset[str]]:
        return self._forbidden_pairs

    @property
    def allowed_protected_sets(self) -> frozenset[frozenset[str]]:
        return self._allowed_sets

    def validate_protected_movements(self, movements: set[str] | frozenset[str]) -> tuple[bool, str]:
        if not self.enabled:
            return True, ""
        protected = protected_movements(movements)
        if protected not in self._allowed_sets:
            return False, f"whitelist_miss:{sorted(protected)}"
        for a, b in combinations(protected, 2):
            pair = frozenset((a, b))
            if pair in self._forbidden_pairs:
                return False, f"forbidden_pair:{sorted(pair)}"
        return True, ""

    def validate_phase(self, phase: PhaseCandidate) -> tuple[bool, str]:
        return self.validate_protected_movements(phase.movements)

    def safe_fallback_phase(self, ring: list[PhaseCandidate]) -> PhaseCandidate | None:
        for phase_id in BASELINE_FALLBACK_PHASE_IDS:
            for phase in ring:
                if phase.id == phase_id:
                    ok, _ = self.validate_phase(phase)
                    if ok:
                        return phase
        for phase in ring:
            ok, _ = self.validate_phase(phase)
            if ok:
                return phase
        return ring[0] if ring else None

    def safe_fallback_movements(self, ring: list[PhaseCandidate]) -> set[str]:
        phase = self.safe_fallback_phase(ring)
        if phase is None:
            return set()
        return set(phase.movements)

    def resolve_phase(
        self,
        phase: PhaseCandidate,
        ring: list[PhaseCandidate],
        *,
        context: str,
    ) -> PhaseCandidate:
        ok, reason = self.validate_phase(phase)
        if ok:
            return phase
        logger.critical(
            "PHASE_SAFETY_VIOLATION context=%s phase_id=%s movements=%s reason=%s",
            context,
            phase.id,
            sorted(phase.movements),
            reason,
        )
        fallback = self.safe_fallback_phase(ring)
        if fallback is None:
            logger.critical(
                "PHASE_SAFETY_FALLBACK_ALL_RED context=%s requested=%s",
                context,
                phase.id,
            )
            return PhaseCandidate("ALL_RED", frozenset(), "fail-safe all-red")
        logger.critical(
            "PHASE_SAFETY_FALLBACK context=%s from=%s to=%s movements=%s",
            context,
            phase.id,
            fallback.id,
            sorted(fallback.movements),
        )
        return fallback

    def resolve_movements(
        self,
        movements: set[str],
        ring: list[PhaseCandidate],
        *,
        context: str,
    ) -> set[str]:
        ok, reason = self.validate_protected_movements(movements)
        if ok:
            return set(movements)
        logger.critical(
            "PHASE_SAFETY_TLS_VIOLATION context=%s movements=%s reason=%s",
            context,
            sorted(movements),
            reason,
        )
        fallback = self.safe_fallback_movements(ring)
        if not fallback:
            logger.critical("PHASE_SAFETY_TLS_FALLBACK_ALL_RED context=%s", context)
            return set()
        logger.critical(
            "PHASE_SAFETY_TLS_FALLBACK context=%s movements=%s",
            context,
            sorted(fallback),
        )
        return set(fallback)


def sixteen_lane_conflict_matrix(topology: IntersectionTopology) -> dict[str, frozenset[str]]:
    if topology.num_links != SIXTEEN_LANE_NUM_LINKS:
        return {}
    out: dict[str, set[str]] = {mid: set() for mid in topology.movements if not mid.endswith("_RT")}
    for pair in build_forbidden_protected_pairs(topology):
        a, b = tuple(pair)
        out[a].add(b)
        out[b].add(a)
    return {mid: frozenset(conflicts) for mid, conflicts in out.items()}
