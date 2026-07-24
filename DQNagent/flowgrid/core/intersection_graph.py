"""
Intersection as a directed graph of movements with automated conflict mapping.

Golden rule: two movements that share a conflict point cannot both be green.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations


class MovementType(str, Enum):
    RIGHT = "right"
    THROUGH = "through"
    LEFT = "left"


@dataclass(frozen=True)
class Movement:
    id: str
    arm: str
    kind: MovementType
    links: tuple[int, ...]
    sensor_lanes: tuple[str, ...] = ()


# SUMO link-index foes at junction center (from network.net.xml <request foes="..."/>)
_LINK_FOES_TWO_LANE: list[tuple[int, ...]] = [
    (10, 11),
    (1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15),
    (1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15),
    (1, 2, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17),
    (4, 11, 12, 13, 14, 15, 16, 17, 18, 19),
    (11, 12, 13, 14, 15, 16, 17),
    (0, 1, 2, 3, 4, 6, 7, 8, 9, 16, 17, 18, 19),
    (0, 1, 2, 3, 4, 6, 7, 8, 9, 16, 17, 18, 19),
    (1, 2, 3, 4, 5, 6, 7, 9, 16, 17, 18, 19),
    (8, 18, 19),
    (),
    (1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18),
    (1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18),
    (0, 1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 16, 17, 18),
    (13, 14, 18, 19),
    (14, 15, 16, 17),
    (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 18),
    (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 18),
    (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 16, 17, 18, 19),
    (9, 19),
]

# Four dedicated lanes per approach (right-hand): 16 TLS links total.
_LINK_FOES_FOUR_LANE: list[tuple[int, ...]] = [
    (),
    (0, 1, 2, 4, 9, 10),
    (0, 1, 2, 4, 9, 10),
    (0, 5, 6, 8, 9, 10),
    (),
    (0, 5, 6, 12, 13, 14),
    (0, 5, 6, 12, 13, 14),
    (1, 2, 4, 5, 6, 12),
    (),
    (1, 2, 8, 9, 10, 12),
    (1, 2, 8, 9, 10, 12),
    (0, 1, 2, 8, 13, 14),
    (),
    (4, 5, 6, 8, 13, 14),
    (4, 5, 6, 8, 13, 14),
    (4, 9, 10, 12, 13, 14),
]

_LINK_FOES_BY_COUNT: dict[int, list[tuple[int, ...]]] = {
    20: _LINK_FOES_TWO_LANE,
    16: _LINK_FOES_FOUR_LANE,
}

_FOUR_LANE_APPROACH_PREFIX: dict[str, str] = {
    "N": "n_to_center",
    "S": "s_to_center",
    "E": "e_to_center",
    "W": "w_to_center",
}

# Back-compat alias for legacy 2-lane topology.
_LINK_FOES = _LINK_FOES_TWO_LANE


def _foes(link_index: int, num_links: int = 20) -> set[int]:
    table = _LINK_FOES_BY_COUNT.get(num_links, _LINK_FOES_TWO_LANE)
    return set(table[link_index])


def _links_conflict(a: int, b: int, num_links: int = 20) -> bool:
    return b in _foes(a, num_links) or a in _foes(b, num_links)


@dataclass
class IntersectionTopology:
    """N-way intersection topology with conflict matrix over movements."""

    movements: dict[str, Movement]
    arms: tuple[str, ...]
    opposing: dict[str, str] = field(default_factory=dict)
    num_links: int = 20
    _conflict_pairs: set[frozenset[str]] = field(default_factory=set, repr=False)

    @classmethod
    def standard_four_way(cls) -> IntersectionTopology:
        movements = {
            "N_RT": Movement("N_RT", "N", MovementType.RIGHT, (0,), ("n_to_center_0",)),
            "N_TH": Movement("N_TH", "N", MovementType.THROUGH, (1, 2), ("n_to_center_0", "n_to_center_1")),
            "N_LT": Movement("N_LT", "N", MovementType.LEFT, (3, 4), ("n_to_center_1",)),
            "S_RT": Movement("S_RT", "S", MovementType.RIGHT, (10,), ("s_to_center_0",)),
            "S_TH": Movement("S_TH", "S", MovementType.THROUGH, (11, 12), ("s_to_center_0", "s_to_center_1")),
            "S_LT": Movement("S_LT", "S", MovementType.LEFT, (13, 14), ("s_to_center_1",)),
            "E_RT": Movement("E_RT", "E", MovementType.RIGHT, (5,), ("e_to_center_0",)),
            "E_TH": Movement("E_TH", "E", MovementType.THROUGH, (6, 7), ("e_to_center_0", "e_to_center_1")),
            "E_LT": Movement("E_LT", "E", MovementType.LEFT, (8, 9), ("e_to_center_1",)),
            "W_RT": Movement("W_RT", "W", MovementType.RIGHT, (15,), ("w_to_center_0",)),
            "W_TH": Movement("W_TH", "W", MovementType.THROUGH, (16, 17), ("w_to_center_0", "w_to_center_1")),
            "W_LT": Movement("W_LT", "W", MovementType.LEFT, (18, 19), ("w_to_center_1",)),
        }
        topo = cls(
            movements=movements,
            arms=("N", "S", "E", "W"),
            opposing={"N": "S", "S": "N", "E": "W", "W": "E"},
        )
        topo._build_conflict_matrix()
        return topo

    @classmethod
    def standard_four_way_four_lane(cls) -> IntersectionTopology:
        """Four lanes per approach (right-hand): 0=right, 1-2=thru, 3=left."""
        movements = {
            "N_RT": Movement("N_RT", "N", MovementType.RIGHT, (0,), ("n_to_center_0",)),
            "N_TH": Movement("N_TH", "N", MovementType.THROUGH, (1, 2), ("n_to_center_1", "n_to_center_2")),
            "N_LT": Movement("N_LT", "N", MovementType.LEFT, (3,), ("n_to_center_3",)),
            "S_RT": Movement("S_RT", "S", MovementType.RIGHT, (8,), ("s_to_center_0",)),
            "S_TH": Movement("S_TH", "S", MovementType.THROUGH, (9, 10), ("s_to_center_1", "s_to_center_2")),
            "S_LT": Movement("S_LT", "S", MovementType.LEFT, (11,), ("s_to_center_3",)),
            "E_RT": Movement("E_RT", "E", MovementType.RIGHT, (4,), ("e_to_center_0",)),
            "E_TH": Movement("E_TH", "E", MovementType.THROUGH, (5, 6), ("e_to_center_1", "e_to_center_2")),
            "E_LT": Movement("E_LT", "E", MovementType.LEFT, (7,), ("e_to_center_3",)),
            "W_RT": Movement("W_RT", "W", MovementType.RIGHT, (12,), ("w_to_center_0",)),
            "W_TH": Movement("W_TH", "W", MovementType.THROUGH, (13, 14), ("w_to_center_1", "w_to_center_2")),
            "W_LT": Movement("W_LT", "W", MovementType.LEFT, (15,), ("w_to_center_3",)),
        }
        topo = cls(
            movements=movements,
            arms=("N", "S", "E", "W"),
            opposing={"N": "S", "S": "N", "E": "W", "W": "E"},
            num_links=16,
        )
        topo._build_conflict_matrix()
        return topo

    @classmethod
    def standard_four_way_three_lane(cls) -> IntersectionTopology:
        """Three lanes per approach: 0=left, 1=thru, 2=right (Israeli layout)."""
        movements = {
            "N_RT": Movement("N_RT", "N", MovementType.RIGHT, (0,), ("n_to_center_2",)),
            "N_TH": Movement("N_TH", "N", MovementType.THROUGH, (1, 2), ("n_to_center_1",)),
            "N_LT": Movement("N_LT", "N", MovementType.LEFT, (3, 4), ("n_to_center_0",)),
            "S_RT": Movement("S_RT", "S", MovementType.RIGHT, (10,), ("s_to_center_2",)),
            "S_TH": Movement("S_TH", "S", MovementType.THROUGH, (11, 12), ("s_to_center_1",)),
            "S_LT": Movement("S_LT", "S", MovementType.LEFT, (13, 14), ("s_to_center_0",)),
            "E_RT": Movement("E_RT", "E", MovementType.RIGHT, (5,), ("e_to_center_2",)),
            "E_TH": Movement("E_TH", "E", MovementType.THROUGH, (6, 7), ("e_to_center_1",)),
            "E_LT": Movement("E_LT", "E", MovementType.LEFT, (8, 9), ("e_to_center_0",)),
            "W_RT": Movement("W_RT", "W", MovementType.RIGHT, (15,), ("w_to_center_2",)),
            "W_TH": Movement("W_TH", "W", MovementType.THROUGH, (16, 17), ("w_to_center_1",)),
            "W_LT": Movement("W_LT", "W", MovementType.LEFT, (18, 19), ("w_to_center_0",)),
        }
        topo = cls(
            movements=movements,
            arms=("N", "S", "E", "W"),
            opposing={"N": "S", "S": "N", "E": "W", "W": "E"},
        )
        topo._build_conflict_matrix()
        return topo

    @classmethod
    def from_arms(cls, arm_movements: dict[str, list[tuple[MovementType, tuple[int, ...], tuple[str, ...]]]]) -> IntersectionTopology:
        """Build topology for arbitrary arms (3-way, 5-way, …)."""
        movements: dict[str, Movement] = {}
        arms = tuple(arm_movements.keys())
        opposing: dict[str, str] = {}
        if len(arms) == 4 and set(arms) == {"N", "S", "E", "W"}:
            return cls.standard_four_way()

        for arm in arms:
            for kind, links, lanes in arm_movements[arm]:
                mid = f"{arm}_{kind.value[:2].upper()}"
                movements[mid] = Movement(mid, arm, kind, links, lanes)

        topo = cls(movements=movements, arms=arms, opposing=opposing)
        topo._build_conflict_matrix()
        return topo

    def _build_conflict_matrix(self) -> None:
        self._conflict_pairs.clear()
        ids = list(self.movements.keys())
        for a, b in combinations(ids, 2):
            if self._movements_conflict(self.movements[a], self.movements[b]):
                self._conflict_pairs.add(frozenset((a, b)))

    def _movements_conflict(self, m1: Movement, m2: Movement) -> bool:
        for la in m1.links:
            for lb in m2.links:
                if _links_conflict(la, lb, self.num_links):
                    return True
        return False

    def movements_conflict(self, m1_id: str, m2_id: str) -> bool:
        return frozenset((m1_id, m2_id)) in self._conflict_pairs

    def is_compatible(self, movement_ids: set[str]) -> bool:
        ids = list(movement_ids)
        if len(ids) == 2:
            m1, m2 = self.movements[ids[0]], self.movements[ids[1]]
            if m1.arm == m2.arm and {m1.kind, m2.kind} == {MovementType.THROUGH, MovementType.LEFT}:
                return True
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                if self.movements_conflict(a, b):
                    return False
        return True

    def queue_lanes_for_movement(self, mov: Movement) -> tuple[str, ...]:
        if self.num_links == 16:
            prefix = _FOUR_LANE_APPROACH_PREFIX.get(mov.arm)
            if prefix:
                if mov.kind == MovementType.THROUGH:
                    return (f"{prefix}_1", f"{prefix}_2")
                if mov.kind == MovementType.LEFT:
                    return (f"{prefix}_3",)
                if mov.kind == MovementType.RIGHT:
                    return (f"{prefix}_0",)
        if mov.sensor_lanes:
            return mov.sensor_lanes
        return ()

    def expand_free_rights(self, active: set[str]) -> set[str]:
        if self.num_links == 16:
            return set(active)
        result = set(active)
        for mid, mov in self.movements.items():
            if mov.kind != MovementType.RIGHT:
                continue
            if mid in result:
                continue
            trial = result | {mid}
            if self.is_compatible(trial):
                result = trial
        return result

    def conflict_matrix_dict(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {m: [] for m in self.movements}
        for pair in self._conflict_pairs:
            a, b = tuple(pair)
            out[a].append(b)
            out[b].append(a)
        return out
