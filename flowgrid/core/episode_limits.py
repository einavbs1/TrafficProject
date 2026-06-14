"""Shared rules for ending RL / compare episodes when the junction clears."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EpisodeLimits:
    min_sim_seconds: float = 30.0
    clear_streak_steps: int = 2
    max_steps: int = 1500
    max_sim_seconds: float = 2400.0
    queue_clear_threshold: int = 0
    require_empty_network: bool = False


# Default training / compare drain settings from the improvement plan.
DEFAULT_EPISODE_LIMITS = EpisodeLimits()


@dataclass
class EpisodeEndState:
    step_count: int = 0
    clear_streak: int = 0
    ended_reason: str = ""
    start_kind: str = "fresh"  # fresh | busy_snapshot


class EpisodeDrainTracker:
    """Track vehicles seen this episode and detect junction-clear drain."""

    def __init__(self, limits: EpisodeLimits | None = None):
        self.limits = limits or DEFAULT_EPISODE_LIMITS
        self.cohort_ids: set[str] = set()
        self.state = EpisodeEndState()

    def begin_episode(self, *, start_kind: str = "fresh", initial_vehicle_ids: set[str] | None = None) -> None:
        self.cohort_ids = set(initial_vehicle_ids or ())
        self.state = EpisodeEndState(start_kind=start_kind)

    def register_vehicle_ids(self, vehicle_ids: set[str] | list[str]) -> None:
        self.cohort_ids.update(vehicle_ids)

    def check_after_step(
        self,
        *,
        sim_time: float,
        total_queue: int,
        active_vehicle_ids: set[str] | list[str],
    ) -> tuple[bool, str]:
        """
        Call once per agent step after the simulation advances.
        Returns (should_end, reason). reason is empty until end triggers.
        """
        lim = self.limits
        self.state.step_count += 1
        active = set(active_vehicle_ids)
        self.register_vehicle_ids(active)

        if self.state.step_count >= lim.max_steps:
            self.state.ended_reason = "max_steps"
            return True, "max_steps"

        if sim_time >= lim.max_sim_seconds:
            self.state.ended_reason = "max_time"
            return True, "max_time"

        if sim_time < lim.min_sim_seconds:
            self.state.clear_streak = 0
            return False, ""

        queues_clear = total_queue <= lim.queue_clear_threshold

        if lim.require_empty_network:
            network_empty = len(active) == 0
        else:
            network_empty = not bool(self.cohort_ids & active)

        if network_empty and queues_clear:
            self.state.clear_streak += 1
            if self.state.clear_streak >= lim.clear_streak_steps:
                self.state.ended_reason = "drained"
                return True, "drained"
        else:
            self.state.clear_streak = 0

        return False, ""
