from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from flowgrid.paths import DEFAULTS_DIR, REPORTS_DIR

DEFAULT_CONFIG_PATH = DEFAULTS_DIR / "dqn_policy_config.yaml"
DEFAULT_TRAINING_LOG_PATH = REPORTS_DIR / "dqn_training_log.jsonl"


def _load_transit_priority_scale(reward_raw: dict) -> float:
    if "transit_priority_scale" in reward_raw:
        return float(reward_raw["transit_priority_scale"])
    legacy = float(reward_raw.get("transit_delay_multiplier", 1.0))
    return max(0.0, legacy - 1.0)


@dataclass
class RewardWeights:
    delay_delta_scale: float = 1.0
    total_wait_scale: float = 1.0e-3
    drain_bonus_per_vehicle: float = 2.0
    drain_bonus_fleet_drop: float = 1.0
    fairness_cap: float = 50.0
    transit_delay_multiplier: float = 1.0
    transit_priority_scale: float = 0.4
    emergency_priority_scale: float = 0.35
    spillback_penalty: float = -1000.0
    throughput_per_vehicle: float = 8.0
    fairness_imbalance_weight: float = -0.08
    starving_arms_weight: float = -0.35
    inactive_wait_weight: float = -0.03
    inactive_wait_threshold: float = 60.0
    switch_penalty: float = -18.0
    platoon_interrupt_penalty: float = -40.0
    consecutive_clear_bonus: float = 3.0
    invalid_action_penalty: float = -8.0


@dataclass
class PriorityServiceParams:
    """Bus/emergency get the next green when switching — not an instant phase cut."""

    instant_emergency_preempt: bool = False
    defer_emergency_to_next_green: bool = True
    defer_transit_to_next_green: bool = True
    starvation_queue_margin: int = 2
    starvation_wait_ratio: float = 1.5


@dataclass
class ConstraintParams:
    min_green_base_seconds: float = 5.0
    min_green_cap_seconds: float = 60.0
    absolute_safety_min_seconds: float = 4.0
    sec_per_car: float = 2.5
    switch_min_vehicles: int = 3
    switch_min_wait_seconds: float = 25.0
    demand_ratio_to_preempt: float = 0.4
    queue_threshold: int = 1
    gap_out_seconds: float = 3.0
    flow_speed_threshold: float = 1.0
    platoon_min_moving: int = 2
    starvation_override_seconds: float = 90.0
    all_red_seconds: float = 2.0
    camera_range_meters: float = 150.0
    stop_line_zone_meters: float = 50.0


@dataclass
class TrainingParams:
    learning_rate: float = 1e-3
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: float = 0.99
    batch_size: int = 64
    buffer_capacity: int = 10000
    target_update_freq: int = 10
    step_length: int = 3
    device: str = "auto"


@dataclass
class EpisodeTrainingParams:
    min_sim_seconds: float = 30.0
    clear_streak_steps: int = 2
    max_steps: int = 1500
    max_sim_seconds: float = 2400.0
    busy_fraction: float = 0.4
    busy_warmup_sim_seconds: float = 450.0
    train_base_seed: int = 42


@dataclass
class PhaseBandParams:
    flow_min: float = 0.10
    flow_max: float = 0.30
    busy_min: float = 0.0
    busy_max: float = 0.0
    bus_min: float = 0.0
    bus_max: float = 0.0
    emg_min: float = 0.0
    emg_max: float = 0.0


@dataclass
class RandomTrafficTrainingParams:
    rebalance_phases: bool = True
    phase_bands: dict[str, PhaseBandParams] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.phase_bands:
            self.phase_bands = {
                "easy": PhaseBandParams(
                    flow_min=0.10,
                    flow_max=0.30,
                    busy_min=0.0,
                    busy_max=0.0,
                    bus_min=0.0,
                    bus_max=0.0,
                    emg_min=0.0,
                    emg_max=0.0,
                ),
                "medium": PhaseBandParams(
                    flow_min=0.40,
                    flow_max=0.70,
                    busy_min=0.10,
                    busy_max=0.25,
                    bus_min=0.005,
                    bus_max=0.015,
                    emg_min=0.001,
                    emg_max=0.003,
                ),
                "hard": PhaseBandParams(
                    flow_min=0.80,
                    flow_max=1.00,
                    busy_min=0.30,
                    busy_max=0.50,
                    bus_min=0.015,
                    bus_max=0.025,
                    emg_min=0.003,
                    emg_max=0.008,
                ),
            }


def _load_phase_band(raw: dict) -> PhaseBandParams:
    return PhaseBandParams(
        flow_min=float(raw.get("flow_min", 0.10)),
        flow_max=float(raw.get("flow_max", 0.30)),
        busy_min=float(raw.get("busy_min", 0.0)),
        busy_max=float(raw.get("busy_max", 0.0)),
        bus_min=float(raw.get("bus_min", 0.0)),
        bus_max=float(raw.get("bus_max", 0.0)),
        emg_min=float(raw.get("emg_min", 0.0)),
        emg_max=float(raw.get("emg_max", 0.0)),
    )


def _load_random_traffic_training(raw: dict | None) -> RandomTrafficTrainingParams:
    if not raw:
        return RandomTrafficTrainingParams()
    bands_raw = raw.get("phase_bands") or {}
    bands: dict[str, PhaseBandParams] = {}
    defaults = RandomTrafficTrainingParams().phase_bands
    for label in ("easy", "medium", "hard"):
        if label in bands_raw:
            bands[label] = _load_phase_band(bands_raw[label])
        else:
            bands[label] = defaults[label]
    return RandomTrafficTrainingParams(
        rebalance_phases=bool(raw.get("rebalance_phases", True)),
        phase_bands=bands,
    )


@dataclass
class BaselineTimingParams:
    through_seconds_default: float = 60.0
    left_to_through_ratio: float = 0.60


@dataclass
class FineTuneParams:
    """Gentle hyperparameters when resuming an existing checkpoint."""
    apply_on_resume: bool = True
    preserve_epsilon: bool = True
    epsilon_resume_bump: float = 0.0
    epsilon_start: float = 0.05
    epsilon_decay: float = 0.995
    learning_rate: float = 0.0005
    target_update_freq: int = 5


@dataclass
class PolicyConfig:
    version: int = 1
    name: str = "FlowGrid DQN"
    objectives: dict[str, Any] = field(default_factory=dict)
    actions: dict[str, str] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    reward: RewardWeights = field(default_factory=RewardWeights)
    priority_service: PriorityServiceParams = field(default_factory=PriorityServiceParams)
    constraints: ConstraintParams = field(default_factory=ConstraintParams)
    training: TrainingParams = field(default_factory=TrainingParams)
    episode_training: EpisodeTrainingParams = field(default_factory=EpisodeTrainingParams)
    random_traffic_training: RandomTrafficTrainingParams = field(
        default_factory=RandomTrafficTrainingParams
    )
    baseline_timing: BaselineTimingParams = field(default_factory=BaselineTimingParams)
    fine_tune: FineTuneParams = field(default_factory=FineTuneParams)
    source_path: str = ""

    @classmethod
    def load(cls, path: str | Path | None = None) -> PolicyConfig:
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not cfg_path.is_file():
            return cls(source_path=str(cfg_path))
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        reward_raw = raw.get("reward") or {}
        ps_raw = raw.get("priority_service") or {}
        constr_raw = raw.get("constraints") or {}
        train_raw = raw.get("training") or {}
        ep_raw = raw.get("episode_training") or {}
        rt_raw = raw.get("random_traffic_training") or {}
        ft_raw = raw.get("fine_tune") or {}
        return cls(
            version=int(raw.get("version", 1)),
            name=str(raw.get("name", "FlowGrid DQN")),
            objectives=dict(raw.get("objectives") or {}),
            actions={str(k): str(v) for k, v in (raw.get("actions") or {}).items()},
            observations=list(raw.get("observations") or []),
            priority_service=PriorityServiceParams(
                instant_emergency_preempt=bool(ps_raw.get("instant_emergency_preempt", False)),
                defer_emergency_to_next_green=bool(ps_raw.get("defer_emergency_to_next_green", True)),
                defer_transit_to_next_green=bool(ps_raw.get("defer_transit_to_next_green", True)),
                starvation_queue_margin=int(ps_raw.get("starvation_queue_margin", 2)),
                starvation_wait_ratio=float(ps_raw.get("starvation_wait_ratio", 1.5)),
            ),
            reward=RewardWeights(
                delay_delta_scale=float(reward_raw.get("delay_delta_scale", 1.0)),
                total_wait_scale=float(reward_raw.get("total_wait_scale", 1.0e-3)),
                drain_bonus_per_vehicle=float(reward_raw.get("drain_bonus_per_vehicle", 2.0)),
                drain_bonus_fleet_drop=float(reward_raw.get("drain_bonus_fleet_drop", 1.0)),
                fairness_cap=float(reward_raw.get("fairness_cap", 50.0)),
                transit_delay_multiplier=float(reward_raw.get("transit_delay_multiplier", 1.0)),
                transit_priority_scale=_load_transit_priority_scale(reward_raw),
                emergency_priority_scale=float(reward_raw.get("emergency_priority_scale", 0.35)),
                spillback_penalty=float(reward_raw.get("spillback_penalty", -1000)),
                throughput_per_vehicle=float(reward_raw.get("throughput_per_vehicle", 8.0)),
                fairness_imbalance_weight=float(reward_raw.get("fairness_imbalance_weight", -0.08)),
                starving_arms_weight=float(reward_raw.get("starving_arms_weight", -0.35)),
                inactive_wait_weight=float(reward_raw.get("inactive_wait_weight", -0.03)),
                inactive_wait_threshold=float(reward_raw.get("inactive_wait_threshold", 60)),
                switch_penalty=float(reward_raw.get("switch_penalty", -18.0)),
                platoon_interrupt_penalty=float(reward_raw.get("platoon_interrupt_penalty", -40.0)),
                consecutive_clear_bonus=float(reward_raw.get("consecutive_clear_bonus", 3.0)),
                invalid_action_penalty=float(reward_raw.get("invalid_action_penalty", -8.0)),
            ),
            constraints=ConstraintParams(
                min_green_base_seconds=float(constr_raw.get("min_green_base_seconds", 5)),
                min_green_cap_seconds=float(constr_raw.get("min_green_cap_seconds", 60)),
                absolute_safety_min_seconds=float(constr_raw.get("absolute_safety_min_seconds", 4)),
                sec_per_car=float(constr_raw.get("sec_per_car", 2.5)),
                switch_min_vehicles=int(constr_raw.get("switch_min_vehicles", 3)),
                switch_min_wait_seconds=float(constr_raw.get("switch_min_wait_seconds", 25)),
                demand_ratio_to_preempt=float(constr_raw.get("demand_ratio_to_preempt", 0.4)),
                queue_threshold=int(constr_raw.get("queue_threshold", 1)),
                gap_out_seconds=float(constr_raw.get("gap_out_seconds", 3.0)),
                flow_speed_threshold=float(constr_raw.get("flow_speed_threshold", 1.0)),
                platoon_min_moving=int(constr_raw.get("platoon_min_moving", 2)),
                starvation_override_seconds=float(constr_raw.get("starvation_override_seconds", 90.0)),
                all_red_seconds=float(constr_raw.get("all_red_seconds", 2.0)),
                camera_range_meters=float(constr_raw.get("camera_range_meters", 150.0)),
                stop_line_zone_meters=float(constr_raw.get("stop_line_zone_meters", 50.0)),
            ),
            training=TrainingParams(
                learning_rate=float(train_raw.get("learning_rate", 1e-3)),
                gamma=float(train_raw.get("gamma", 0.99)),
                epsilon_start=float(train_raw.get("epsilon_start", 1.0)),
                epsilon_end=float(train_raw.get("epsilon_end", 0.01)),
                epsilon_decay=float(train_raw.get("epsilon_decay", 0.99)),
                batch_size=int(train_raw.get("batch_size", 64)),
                buffer_capacity=int(train_raw.get("buffer_capacity", 10000)),
                target_update_freq=int(train_raw.get("target_update_freq", 10)),
                step_length=int(train_raw.get("step_length", 3)),
                device=str(train_raw.get("device", "auto")),
            ),
            episode_training=EpisodeTrainingParams(
                min_sim_seconds=float(ep_raw.get("min_sim_seconds", 30)),
                clear_streak_steps=int(ep_raw.get("clear_streak_steps", 2)),
                max_steps=int(ep_raw.get("max_steps", 1500)),
                max_sim_seconds=float(ep_raw.get("max_sim_seconds", 2400)),
                busy_fraction=float(ep_raw.get("busy_fraction", 0.4)),
                busy_warmup_sim_seconds=float(ep_raw.get("busy_warmup_sim_seconds", 450)),
                train_base_seed=int(ep_raw.get("train_base_seed", 42)),
            ),
            random_traffic_training=_load_random_traffic_training(rt_raw),
            baseline_timing=BaselineTimingParams(
                through_seconds_default=float(raw.get("baseline_through_seconds_default", 60)),
                left_to_through_ratio=float(raw.get("baseline_left_to_through_ratio", 0.60)),
            ),
            fine_tune=FineTuneParams(
                apply_on_resume=bool(ft_raw.get("apply_on_resume", True)),
                preserve_epsilon=bool(ft_raw.get("preserve_epsilon", True)),
                epsilon_resume_bump=float(ft_raw.get("epsilon_resume_bump", 0.0)),
                epsilon_start=float(ft_raw.get("epsilon_start", 0.05)),
                epsilon_decay=float(ft_raw.get("epsilon_decay", 0.995)),
                learning_rate=float(ft_raw.get("learning_rate", 0.0005)),
                target_update_freq=int(ft_raw.get("target_update_freq", 5)),
            ),
            source_path=str(cfg_path.resolve()),
        )

    def objectives_summary_lines(self) -> list[str]:
        lines = [f"Policy: {self.name}", f"Config: {self.source_path or DEFAULT_CONFIG_PATH}"]
        primary = self.objectives.get("primary")
        if primary:
            lines.append(f"PRIMARY (maximize reward ≈ minimize): {primary}")
        for label, key in (
            ("Secondary", "secondary"),
            ("Hard rules (not learned)", "enforced_outside_rl"),
        ):
            items = self.objectives.get(key)
            if items:
                lines.append(f"{label}:")
                lines.extend(f"  - {item}" for item in items)
        lines.append(
            "Reward priority: spillback > delay_delta (all vehicles + bus/emergency extras) "
            "> total_wait penalty > drain bonus > throughput > fairness (capped)"
        )
        lines.append("Action masking: invalid switch requests penalized without phase change")
        lines.append("Actions:")
        for k in sorted(self.actions.keys(), key=lambda x: int(x) if x.isdigit() else x):
            lines.append(f"  {k} = {self.actions[k]}")
        return lines
