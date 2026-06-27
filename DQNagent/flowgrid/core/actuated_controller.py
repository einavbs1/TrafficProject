"""
Sensor-driven actuated phasing with a per-arm phase ring.

Default ring: North -> South -> East -> West, each phase greens thru + left on that arm.
Dynamic: skip empty arms; bulk-first switching; optional demand-based preemption.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from flowgrid.core.intersection_graph import IntersectionTopology, MovementType
from flowgrid.core.phase_safety import PhaseSafetyGate
from flowgrid.core.phasing_schemes import (
    DEFAULT_SCHEME,
    DUAL_PEEL_PHASES,
    PhaseCandidate,
    build_phase_ring,
    directional_resume_id,
    dual_phase_arms,
)

ARM_RING = build_phase_ring(DEFAULT_SCHEME, separate_right_turn=True)

STRICT_ROTATION_PHASE_IDS = (
    "NS_LEFT",
    "NS_THRU",
    "NS_THRU_RT",
    "EW_LEFT",
    "EW_THRU",
    "EW_THRU_RT",
    "N_ALL",
    "S_ALL",
    "E_ALL",
    "W_ALL",
)

BALANCED_ROTATION_PHASE_IDS = (
    "NS_LEFT",
    "NS_THRU",
    "EW_LEFT",
    "EW_THRU",
)

DQN_ROTATION_PHASE_IDS = (
    "NS_LEFT",
    "NS_THRU",
    "EW_LEFT",
    "EW_THRU",
)

# Legacy split ring (dual left / dual thru per axis) — kept for reference only
PROTECTED_RING = [
    PhaseCandidate("NS_LEFT", frozenset({"N_LT", "S_LT"}), "Dual left: N + S"),
    PhaseCandidate("NS_THRU", frozenset({"N_TH", "S_TH"}), "Dual thru: N + S"),
    PhaseCandidate("EW_LEFT", frozenset({"E_LT", "W_LT"}), "Dual left: E + W"),
    PhaseCandidate("EW_THRU", frozenset({"E_TH", "W_TH"}), "Dual thru: E + W"),
]

ABS_MIN_GREEN_THRU_SECONDS = 15.0
ABS_MIN_GREEN_LEFT_SECONDS = 10.0


def _default_skip_stats() -> dict[str, dict]:
    return {
        phase_id: {"count": 0, "reasons": {}}
        for phase_id in DQN_ROTATION_PHASE_IDS
    }


@dataclass(frozen=True)
class GreenFlowSnapshot:
    moving_count: int
    detection_occupied: bool
    upstream_queued: int
    seconds_since_detection: float
    max_competing_red_wait: float


@dataclass
class ActuatedController:
    topology: IntersectionTopology
    queue_threshold: int = 1
    min_platoon_vehicles: int = 3
    min_platoon_wait_seconds: float = 25.0
    demand_ratio_to_preempt: float = 0.4
    competing_demand_threshold: int = 3
    starvation_override_seconds: float = 90.0
    flow_speed_threshold: float = 1.0
    gap_out_seconds: float = 3.0
    platoon_min_moving: int = 2
    ring: list[PhaseCandidate] = field(default_factory=lambda: list(ARM_RING))
    separate_right_turn: bool = True
    directional_phases_enabled: bool = False
    safety_gate: PhaseSafetyGate | None = field(default=None, repr=False)
    ring_index: int = 0
    current_phase_id: str = "N_ALL"
    current_movements: set[str] = field(default_factory=lambda: {"N_TH", "N_LT"})
    last_description: str = "North: thru + left"
    current_phase_duration: float = 0.0
    min_green_time: float = 25.0
    max_green_time: float = 90.0
    _peel_source_phase_id: str | None = field(default=None, repr=False)
    _peeled_arms_this_axis: set[str] = field(default_factory=set, repr=False)
    _rotation_slot_index: int = 0
    skip_stats: dict[str, dict] = field(default_factory=_default_skip_stats)
    _debug_rotation_enabled: bool = False
    _skip_tracking_enabled: bool = False

    def _debug_dump_rotation_config(self) -> None:
        if not self._debug_rotation_enabled:
            return
        static_sequence = self._build_rotation_sequence()
        print(
            f"[ROTATION_DEBUG] DQN_ROTATION_PHASE_IDS={DQN_ROTATION_PHASE_IDS}",
            flush=True,
        )
        print(
            f"[ROTATION_DEBUG] _build_rotation_sequence() static={[phase.id for phase in static_sequence]}",
            flush=True,
        )
        print(
            f"[ROTATION_DEBUG] topology num_links={self.topology.num_links} "
            f"directional_phases_enabled={self.directional_phases_enabled}",
            flush=True,
        )
        print(
            f"[ROTATION_DEBUG] queue_threshold={self.queue_threshold} "
            f"min_platoon_vehicles={self.min_platoon_vehicles}",
            flush=True,
        )

    def _debug_print_backbone_demand_status(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> None:
        if not self._debug_rotation_enabled or not self.directional_phases_enabled:
            return
        backbone_ids, sequence = self._rotation_context(queues, lane_totals)
        next_forward = (
            backbone_ids[(self._rotation_slot_index + 1) % len(backbone_ids)]
            if backbone_ids
            else None
        )
        print(
            f"[ROTATION_DEBUG] static backbone _build_rotation_sequence()="
            f"{[phase.id for phase in sequence]}",
            flush=True,
        )
        print(
            f"[ROTATION_DEBUG] rotation_slot_index={self._rotation_slot_index} "
            f"next_forward_slot={next_forward}",
            flush=True,
        )
        print(
            f"[ROTATION_DEBUG] skip_stats={self.skip_stats}",
            flush=True,
        )
        for phase_id in backbone_ids:
            phase = self._phase_by_id(phase_id)
            if phase is None:
                continue
            has_demand = self._incoming_phase_has_demand(phase, queues, lane_totals)
            if lane_totals is not None:
                occupancy = self._occupancy_for_phase(phase, lane_totals)
                metric = f"lane occupancy {occupancy}"
            else:
                occupancy = self._demand_for_phase(phase, queues)
                metric = f"queue occupancy {occupancy}"
            print(
                f"[ROTATION_DEBUG] Phase {phase_id} Demand: {has_demand} based on {metric}",
                flush=True,
            )

    def __post_init__(self) -> None:
        if self.safety_gate is None and self.topology.num_links == 16:
            object.__setattr__(
                self,
                "safety_gate",
                PhaseSafetyGate(
                    self.topology,
                    separate_right_turn=self.separate_right_turn,
                    ring=self.ring,
                ),
            )

    def current_baseline_cap(self) -> str:
        phase = next((p for p in self.ring if p.id == self.current_phase_id), None)
        if phase:
            return phase.baseline_cap
        return "through"

    def absolute_min_green_seconds(self) -> float:
        phase_id = self.current_phase_id
        if self._is_directional_phase_id(phase_id):
            return ABS_MIN_GREEN_LEFT_SECONDS
        cap = self.current_baseline_cap()
        if cap == "full_arm":
            return ABS_MIN_GREEN_LEFT_SECONDS
        if phase_id.endswith("_LEFT") or cap == "left":
            return ABS_MIN_GREEN_LEFT_SECONDS
        if "_THRU" in phase_id or cap == "through":
            return ABS_MIN_GREEN_THRU_SECONDS
        return ABS_MIN_GREEN_THRU_SECONDS

    def competing_phase_demand(self, queues: dict[str, int]) -> int:
        green = self.green_arms()
        return max(
            (int(self.arm_demand(queues, arm)) for arm in self.topology.arms if arm not in green),
            default=0,
        )

    def has_incoming_green_flow(self, snapshot: GreenFlowSnapshot) -> bool:
        if snapshot.detection_occupied:
            return True
        if snapshot.moving_count >= 1:
            return True
        return snapshot.upstream_queued >= self.queue_threshold

    def platoon_active(self, snapshot: GreenFlowSnapshot) -> bool:
        if snapshot.moving_count >= self.platoon_min_moving:
            return True
        if snapshot.moving_count >= 1 and snapshot.upstream_queued >= self.queue_threshold:
            return True
        if snapshot.detection_occupied and snapshot.seconds_since_detection < self.gap_out_seconds:
            return True
        return False

    def gap_sufficient(self, snapshot: GreenFlowSnapshot) -> bool:
        if snapshot.detection_occupied:
            return False
        return snapshot.seconds_since_detection >= self.gap_out_seconds

    def starvation_override_active(self, snapshot: GreenFlowSnapshot) -> bool:
        return snapshot.max_competing_red_wait >= self.starvation_override_seconds

    def advance_blocked_for_flow(
        self,
        queues: dict[str, int],
        snapshot: GreenFlowSnapshot,
        *,
        time_in_phase: float,
        max_green_seconds: float,
    ) -> bool:
        competing_low = self.competing_phase_demand(queues) < self.competing_demand_threshold
        if (
            competing_low
            and self.has_incoming_green_flow(snapshot)
            and not self.starvation_override_active(snapshot)
        ):
            return True
        if (
            self.platoon_active(snapshot)
            and not self.gap_sufficient(snapshot)
            and time_in_phase < max_green_seconds
        ):
            return True
        return False

    def _movement_halting_count(self, mov, lane_halting_fn) -> int:
        lanes = self.topology.queue_lanes_for_movement(mov)
        return sum(int(lane_halting_fn(lane)) for lane in lanes)

    def _demand_for_movement(self, movement_id: str, lane_halting_fn) -> int:
        mov = self.topology.movements.get(movement_id)
        if mov is None:
            return 0
        return self._movement_halting_count(mov, lane_halting_fn)

    def read_queues(self, lane_halting_fn) -> dict[str, int]:
        queues: dict[str, int] = {}
        for mid, mov in self.topology.movements.items():
            queues[mid] = self._movement_halting_count(mov, lane_halting_fn)
        return queues

    def _movement_lane_total(self, mov, lane_total_fn) -> int:
        lanes = self.topology.queue_lanes_for_movement(mov)
        return sum(int(lane_total_fn(lane)) for lane in lanes)

    def read_lane_totals(self, lane_total_fn) -> dict[str, int]:
        totals: dict[str, int] = {}
        for mid, mov in self.topology.movements.items():
            totals[mid] = self._movement_lane_total(mov, lane_total_fn)
        return totals

    def _occupancy_for_phase(self, phase: PhaseCandidate, lane_totals: dict[str, int]) -> int:
        return sum(int(lane_totals.get(m, 0)) for m in phase.movements)

    def _phase_has_vehicle_presence(self, phase: PhaseCandidate, lane_totals: dict[str, int]) -> bool:
        return self._occupancy_for_phase(phase, lane_totals) > 0

    def arm_lane_occupancy(self, lane_totals: dict[str, int], arm: str) -> int:
        return sum(
            int(lane_totals.get(mid, 0))
            for mid, m in self.topology.movements.items()
            if m.arm == arm
        )

    def _movement_has_presence(
        self,
        arm: str,
        suffix: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> bool:
        movement_id = f"{arm}_{suffix}"
        if lane_totals is not None:
            return int(lane_totals.get(movement_id, 0)) > 0
        return int(queues.get(movement_id, 0)) > 0

    def _arm_has_combined_demand(
        self,
        arm: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> bool:
        return self._movement_has_presence(arm, "TH", queues, lane_totals) and self._movement_has_presence(
            arm, "LT", queues, lane_totals
        )

    def _arm_combined_occupancy(
        self,
        arm: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> int:
        if lane_totals is not None:
            return int(lane_totals.get(f"{arm}_TH", 0)) + int(lane_totals.get(f"{arm}_LT", 0))
        return self._arm_movement_demand(queues, arm, "TH") + self._arm_movement_demand(queues, arm, "LT")

    def _axis_arms_for_backbone(self, phase_id: str) -> tuple[str, ...]:
        if phase_id in ("NS_THRU", "NS_THRU_RT", "NS_LEFT"):
            return ("N", "S")
        if phase_id in ("EW_THRU", "EW_THRU_RT", "EW_LEFT"):
            return ("E", "W")
        return ()

    def _phase_is_safe(self, phase: PhaseCandidate) -> bool:
        if self.safety_gate is None:
            return True
        ok, _ = self.safety_gate.validate_phase(phase)
        return ok

    def _incoming_phase_has_demand(
        self,
        phase: PhaseCandidate,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> bool:
        if self._is_directional_phase_id(phase.id):
            return self._arm_has_combined_demand(phase.id[0], queues, lane_totals)
        if lane_totals is not None:
            return self._phase_has_vehicle_presence(phase, lane_totals)
        return self._demand_for_phase(phase, queues) > 0

    def arm_demand(self, queues: dict[str, int], arm: str) -> int:
        return sum(queues.get(mid, 0) for mid, m in self.topology.movements.items() if m.arm == arm)

    def is_arm_empty(self, queues: dict[str, int], arm: str) -> bool:
        return self.arm_demand(queues, arm) < self.queue_threshold

    def green_arms(self) -> set[str]:
        arms: set[str] = set()
        for mid in self.current_movements:
            mov = self.topology.movements.get(mid)
            if mov:
                arms.add(mov.arm)
        return arms

    def current_phase_demand(self, queues: dict[str, int]) -> int:
        phase = next((p for p in self.ring if p.id == self.current_phase_id), None)
        if phase:
            return self._demand_for_phase(phase, queues)
        return sum(queues.get(mid, 0) for mid in self.current_movements)

    def _dominant_backlog(self, queues: dict[str, int], arm_waits: dict[str, float]) -> float:
        scores = [
            float(self.arm_demand(queues, arm)) + arm_waits.get(arm, 0.0) / 15.0
            for arm in self.topology.arms
        ]
        return max(scores) if scores else 0.0

    def should_hold_green_for_bulk(self, queues: dict[str, int]) -> bool:
        """Keep current green while a meaningful batch is still being served."""
        if self.current_phase_demand(queues) >= 2:
            return True
        for arm in self.green_arms():
            if self.arm_demand(queues, arm) >= 2:
                return True
        return False

    def _arm_justifies_preempt(
        self,
        arm: str,
        queues: dict[str, int],
        arm_waits: dict[str, float],
        dominant: float,
    ) -> bool:
        q = self.arm_demand(queues, arm)
        w = arm_waits.get(arm, 0.0)
        if q < self.queue_threshold and w <= 0:
            return False

        green_residual = max(
            self.current_phase_demand(queues),
            max((self.arm_demand(queues, a) for a in self.green_arms()), default=0),
        )
        if green_residual >= 2:
            return False

        max_other_red = max(
            (
                self.arm_demand(queues, a)
                for a in self.topology.arms
                if a not in self.green_arms() and a != arm
            ),
            default=0,
        )
        if q <= 1 and w < self.min_platoon_wait_seconds:
            if max_other_red > q or green_residual > 0:
                return False

        batch_ok = q >= self.min_platoon_vehicles
        wait_ok = w >= self.min_platoon_wait_seconds and q >= self.queue_threshold
        if not (batch_ok or wait_ok):
            return False

        pressure = float(q) + w / 20.0
        if dominant > 0 and pressure < dominant * self.demand_ratio_to_preempt:
            if q < self.min_platoon_vehicles:
                return False
        if max_other_red > q + 1:
            return False
        return True

    def best_inactive_arm_to_serve(
        self, queues: dict[str, int], arm_waits: dict[str, float]
    ) -> str | None:
        """Pick the red approach worth serving — bulk first, not a lone car over a big platoon."""
        if self.should_hold_green_for_bulk(queues):
            return None
        dominant = self._dominant_backlog(queues, arm_waits)
        candidates: list[tuple[str, float]] = []
        for arm in self.topology.arms:
            if arm in self.green_arms():
                continue
            if not self._arm_justifies_preempt(arm, queues, arm_waits, dominant):
                continue
            q = self.arm_demand(queues, arm)
            w = arm_waits.get(arm, 0.0)
            candidates.append((arm, float(q) + w / 15.0))
        if not candidates:
            return None
        return max(candidates, key=lambda item: item[1])[0]

    def _phases_for_arm(self, arm: str) -> list[PhaseCandidate]:
        out: list[PhaseCandidate] = []
        for phase in self.ring:
            phase_arms = {
                self.topology.movements[m].arm
                for m in phase.movements
                if m in self.topology.movements
            }
            if arm in phase_arms:
                out.append(phase)
        return out

    def _is_left_phase(self, phase: PhaseCandidate) -> bool:
        for mid in phase.movements:
            mov = self.topology.movements.get(mid)
            if mov and mov.kind == MovementType.LEFT:
                return True
        return False

    def _rotation_phase_ids(self) -> tuple[str, ...]:
        if self.directional_phases_enabled:
            return DQN_ROTATION_PHASE_IDS
        if self.topology.num_links == 16 and self.separate_right_turn:
            return BALANCED_ROTATION_PHASE_IDS
        return STRICT_ROTATION_PHASE_IDS

    def _build_rotation_sequence(
        self,
        queues: dict[str, int] | None = None,
        lane_totals: dict[str, int] | None = None,
    ) -> list[PhaseCandidate]:
        _, sequence = self._rotation_context(queues, lane_totals)
        return sequence

    def _rotation_context(
        self,
        queues: dict[str, int] | None = None,
        lane_totals: dict[str, int] | None = None,
    ) -> tuple[tuple[str, ...], list[PhaseCandidate]]:
        by_id = {phase.id: phase for phase in self.ring}
        backbone_ids = self._rotation_phase_ids()
        sequence = [by_id[pid] for pid in backbone_ids if pid in by_id]
        if not sequence:
            sequence = list(self.ring)
        return backbone_ids, sequence

    def _record_phase_skip(
        self,
        phase_id: str,
        reason: str,
        demand_snapshot: str | None = None,
    ) -> None:
        if phase_id not in self.skip_stats:
            self.skip_stats[phase_id] = {"count": 0, "reasons": {}}
        self.skip_stats[phase_id]["count"] += 1
        reasons = self.skip_stats[phase_id]["reasons"]
        reasons[reason] = reasons.get(reason, 0) + 1
        if self._skip_tracking_enabled:
            demand_part = f" | Demand: {demand_snapshot}" if demand_snapshot else ""
            print(
                f"[SKIP_TRACKER] Skipped Phase: {phase_id} | Reason: {reason}{demand_part}",
                flush=True,
            )

    def _slot_demand_snapshot(
        self,
        backbone_id: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> str:
        if backbone_id in ("NS_LEFT", "NS_THRU"):
            return (
                f"N_LT={self._movement_demand('N', 'LT', queues, lane_totals)}, "
                f"N_TH={self._movement_demand('N', 'TH', queues, lane_totals)}, "
                f"S_LT={self._movement_demand('S', 'LT', queues, lane_totals)}, "
                f"S_TH={self._movement_demand('S', 'TH', queues, lane_totals)}"
            )
        if backbone_id in ("EW_LEFT", "EW_THRU"):
            return (
                f"E_LT={self._movement_demand('E', 'LT', queues, lane_totals)}, "
                f"E_TH={self._movement_demand('E', 'TH', queues, lane_totals)}, "
                f"W_LT={self._movement_demand('W', 'LT', queues, lane_totals)}, "
                f"W_TH={self._movement_demand('W', 'TH', queues, lane_totals)}"
            )
        return ""

    def _pendulum_candidate_slots(self) -> list[int]:
        slot_map = {
            0: [1],
            1: [2, 3],
            2: [3],
            3: [0, 1],
        }
        return slot_map[self._rotation_slot_index]

    def _skip_reason_for_slot(
        self,
        backbone_id: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> str | None:
        backbone = self._phase_by_id(backbone_id)
        if backbone is None:
            return "Empty / No Demand"
        resolved = self._resolve_axis_slot(backbone_id, queues, lane_totals)
        if self._incoming_phase_has_demand(resolved, queues, lane_totals):
            return None
        if self._peeled_arms_this_axis:
            for arm in self._peeled_arms_this_axis:
                if any(movement.startswith(f"{arm}_") for movement in backbone.movements):
                    return "Already served by combined phase"
        return "Empty / No Demand"

    def _select_iron_rotation_phase(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
        *,
        record_skips: bool = True,
    ) -> PhaseCandidate | None:
        backbone_ids, sequence = self._rotation_context(queues, lane_totals)
        if not sequence:
            return None
        candidate_slots = self._pendulum_candidate_slots()
        for slot_idx in candidate_slots:
            backbone = sequence[slot_idx]
            reason = self._skip_reason_for_slot(backbone.id, queues, lane_totals)
            if reason is not None:
                if record_skips:
                    self._record_phase_skip(
                        backbone.id,
                        reason,
                        self._slot_demand_snapshot(backbone.id, queues, lane_totals),
                    )
                continue
            return self._upgrade_rotation_slot(backbone, queues, lane_totals)
        fallback_backbone = sequence[candidate_slots[0]]
        if record_skips:
            self._record_phase_skip(
                fallback_backbone.id,
                "Empty / No Demand",
                self._slot_demand_snapshot(fallback_backbone.id, queues, lane_totals),
            )
        return self._upgrade_rotation_slot(fallback_backbone, queues, lane_totals)

    def _upgrade_rotation_slot(
        self,
        backbone: PhaseCandidate,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> PhaseCandidate:
        return self._resolve_axis_slot(backbone.id, queues, lane_totals)

    def _movement_demand(
        self,
        arm: str,
        suffix: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> int:
        movement_id = f"{arm}_{suffix}"
        if lane_totals is not None:
            return int(lane_totals.get(movement_id, 0))
        return int(queues.get(movement_id, 0))

    def _safe_directional_peel(self, arm: str) -> PhaseCandidate | None:
        peel = self._phase_by_id(f"{arm}_ALL")
        if peel is not None and self._phase_is_safe(peel):
            return peel
        return None

    def _resolve_left_axis_slot(
        self,
        left_id: str,
        arm_a: str,
        arm_b: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> PhaseCandidate:
        backbone = self._phase_by_id(left_id)
        if backbone is None:
            return self.ring[self.ring_index]
        a_lt = self._movement_demand(arm_a, "LT", queues, lane_totals)
        b_lt = self._movement_demand(arm_b, "LT", queues, lane_totals)
        a_th = self._movement_demand(arm_a, "TH", queues, lane_totals)
        b_th = self._movement_demand(arm_b, "TH", queues, lane_totals)
        if a_lt > 0 and b_lt > 0:
            return backbone
        if a_lt > 0 and a_th > 0 and b_lt == 0:
            peel = self._safe_directional_peel(arm_a)
            if peel is not None:
                return peel
        if b_lt > 0 and b_th > 0 and a_lt == 0:
            peel = self._safe_directional_peel(arm_b)
            if peel is not None:
                return peel
        return backbone

    def _resolve_axis_slot(
        self,
        backbone_id: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> PhaseCandidate:
        if backbone_id == "NS_LEFT":
            return self._resolve_left_axis_slot("NS_LEFT", "N", "S", queues, lane_totals)
        if backbone_id == "EW_LEFT":
            return self._resolve_left_axis_slot("EW_LEFT", "E", "W", queues, lane_totals)
        if backbone_id in ("NS_THRU", "EW_THRU"):
            phase = self._phase_by_id(backbone_id)
            if phase is not None:
                return phase
        phase = self._phase_by_id(backbone_id)
        if phase is not None:
            return phase
        return self.ring[self.ring_index]

    def _current_slot_index(self, backbone_ids: tuple[str, ...]) -> int:
        anchor = self._rotation_anchor_phase_id()
        if anchor in backbone_ids:
            return backbone_ids.index(anchor)
        if self.current_phase_id in backbone_ids:
            return backbone_ids.index(self.current_phase_id)
        return -1

    def _rotation_anchor_phase_id(self) -> str:
        if (
            self.directional_phases_enabled
            and self._is_directional_phase_id(self.current_phase_id)
            and self._peel_source_phase_id
        ):
            return self._peel_source_phase_id
        return self.current_phase_id

    def _phase_in_sequence(self, sequence: list[PhaseCandidate], phase_id: str) -> PhaseCandidate | None:
        for phase in sequence:
            if phase.id == phase_id:
                return phase
        return None

    def _current_phase_in_sequence(self, sequence: list[PhaseCandidate]) -> PhaseCandidate:
        phase = self._phase_in_sequence(sequence, self._rotation_anchor_phase_id())
        if phase is not None:
            return phase
        for candidate in sequence:
            if candidate.id == self.current_phase_id:
                return candidate
        return self.ring[self.ring_index]

    def _next_backbone_after(
        self,
        phase_id: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
    ) -> PhaseCandidate | None:
        backbone_ids, sequence = self._rotation_context(queues, lane_totals)
        if not sequence:
            return None
        try:
            start = backbone_ids.index(phase_id)
        except ValueError:
            return self._next_phase_in_rotation(queues, lane_totals)
        n = len(backbone_ids)
        for offset in range(1, n + 1):
            phase = sequence[(start + offset) % n]
            if self._incoming_phase_has_demand(phase, queues, lane_totals):
                return phase
        return sequence[(start + 1) % n]

    def _next_phase_in_rotation(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
    ) -> PhaseCandidate | None:
        if self.directional_phases_enabled:
            return self._select_iron_rotation_phase(queues, lane_totals)
        backbone_ids, sequence = self._rotation_context(queues, lane_totals)
        if not sequence:
            return None
        start = self._current_slot_index(backbone_ids)
        n = len(backbone_ids)
        for offset in range(1, n + 1):
            backbone = sequence[(start + offset) % n]
            if self._incoming_phase_has_demand(backbone, queues, lane_totals):
                return backbone
        return sequence[(start + 1) % n]

    def _current_phase_serves_left(self) -> bool:
        for mid in self.current_movements:
            mov = self.topology.movements.get(mid)
            if mov and mov.kind == MovementType.LEFT:
                return True
        return False

    def _is_directional_phase_id(self, phase_id: str) -> bool:
        return phase_id.endswith("_ALL") and len(phase_id) == 5 and phase_id[0] in self.topology.arms

    def _dual_peel_movement_suffix(self, phase_id: str) -> str | None:
        if phase_id.endswith("_LEFT"):
            return "LT"
        if phase_id.endswith("_THRU"):
            return "TH"
        return None

    def _arm_movement_demand(self, queues: dict[str, int], arm: str, suffix: str) -> int:
        return int(queues.get(f"{arm}_{suffix}", 0))

    def _phase_by_id(self, phase_id: str) -> PhaseCandidate | None:
        return next((p for p in self.ring if p.id == phase_id), None)

    def _other_peel_arm(self, source_id: str, directional_id: str) -> str | None:
        arms = dual_phase_arms(source_id)
        if arms is None:
            return None
        served = directional_id[0]
        if served not in arms:
            return None
        return arms[0] if arms[1] == served else arms[1]

    def _unserved_peel_arm_demand(self, queues: dict[str, int], source_id: str, directional_id: str) -> int:
        suffix = self._dual_peel_movement_suffix(source_id)
        other_arm = self._other_peel_arm(source_id, directional_id)
        if suffix is None or other_arm is None:
            return 0
        return self._arm_movement_demand(queues, other_arm, suffix)

    def _select_combined_phase(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
        *,
        backbone_id: str | None = None,
        exclude_arms: frozenset[str] = frozenset(),
    ) -> PhaseCandidate | None:
        if not self.directional_phases_enabled or self.topology.num_links != 16:
            return None
        source_id = backbone_id or self.current_phase_id
        if source_id not in DUAL_PEEL_PHASES and source_id not in DQN_ROTATION_PHASE_IDS:
            return None
        arms = self._axis_arms_for_backbone(source_id)
        best_peel: PhaseCandidate | None = None
        best_score = 0
        for arm in arms:
            if arm in exclude_arms:
                continue
            if not self._arm_has_combined_demand(arm, queues, lane_totals):
                continue
            peel = self._phase_by_id(f"{arm}_ALL")
            if peel is None or not self._phase_is_safe(peel):
                continue
            score = self._arm_combined_occupancy(arm, queues, lane_totals)
            if score > best_score:
                best_score = score
                best_peel = peel
        if best_peel is not None:
            return best_peel
        if source_id not in DUAL_PEEL_PHASES:
            return None
        suffix = self._dual_peel_movement_suffix(source_id)
        dual_arms = dual_phase_arms(source_id)
        if suffix is None or dual_arms is None:
            return None
        arm_a, arm_b = dual_arms
        demand_a = self._arm_movement_demand(queues, arm_a, suffix)
        demand_b = self._arm_movement_demand(queues, arm_b, suffix)
        if demand_a == demand_b:
            return None
        if demand_a > demand_b:
            if demand_a <= 0 or demand_b != 0:
                return None
            winner = arm_a
        else:
            if demand_b <= 0 or demand_a != 0:
                return None
            winner = arm_b
        if winner in exclude_arms:
            return None
        peel = self._phase_by_id(f"{winner}_ALL")
        if peel is not None and self._phase_is_safe(peel):
            return peel
        return None

    def _resume_from_directional(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
    ) -> PhaseCandidate | None:
        if self.directional_phases_enabled:
            return None
        if self.topology.num_links != 16:
            return None
        if not self._is_directional_phase_id(self.current_phase_id):
            return None
        source = self._peel_source_phase_id
        if not source:
            return None
        unserved = self._unserved_peel_arm_demand(queues, source, self.current_phase_id)
        if unserved > 0:
            other_arm = self._other_peel_arm(source, self.current_phase_id)
            if other_arm is not None:
                other_phase = self._phase_by_id(f"{other_arm}_ALL")
                if (
                    other_phase is not None
                    and self._phase_is_safe(other_phase)
                    and self._incoming_phase_has_demand(other_phase, queues, lane_totals)
                ):
                    return other_phase
            source_phase = self._phase_by_id(source)
            if source_phase is not None:
                return source_phase
        resume_id = directional_resume_id(source, self.current_phase_id)
        if resume_id:
            resume_phase = self._phase_by_id(resume_id)
            if (
                resume_phase is not None
                and self._phase_is_safe(resume_phase)
                and self._incoming_phase_has_demand(resume_phase, queues, lane_totals)
            ):
                return resume_phase
        return self._next_backbone_after(source, queues, lane_totals)

    def _arms_for_phase(self, phase: PhaseCandidate) -> set[str]:
        return {
            self.topology.movements[m].arm
            for m in phase.movements
            if m in self.topology.movements
        }

    def phase_for_arm(
        self,
        arm: str,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
    ) -> PhaseCandidate | None:
        if self.directional_phases_enabled and self._arm_has_combined_demand(arm, queues, lane_totals):
            peel = self._phase_by_id(f"{arm}_ALL")
            if (
                peel is not None
                and self._phase_is_safe(peel)
                and self._incoming_phase_has_demand(peel, queues, lane_totals)
            ):
                return peel
        phases = self._phases_for_arm(arm)
        if not phases:
            return None
        phase_ids = {p.id for p in phases}
        ordered = [p for p in self._build_rotation_sequence(queues, lane_totals) if p.id in phase_ids]
        if not ordered:
            ordered = phases
        for phase in ordered:
            if self._incoming_phase_has_demand(phase, queues, lane_totals):
                return phase
        return None

    def _demand_for_phase(
        self,
        phase: PhaseCandidate,
        queues: dict[str, int],
        lane_halting_fn=None,
    ) -> int:
        if lane_halting_fn is None:
            return sum(queues.get(m, 0) for m in phase.movements)
        return sum(self._demand_for_movement(m, lane_halting_fn) for m in phase.movements)

    def build_phase_candidates(self, queues: dict[str, int]) -> list[PhaseCandidate]:
        candidates: list[PhaseCandidate] = []
        for phase in self.ring:
            if self._demand_for_phase(phase, queues) >= self.queue_threshold:
                candidates.append(phase)
        if not candidates:
            candidates.append(self.ring[0])
        return candidates

    def movements_overlap(self, prev: set[str], nxt: set[str]) -> bool:
        return bool(prev & nxt)

    def select_next_phase(
        self,
        queues: dict[str, int],
        arm_waits: dict[str, float] | None = None,
        *,
        emergency_arms: frozenset[str] | None = None,
        transit_arms: frozenset[str] | None = None,
        priority_service: object | None = None,
        lane_totals: dict[str, int] | None = None,
        log_debug: bool = True,
    ) -> PhaseCandidate:
        if log_debug:
            self._debug_print_backbone_demand_status(queues, lane_totals)
        waits = arm_waits or {}
        emg = emergency_arms or frozenset()
        rotation_next: PhaseCandidate | None = None
        if not self.directional_phases_enabled:
            rotation_next = self._next_phase_in_rotation(queues, lane_totals)
        if priority_service is not None:
            deferred = self._pick_deferred_priority_arm(
                queues,
                waits,
                emg,
                transit_arms or frozenset(),
                priority_service,
            )
            if deferred:
                phase = self.phase_for_arm(deferred, queues, lane_totals)
                if phase and phase.id != self.current_phase_id:
                    if deferred in emg:
                        return phase
                    if not self.directional_phases_enabled:
                        if rotation_next is None:
                            rotation_next = self._next_phase_in_rotation(queues, lane_totals)
                        if rotation_next is not None and deferred in self._arms_for_phase(rotation_next):
                            return phase

        if self.directional_phases_enabled:
            iron_next = self._select_iron_rotation_phase(queues, lane_totals)
            if iron_next is not None:
                return iron_next
            backbone_ids, sequence = self._rotation_context(queues, lane_totals)
            return self._current_phase_in_sequence(sequence)

        resume = self._resume_from_directional(queues, lane_totals)
        if resume is not None:
            return resume

        if self._is_directional_phase_id(self.current_phase_id):
            current_peel = self._phase_by_id(self.current_phase_id)
            if (
                current_peel is not None
                and self._incoming_phase_has_demand(current_peel, queues, lane_totals)
            ):
                return current_peel

        if not self._is_directional_phase_id(self.current_phase_id):
            current_backbone = self._phase_by_id(self.current_phase_id)
            if current_backbone is not None:
                if self._demand_for_phase(current_backbone, queues) > 0:
                    peel = self._select_combined_phase(
                        queues,
                        lane_totals,
                        exclude_arms=frozenset(self._peeled_arms_this_axis),
                    )
                    if peel is not None:
                        return peel
                    return current_backbone

        if rotation_next is not None:
            return rotation_next
        backbone_ids, sequence = self._rotation_context(queues, lane_totals)
        return self._current_phase_in_sequence(sequence)

    def peek_next_phase(
        self,
        queues: dict[str, int],
        arm_waits: dict[str, float] | None = None,
        *,
        emergency_arms: frozenset[str] | None = None,
        transit_arms: frozenset[str] | None = None,
        priority_service: object | None = None,
        lane_totals: dict[str, int] | None = None,
    ) -> PhaseCandidate:
        return self.select_next_phase(
            queues,
            arm_waits,
            emergency_arms=emergency_arms,
            transit_arms=transit_arms,
            priority_service=priority_service,
            lane_totals=lane_totals,
            log_debug=False,
        )

    def _all_rings_empty(self, queues: dict[str, int]) -> bool:
        return all(self._demand_for_phase(p, queues) < self.queue_threshold for p in self.ring)

    def apply_phase(self, phase: PhaseCandidate, *, context: str = "apply_phase") -> set[str]:
        if self.safety_gate is not None:
            phase = self.safety_gate.resolve_phase(phase, self.ring, context=context)
        previous_id = self.current_phase_id
        self.current_phase_id = phase.id
        self.current_movements = set(phase.movements)
        self.last_description = phase.description
        for i, p in enumerate(self.ring):
            if p.id == phase.id:
                self.ring_index = i
                break
        if self.directional_phases_enabled:
            slot_id: str | None = None
            if phase.id in DQN_ROTATION_PHASE_IDS:
                slot_id = phase.id
            elif self._is_directional_phase_id(phase.id) and previous_id in DQN_ROTATION_PHASE_IDS:
                slot_id = previous_id
            elif (
                self._is_directional_phase_id(phase.id)
                and self._is_directional_phase_id(previous_id)
                and self._peel_source_phase_id in DQN_ROTATION_PHASE_IDS
            ):
                slot_id = self._peel_source_phase_id
            if slot_id is not None:
                self._rotation_slot_index = DQN_ROTATION_PHASE_IDS.index(slot_id)
            if self._is_directional_phase_id(phase.id) and (
                previous_id in DUAL_PEEL_PHASES or previous_id in DQN_ROTATION_PHASE_IDS
            ):
                self._peel_source_phase_id = previous_id
                if previous_id in DQN_ROTATION_PHASE_IDS:
                    self._peeled_arms_this_axis.add(phase.id[0])
            elif self._is_directional_phase_id(phase.id) and self._is_directional_phase_id(previous_id):
                self._peeled_arms_this_axis.add(phase.id[0])
            elif not self._is_directional_phase_id(phase.id):
                if self._is_directional_phase_id(previous_id):
                    self._peel_source_phase_id = None
                if previous_id == "NS_THRU" and phase.id == "EW_LEFT":
                    self._peeled_arms_this_axis.clear()
                elif previous_id == "EW_THRU" and phase.id == "NS_LEFT":
                    self._peeled_arms_this_axis.clear()
        if self.separate_right_turn:
            return self.current_movements
        return self.topology.expand_free_rights(self.current_movements)

    def advance_fixed_time(self) -> set[str]:
        sequence = self._build_rotation_sequence()
        if not sequence:
            n = len(self.ring)
            idx = (self.ring_index + 1) % n
            return self.apply_phase(self.ring[idx])
        try:
            start = sequence.index(self._current_phase_in_sequence(sequence))
        except ValueError:
            start = -1
        next_phase = sequence[(start + 1) % len(sequence)]
        return self.apply_phase(next_phase)

    def _pick_deferred_priority_arm(
        self,
        queues: dict[str, int],
        arm_waits: dict[str, float],
        emergency_arms: frozenset[str],
        transit_arms: frozenset[str],
        ps,
    ) -> str | None:
        """Schedule next green for bus/emergency arms without starving heavier red queues."""
        if ps.defer_emergency_to_next_green:
            for arm in sorted(emergency_arms, key=lambda a: arm_waits.get(a, 0.0), reverse=True):
                if arm in self.green_arms():
                    continue
                return arm
        if ps.defer_transit_to_next_green:
            for arm in sorted(transit_arms, key=lambda a: arm_waits.get(a, 0.0), reverse=True):
                if arm in self.green_arms() or arm in emergency_arms:
                    continue
                if self._priority_arm_fair_to_serve(arm, queues, arm_waits, ps):
                    return arm
        return None

    def _priority_arm_fair_to_serve(
        self,
        arm: str,
        queues: dict[str, int],
        arm_waits: dict[str, float],
        ps,
    ) -> bool:
        q_a = self.arm_demand(queues, arm)
        w_a = arm_waits.get(arm, 0.0)
        if q_a < self.queue_threshold and w_a < 5.0:
            return False
        margin = int(ps.starvation_queue_margin)
        wait_ratio = float(ps.starvation_wait_ratio)
        for other in self.topology.arms:
            if other == arm or other in self.green_arms():
                continue
            oq = self.arm_demand(queues, other)
            ow = arm_waits.get(other, 0.0)
            if oq >= self.min_platoon_vehicles and oq > q_a + margin:
                return False
            if ow >= self.min_platoon_wait_seconds and ow > w_a * wait_ratio:
                return False
        return True

    def advance(
        self,
        queues: dict[str, int],
        arm_waits: dict[str, float] | None = None,
        *,
        emergency_arms: frozenset[str] | None = None,
        transit_arms: frozenset[str] | None = None,
        priority_service: object | None = None,
        lane_totals: dict[str, int] | None = None,
    ) -> set[str]:
        phase = self.select_next_phase(
            queues,
            arm_waits,
            emergency_arms=emergency_arms,
            transit_arms=transit_arms,
            priority_service=priority_service,
            lane_totals=lane_totals,
        )
        return self.apply_phase(phase)

    def _current_phase_has_demand(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None,
    ) -> bool:
        phase = self._phase_by_id(self.current_phase_id)
        if phase is None:
            fallback = PhaseCandidate(
                self.current_phase_id,
                frozenset(self.current_movements),
                self.last_description,
            )
            return self._demand_for_phase(fallback, queues) > 0
        return self._incoming_phase_has_demand(phase, queues, lane_totals)

    def should_skip_current(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
    ) -> bool:
        if self.current_phase_duration < self.min_green_time:
            return False
        if self.current_phase_duration > self.max_green_time:
            return True
        if not self._current_phase_has_demand(queues, lane_totals):
            return True
        return False
