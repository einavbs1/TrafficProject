import os
import sys
import shutil
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import traci

from flowgrid.core.actuated_controller import ActuatedController, GreenFlowSnapshot
from flowgrid.core.intersection_graph import IntersectionTopology, MovementType
from flowgrid.core.signal_phases import LANES, MOVEMENTS, approach_signal, movement_signal
from flowgrid.core.tls_builder import baseline_left_duration, build_all_red, build_all_yellow, build_tls_state
from flowgrid.core.episode_limits import DEFAULT_EPISODE_LIMITS, EpisodeDrainTracker, EpisodeLimits
from flowgrid.rl.policy_config import PolicyConfig

ARMS = ("N", "S", "E", "W")
TRANSIT_VCLASS = frozenset({"bus", "coach", "tram", "trolleybus"})
TRANSIT_TYPE_HINTS = ("bus", "transit", "coach")


class SumoEnv(gym.Env):
    def __init__(
        self,
        sumocfg_file,
        gui=False,
        gui_delay=80,
        step_length=3,
        yellow_duration=3,
        all_red_seconds: float | None = None,
        camera_range_meters: float | None = None,
        stop_line_zone_meters: float | None = None,
        min_green_time=10,
        min_green_seconds: float | None = 60,
        min_green_base_seconds: float = 5.0,
        green_seconds_per_vehicle: float = 2.0,
        switch_min_vehicles: int = 3,
        switch_min_wait_seconds: float = 25.0,
        max_green_seconds: float | None = None,
        baseline_green_seconds=None,
        baseline_through_seconds: float | None = None,
        baseline_left_to_through_ratio: float | None = None,
        phase_ring=None,
        separate_right_turn: bool = True,
        on_step=None,
        topology: IntersectionTopology | None = None,
        quit_on_end: bool | None = None,
        snapshot_path: str | None = None,
        live_updates: bool = True,
        policy_config: PolicyConfig | None = None,
        end_when_clear: bool = False,
        episode_limits: EpisodeLimits | None = None,
        log_phase_tracker: bool = False,
    ):
        super().__init__()
        self.policy_config = policy_config or PolicyConfig.load()
        self.sumocfg_file = sumocfg_file
        self.gui = gui
        self.gui_delay = gui_delay
        self.quit_on_end = quit_on_end if quit_on_end is not None else (not gui)
        self.step_length = step_length
        self.yellow_duration = yellow_duration
        self.all_red_seconds = int(
            round(float(all_red_seconds or self.policy_config.constraints.all_red_seconds))
        )
        self.camera_range_meters = float(
            camera_range_meters or self.policy_config.constraints.camera_range_meters
        )
        self.stop_line_zone_meters = float(
            stop_line_zone_meters or self.policy_config.constraints.stop_line_zone_meters
        )
        self.min_green_time = min_green_time
        self.min_green_seconds = min_green_seconds
        self.min_green_base_seconds = float(min_green_base_seconds)
        self.green_seconds_per_vehicle = float(green_seconds_per_vehicle)
        self.max_green_seconds = max_green_seconds
        self.baseline_green_seconds = baseline_green_seconds
        self.baseline_through_seconds = (
            float(baseline_through_seconds)
            if baseline_through_seconds is not None
            else (float(baseline_green_seconds) if baseline_green_seconds is not None else 60.0)
        )
        if baseline_left_to_through_ratio is not None:
            self.baseline_left_to_through_ratio = float(baseline_left_to_through_ratio)
        else:
            self.baseline_left_to_through_ratio = float(
                self.policy_config.baseline_timing.left_to_through_ratio
            )
        self.separate_right_turn = bool(separate_right_turn)
        self._phase_ring = phase_ring
        self.on_step = on_step
        self.live_updates = live_updates
        self.snapshot_path = snapshot_path
        self._snapshot_saved = False
        self.end_when_clear = bool(end_when_clear)
        self.log_phase_tracker = bool(log_phase_tracker)
        self._episode_limits = episode_limits or DEFAULT_EPISODE_LIMITS
        self._episode_tracker = EpisodeDrainTracker(self._episode_limits)
        self._departure_recorder: tuple[list, set[str], dict] | None = None
        self._traci_active = False
        self.topology = topology or IntersectionTopology.standard_four_way_four_lane()
        self._switch_min_vehicles = int(switch_min_vehicles)
        self._switch_min_wait_seconds = float(switch_min_wait_seconds)
        self.controller = self._make_controller()
        self.time_since_last_switch = 0
        self.sim_time = 0.0
        self.tls_id = "center"
        self.action_space = spaces.Discrete(2)
        n_mov = len(self.topology.movements)
        n_arms = len(self.topology.arms)
        obs_dim = n_mov + n_arms + n_arms + 1 + 1 + n_arms
        self.observation_space = spaces.Box(low=0, high=1, shape=(obs_dim,), dtype=np.float32)
        self.lanes = self._lanes_from_topology(self.topology)
        self.lane_lengths = {lane: 489.60 for lanes in self.lanes.values() for lane in lanes}
        self._tls_state = "r" * self.topology.num_links
        self._prev_wait = 0.0
        self._prev_transit_wait = 0.0
        self._prev_emergency_wait = 0.0
        self._prev_arrived = 0
        self._prev_fleet_size = 0
        self._emergency_active = False
        self._last_invalid_action = False
        self._seconds_since_green_detection = 0.0
        self._consecutive_clears_since_switch = 0
        self._platoon_active_prev_step = False
        self._phase_switched_this_step = False
        self._reset_episode_transparency()

        sumo_binary = "sumo-gui" if self.gui else "sumo"
        sumo_path = shutil.which(sumo_binary)
        if not sumo_path:
            sumo_path = os.path.join(os.path.dirname(sys.executable), "Scripts", sumo_binary + ".exe")
        self.sumo_cmd = [
            sumo_path,
            "-c",
            self.sumocfg_file,
            "--no-step-log",
            "true",
            "--no-warnings",
            "true",
            "--waiting-time-memory",
            "10000",
            "--time-to-teleport",
            "3600",
        ]
        if self.gui:
            self.sumo_cmd.extend(
                [
                    "--start",
                    "--delay",
                    str(self.gui_delay),
                    "--quit-on-end",
                    "true" if self.quit_on_end else "false",
                ]
            )

    def _sumo_start_cmd(
        self,
        *,
        seed: int | None = None,
        route_files: str | None = None,
    ) -> list[str]:
        cmd = list(self.sumo_cmd)
        if route_files:
            cmd.extend(["--route-files", str(route_files)])
        if seed is not None:
            cmd.extend(["--seed", str(seed)])
        return cmd

    @staticmethod
    def _lanes_from_topology(topology: IntersectionTopology) -> dict[str, list[str]]:
        order = (MovementType.LEFT, MovementType.THROUGH, MovementType.RIGHT)
        out: dict[str, list[str]] = {}
        for arm in topology.arms:
            lanes: list[str] = []
            for kind in order:
                for mov in topology.movements.values():
                    if mov.arm != arm or mov.kind != kind:
                        continue
                    for sl in topology.queue_lanes_for_movement(mov):
                        if sl not in lanes:
                            lanes.append(sl)
            out[arm] = lanes
        return out

    def _arm_sensor_lanes(self, arm: str) -> tuple[str, ...]:
        mov_th = self.topology.movements[f"{arm}_TH"]
        mov_lt = self.topology.movements[f"{arm}_LT"]
        thru_lanes = self.topology.queue_lanes_for_movement(mov_th)
        left_lanes = self.topology.queue_lanes_for_movement(mov_lt)
        if len(thru_lanes) >= 2:
            return thru_lanes[0], thru_lanes[1], left_lanes[0]
        if thru_lanes:
            return thru_lanes[0], thru_lanes[0], left_lanes[0] if left_lanes else thru_lanes[0]
        return left_lanes[0], left_lanes[0], left_lanes[0]

    def _make_controller(self) -> ActuatedController:
        from flowgrid.core.phasing_schemes import (
            build_actuated_ring_with_directionals,
            build_baseline_balanced_ring,
            build_phase_ring,
        )

        c = self.policy_config.constraints
        if self.baseline_green_seconds is not None:
            ring = build_baseline_balanced_ring(self.separate_right_turn)
            directional = False
        else:
            base_ring = self._phase_ring or build_phase_ring("per_arm_full", self.separate_right_turn)
            if self.topology.num_links == 16:
                ring = build_actuated_ring_with_directionals(base_ring)
                directional = True
            else:
                ring = base_ring
                directional = False
        return ActuatedController(
            self.topology,
            queue_threshold=int(c.queue_threshold),
            min_platoon_vehicles=self._switch_min_vehicles,
            min_platoon_wait_seconds=self._switch_min_wait_seconds,
            demand_ratio_to_preempt=float(c.demand_ratio_to_preempt),
            competing_demand_threshold=int(c.switch_min_vehicles),
            starvation_override_seconds=float(c.starvation_override_seconds),
            flow_speed_threshold=float(c.flow_speed_threshold),
            gap_out_seconds=float(c.gap_out_seconds),
            platoon_min_moving=int(c.platoon_min_moving),
            ring=list(ring),
            separate_right_turn=self.separate_right_turn,
            directional_phases_enabled=directional,
        )

    def _init_controller(self):
        self.controller = self._make_controller()
        self.controller._debug_rotation_enabled = self.log_phase_tracker
        self.controller._skip_tracking_enabled = self.log_phase_tracker
        self.controller._debug_dump_rotation_config()
        start_phase = self.controller.ring[0]
        if self.controller.directional_phases_enabled:
            sequence = self.controller._build_rotation_sequence()
            if sequence:
                start_phase = sequence[0]
        active = self.controller.apply_phase(start_phase, context="init_controller")
        active = self._enforce_phase_safety(active, context="init_controller_tls")
        self._tls_state = build_tls_state(self.topology, active)
        traci.trafficlight.setRedYellowGreenState(self.tls_id, self._tls_state)
        self.time_since_last_switch = 0
        self.sim_time = float(traci.simulation.getTime())
        self._prev_wait = self._total_waiting_time()
        self._prev_transit_wait = self.total_transit_waiting_time()
        self._prev_emergency_wait = self.total_emergency_waiting_time()
        self._prev_arrived = int(traci.simulation.getArrivedNumber())
        try:
            self._prev_fleet_size = len(traci.vehicle.getIDList())
        except traci.exceptions.TraCIException:
            self._prev_fleet_size = 0
        self._emergency_active = False
        self._last_invalid_action = False
        self._seconds_since_green_detection = 0.0
        self._consecutive_clears_since_switch = 0
        self._platoon_active_prev_step = False
        self._phase_switched_this_step = False

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if "SUMO_HOME" in os.environ and os.path.join(os.environ["SUMO_HOME"], "tools") not in sys.path:
            sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))

        opts = options or {}
        busy_path = opts.get("load_busy_snapshot")
        if busy_path and os.path.isfile(str(busy_path)):
            if not self._traci_active:
                cmd = self._sumo_start_cmd(seed=seed, route_files=opts.get("route_files"))
                traci.start(cmd)
                self._traci_active = True
            traci.simulation.loadState(str(busy_path))
            self._init_controller()
            self._begin_episode_tracking(start_kind="busy_snapshot")
            state = self._get_state()
            return state, {
                "action_mask": self._action_mask(self._read_queues()),
                "episode_start_kind": "busy_snapshot",
            }

        reuse = bool(opts.get("reuse_snapshot"))
        busy_start = bool(opts.get("busy_snapshot"))
        if reuse and self._traci_active and self.snapshot_path and os.path.isfile(self.snapshot_path):
            traci.simulation.loadState(self.snapshot_path)
            self._init_controller()
            self._begin_episode_tracking(start_kind="busy_snapshot" if busy_start else "fresh")
            state = self._get_state()
            reset_info = {
                "action_mask": self._action_mask(self._read_queues()),
                "episode_start_kind": self._episode_tracker.state.start_kind,
            }
            return state, reset_info

        if self._traci_active:
            try:
                traci.close()
            except traci.exceptions.FatalTraCIError:
                pass
            self._traci_active = False

        cmd = self._sumo_start_cmd(seed=seed, route_files=opts.get("route_files"))

        traci.start(cmd)
        self._traci_active = True
        self._init_controller()

        if self.snapshot_path and not self._snapshot_saved:
            os.makedirs(os.path.dirname(self.snapshot_path) or ".", exist_ok=True)
            traci.simulation.saveState(self.snapshot_path)
            self._snapshot_saved = True

        self._begin_episode_tracking(start_kind="fresh")
        state = self._get_state()
        return state, {
            "action_mask": self._action_mask(self._read_queues()),
            "episode_start_kind": self._episode_tracker.state.start_kind,
        }

    def reload_from_snapshot(self):
        if not self.snapshot_path or not os.path.isfile(self.snapshot_path):
            raise RuntimeError("No simulation snapshot for reload")
        traci.simulation.loadState(self.snapshot_path)
        self._init_controller()
        self._begin_episode_tracking(start_kind="busy_snapshot")
        state = self._get_state()
        return state, {
            "action_mask": self._action_mask(self._read_queues()),
            "episode_start_kind": self._episode_tracker.state.start_kind,
        }

    def _reset_episode_transparency(self) -> None:
        self._episode_transparency = {
            "phase_seconds": {},
            "actions": {
                "hold": 0,
                "advance": 0,
                "forced_hold": 0,
                "forced_advance": 0,
            },
            "reward_components": {},
        }

    def _accumulate_phase_second(self, seconds: float = 1.0) -> None:
        phase_id = self.controller.current_phase_id
        phase_seconds = self._episode_transparency["phase_seconds"]
        phase_seconds[phase_id] = float(phase_seconds.get(phase_id, 0.0)) + float(seconds)

    def _record_step_action(self, mask, applied: int) -> None:
        actions = self._episode_transparency["actions"]
        voluntary = bool(mask[0] and mask[1])
        if voluntary:
            if applied == 0:
                actions["hold"] += 1
            else:
                actions["advance"] += 1
        elif bool(mask[1]) and not bool(mask[0]):
            actions["forced_advance"] += 1
        else:
            actions["forced_hold"] += 1

    def _record_reward_components(self, components: dict[str, float]) -> None:
        totals = self._episode_transparency["reward_components"]
        for key, value in components.items():
            totals[key] = float(totals.get(key, 0.0)) + float(value)

    def get_episode_transparency(self) -> dict:
        return {
            "phase_seconds": dict(self._episode_transparency.get("phase_seconds") or {}),
            "actions": dict(self._episode_transparency.get("actions") or {}),
            "reward_components": dict(self._episode_transparency.get("reward_components") or {}),
        }

    def _begin_episode_tracking(self, *, start_kind: str) -> None:
        self._reset_episode_transparency()
        if not self.end_when_clear:
            return
        initial_ids: set[str] = set()
        if self._traci_active:
            try:
                initial_ids = set(traci.vehicle.getIDList())
            except traci.exceptions.TraCIException:
                initial_ids = set()
        self._episode_tracker.begin_episode(start_kind=start_kind, initial_vehicle_ids=initial_ids)

    def _total_approach_queue(self) -> int:
        return sum(self._read_queues().values())

    def _active_vehicle_ids(self) -> set[str]:
        try:
            return set(traci.vehicle.getIDList())
        except traci.exceptions.TraCIException:
            return set()

    def _enforce_phase_safety(self, movements: set[str], *, context: str) -> set[str]:
        gate = self.controller.safety_gate
        if gate is None:
            return set(movements)
        return gate.resolve_movements(set(movements), self.controller.ring, context=context)

    def _apply_phase_switch(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
    ) -> None:
        if self.baseline_green_seconds is not None:
            self._run_yellow()
            self._run_all_red()
            active = self.controller.advance_fixed_time()
            switch_context = "advance_fixed_time"
        else:
            if lane_totals is None:
                lane_totals = self._read_lane_totals()
            emg_arms, bus_arms = self._priority_arms_on_red()
            next_phase = self.controller.peek_next_phase(
                queues,
                self._arm_wait_times(),
                emergency_arms=emg_arms,
                transit_arms=bus_arms,
                priority_service=self.policy_config.priority_service,
                lane_totals=lane_totals,
            )
            overlap = self.controller.movements_overlap(
                self.controller.current_movements,
                set(next_phase.movements),
            )
            if not overlap:
                self._run_yellow()
                self._run_all_red()
            active = self.controller.advance(
                queues,
                self._arm_wait_times(),
                emergency_arms=emg_arms,
                transit_arms=bus_arms,
                priority_service=self.policy_config.priority_service,
                lane_totals=lane_totals,
            )
            switch_context = "advance_actuated"
        active = self._enforce_phase_safety(active, context=f"{switch_context}_tls")
        self._tls_state = build_tls_state(self.topology, active)
        traci.trafficlight.setRedYellowGreenState(self.tls_id, self._tls_state)
        self.time_since_last_switch = 0
        self._seconds_since_green_detection = 0.0

    def step(self, action):
        queues = self._read_queues()
        lane_totals = self._read_lane_totals()
        self._sync_controller_phase_duration()
        requested = int(action)
        invalid = False
        applied = requested
        switched = False
        depart_idx = self.controller.ring_index
        depart_phase_id = self.controller.current_phase_id
        mask = self._action_mask(queues, lane_totals)

        if self.baseline_green_seconds is not None:
            if self._switch_required(queues, lane_totals) and self._switch_allowed(queues):
                self._apply_phase_switch(queues, lane_totals)
                switched = True
                applied = 1
            else:
                applied = 0
        else:
            min_switch = self.controller.min_green_time
            if requested == 1 and self.time_since_last_switch >= min_switch:
                applied = 1
                invalid = False
            elif mask[1] and not mask[0]:
                applied = 1
                invalid = requested == 0
            elif not mask[1]:
                applied = 0
                invalid = requested == 1
            else:
                applied = requested

            if applied == 1 and not invalid:
                self._apply_phase_switch(queues, lane_totals)
                switched = True
            self._record_step_action(mask, applied)

        if switched and self.log_phase_tracker:
            incoming_idx = self.controller.ring_index
            incoming_phase_id = self.controller.current_phase_id
            light_state = traci.trafficlight.getRedYellowGreenState(self.tls_id)
            print(
                f"[PHASE_TRACKER] t={self.sim_time} | "
                f"Phase {depart_idx} ({depart_phase_id}) -> {incoming_idx} ({incoming_phase_id}) | "
                f"Lights: {light_state} | Mask: {mask} | Action: {requested}",
                flush=True,
            )

        self._phase_switched_this_step = switched
        self._last_invalid_action = invalid
        self._simulate_steps(self.step_length)

        state = self._get_state()
        reward, reward_components = self._compute_reward()
        self._record_reward_components(reward_components)
        done = traci.simulation.getMinExpectedNumber() <= 0
        truncated = False
        ended_reason = ""
        post_queues = self._read_queues()
        if self.end_when_clear:
            should_end, ended_reason = self._episode_tracker.check_after_step(
                sim_time=self.sim_time,
                total_queue=self._total_approach_queue(),
                active_vehicle_ids=self._active_vehicle_ids(),
            )
            if should_end:
                truncated = True
        post_lane_totals = self._read_lane_totals()
        next_mask = self._action_mask(post_queues, post_lane_totals)
        timing = self._green_timing_snapshot(post_queues)
        post_flow = self._green_flow_snapshot()
        if self.baseline_green_seconds is None:
            self._tick_green_gap_timer(post_flow.detection_occupied)
            self._platoon_active_prev_step = self.controller.platoon_active(post_flow)
        info = {
            "reward_components": reward_components,
            "action_requested": requested,
            "action_applied": applied,
            "action_mask": next_mask,
            "invalid_action": invalid,
            "phase_switched": switched,
            "time_in_phase": self.time_since_last_switch,
            "phase": self.controller.current_phase_id,
            "emergency_active": self._emergency_active,
            "priority_next_arm": self._deferred_priority_next_arm(post_queues),
            "effective_min_green": timing["effective_min_green"],
            "required_green_time": timing["required_time"],
            "cars_in_green": timing["cars_in_green"],
            "platoon_active": self.controller.platoon_active(post_flow),
            "gap_sufficient": self.controller.gap_sufficient(post_flow),
            "advance_flow_blocked": self.controller.advance_blocked_for_flow(
                post_queues,
                post_flow,
                time_in_phase=float(self.time_since_last_switch),
                max_green_seconds=self._effective_max_green(),
            )
            if self.baseline_green_seconds is None
            else False,
            "competing_demand": self.controller.competing_phase_demand(post_queues),
            "max_competing_red_wait": post_flow.max_competing_red_wait,
            "starvation_override_active": self.controller.starvation_override_active(post_flow),
            "seconds_since_detection": post_flow.seconds_since_detection,
            "sim_time": self.sim_time,
            "step_count": self._episode_tracker.state.step_count if self.end_when_clear else 0,
            "ended_reason": ended_reason,
            "episode_start_kind": self._episode_tracker.state.start_kind if self.end_when_clear else "",
        }

        if self.on_step and self.live_updates:
            self.on_step(self.get_live_snapshot())

        return state, reward, done, truncated, info

    def _baseline_hold_seconds(self, queues: dict[str, int]) -> float:
        """Fixed-time compare: full phase duration (60s thru, 25s left-only), no early gap-out."""
        return self._baseline_cap_seconds()

    def _emergency_waiting_on_red(self) -> bool:
        if self.baseline_green_seconds is not None:
            return False
        if not self.policy_config.priority_service.defer_emergency_to_next_green:
            return False
        emg_arms, _ = self._priority_arms_on_red()
        return bool(emg_arms)

    def _left_turn_waiting_on_red(self, queues: dict[str, int]) -> bool:
        if self.baseline_green_seconds is not None:
            return False
        if not self._green_stop_zone_empty():
            return False
        if self.controller._current_phase_serves_left():
            return False
        from flowgrid.core.intersection_graph import MovementType

        for mid, mov in self.topology.movements.items():
            if mov.kind != MovementType.LEFT:
                continue
            if mid in self.controller.current_movements:
                continue
            if int(queues.get(mid, 0)) >= self.controller.queue_threshold:
                return True
        return False

    def _green_lane_empty_other_arms_waiting(self, queues: dict[str, int]) -> bool:
        if self.baseline_green_seconds is not None:
            return False
        if not self._green_stop_zone_empty():
            return False
        red_queues = [
            int(self.controller.arm_demand(queues, arm))
            for arm in self.topology.arms
            if arm not in self.controller.green_arms()
        ]
        return max(red_queues, default=0) >= self._switch_min_vehicles

    def _instant_emergency_preempt(self) -> bool:
        return bool(self.policy_config.priority_service.instant_emergency_preempt)

    def _sync_controller_phase_duration(self) -> None:
        self.controller.current_phase_duration = float(self.time_since_last_switch)

    def _actuated_switch_floor(self) -> float:
        return self.controller.min_green_time

    def _switch_required(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
    ) -> bool:
        if lane_totals is None:
            lane_totals = self._read_lane_totals()
        self._sync_controller_phase_duration()
        if self.baseline_green_seconds is not None:
            return self.time_since_last_switch >= self._baseline_hold_seconds(queues)
        if self._emergency_active and self._instant_emergency_preempt():
            return True
        if self.max_green_seconds is not None and self.time_since_last_switch >= self.max_green_seconds:
            return True
        if self.time_since_last_switch > self.controller.max_green_time:
            return True
        if self.controller.should_skip_current(queues, lane_totals):
            return True
        floor = self._actuated_switch_floor()
        if self.time_since_last_switch >= floor and self._green_lane_empty_other_arms_waiting(queues):
            return True
        if self.time_since_last_switch >= floor and self._left_turn_waiting_on_red(queues):
            return True
        if self.time_since_last_switch >= floor and self._emergency_waiting_on_red():
            return True
        if self._should_force_switch_to_waiting(queues, floor, self._arm_wait_times(), lane_totals):
            return True
        return False

    def _effective_max_green(self) -> float:
        cap = self.controller.max_green_time
        if self.max_green_seconds is not None:
            return min(float(self.max_green_seconds), cap)
        return cap

    def _switch_allowed(self, queues: dict[str, int]) -> bool:
        if self.baseline_green_seconds is not None:
            return self.time_since_last_switch >= self._baseline_hold_seconds(queues)
        if self._emergency_active and self._instant_emergency_preempt():
            return True
        return self.time_since_last_switch >= self._actuated_switch_floor()

    def _action_mask(
        self,
        queues: dict[str, int],
        lane_totals: dict[str, int] | None = None,
    ) -> np.ndarray:
        if lane_totals is None:
            lane_totals = self._read_lane_totals()
        self._sync_controller_phase_duration()
        self._emergency_active = self._detect_emergency_arm() is not None
        required = self._switch_required(queues, lane_totals)
        allowed = self._switch_allowed(queues)
        if required:
            if allowed:
                return np.array([False, True], dtype=bool)
            return np.array([True, False], dtype=bool)
        if not allowed:
            return np.array([True, False], dtype=bool)
        return np.array([True, True], dtype=bool)

    def _run_yellow(self):
        yellow = build_all_yellow(self.topology, self._tls_state)
        traci.trafficlight.setRedYellowGreenState(self.tls_id, yellow)
        for _ in range(self.yellow_duration):
            traci.simulationStep()
            self.sim_time = traci.simulation.getTime()
            self.time_since_last_switch += 1
            self._accumulate_phase_second(1.0)

    def _run_all_red(self) -> None:
        if self.all_red_seconds <= 0:
            return
        all_red = build_all_red(self.topology)
        traci.trafficlight.setRedYellowGreenState(self.tls_id, all_red)
        for _ in range(self.all_red_seconds):
            traci.simulationStep()
            self.sim_time = traci.simulation.getTime()
            self._accumulate_phase_second(1.0)

    def _lane_queue_count(self, lane_id: str) -> int:
        try:
            halting = int(traci.lane.getLastStepHaltingNumber(lane_id))
            if halting > 0:
                return halting
            waiting = 0
            for vid in traci.lane.getLastStepVehicleIDs(lane_id):
                try:
                    if float(traci.vehicle.getWaitingTime(vid)) > 0.5:
                        waiting += 1
                    elif float(traci.vehicle.getSpeed(vid)) < 0.1:
                        waiting += 1
                except traci.exceptions.TraCIException:
                    continue
            return waiting
        except traci.exceptions.TraCIException:
            return 0

    def _read_queues(self) -> dict[str, int]:
        return self.controller.read_queues(self._lane_queue_count)

    def _lane_vehicle_total(self, lane_id: str) -> int:
        try:
            return int(traci.lane.getLastStepVehicleNumber(lane_id))
        except traci.exceptions.TraCIException:
            return 0

    def _read_lane_totals(self) -> dict[str, int]:
        return self.controller.read_lane_totals(self._lane_vehicle_total)

    def _distance_to_stop_line(self, lane_id: str, veh_id: str) -> float:
        try:
            return self._lane_length(lane_id) - float(traci.vehicle.getLanePosition(veh_id))
        except traci.exceptions.TraCIException:
            return float("inf")

    def _vehicle_in_camera_range(self, lane_id: str, veh_id: str) -> bool:
        return self._distance_to_stop_line(lane_id, veh_id) <= self.camera_range_meters

    def _vehicle_in_stop_line_zone(self, lane_id: str, veh_id: str) -> bool:
        return self._distance_to_stop_line(lane_id, veh_id) <= self.stop_line_zone_meters

    def _green_stop_zone_vehicle_count(self) -> int:
        count = 0
        for lane in self._green_movement_lanes():
            try:
                vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
            except traci.exceptions.TraCIException:
                continue
            for vid in vehicle_ids:
                if self._vehicle_in_stop_line_zone(lane, vid):
                    count += 1
        return count

    def _green_stop_zone_empty(self) -> bool:
        return self._green_stop_zone_vehicle_count() == 0

    def _observation_lane_halting_count(self, lane_id: str) -> int:
        count = 0
        try:
            vehicle_ids = traci.lane.getLastStepVehicleIDs(lane_id)
        except traci.exceptions.TraCIException:
            return 0
        for vid in vehicle_ids:
            if not self._vehicle_is_halted(vid):
                continue
            if self._vehicle_in_camera_range(lane_id, vid):
                count += 1
        return count

    def _read_observation_queues(self) -> dict[str, int]:
        return self.controller.read_queues(self._observation_lane_halting_count)

    def _observation_arm_wait_times(self) -> dict[str, float]:
        waits: dict[str, float] = {}
        for arm in self.topology.arms:
            total = 0.0
            for lane in self.lanes.get(arm, []):
                try:
                    vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
                except traci.exceptions.TraCIException:
                    continue
                for vid in vehicle_ids:
                    if not self._vehicle_in_camera_range(lane, vid):
                        continue
                    try:
                        total += float(traci.vehicle.getWaitingTime(vid))
                    except traci.exceptions.TraCIException:
                        continue
            waits[arm] = total
        return waits

    def _observation_transit_counts(self) -> dict[str, int]:
        counts = {arm: 0 for arm in ARMS}
        for arm in ARMS:
            for lane in self.lanes.get(arm, []):
                try:
                    vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
                except traci.exceptions.TraCIException:
                    continue
                for vid in vehicle_ids:
                    if not self._vehicle_in_camera_range(lane, vid):
                        continue
                    if self._is_transit_vehicle(vid):
                        counts[arm] += 1
        return counts

    def _arm_wait_times(self) -> dict[str, float]:
        waits: dict[str, float] = {}
        for arm in self.topology.arms:
            waits[arm] = sum(traci.lane.getWaitingTime(l) for l in self.lanes.get(arm, []))
        return waits

    def _transit_counts(self) -> dict[str, int]:
        counts = {arm: 0 for arm in ARMS}
        for arm in ARMS:
            for lane in self.lanes.get(arm, []):
                for vid in traci.lane.getLastStepVehicleIDs(lane):
                    if self._is_transit_vehicle(vid):
                        counts[arm] += 1
        return counts

    def _is_transit_vehicle(self, veh_id: str) -> bool:
        try:
            vclass = traci.vehicle.getVehicleClass(veh_id)
            if vclass in TRANSIT_VCLASS:
                return True
            type_id = traci.vehicle.getTypeID(veh_id).lower()
            return any(h in type_id for h in TRANSIT_TYPE_HINTS)
        except traci.exceptions.TraCIException:
            return False

    def _cars_in_green_phase(self) -> int:
        total = 0
        for mid in self.controller.current_movements:
            mov = self.topology.movements.get(mid)
            if not mov:
                continue
            for lane in self.topology.queue_lanes_for_movement(mov):
                try:
                    total += len(traci.lane.getLastStepVehicleIDs(lane))
                except traci.exceptions.TraCIException:
                    pass
        return total

    def _lane_length(self, lane_id: str) -> float:
        try:
            return max(float(traci.lane.getLength(lane_id)), 1.0)
        except traci.exceptions.TraCIException:
            return max(float(self.lane_lengths.get(lane_id, 1.0)), 1.0)

    def _vehicle_is_halted(self, veh_id: str) -> bool:
        try:
            if float(traci.vehicle.getWaitingTime(veh_id)) > 0.5:
                return True
            return float(traci.vehicle.getSpeed(veh_id)) < 0.1
        except traci.exceptions.TraCIException:
            return False

    def _vehicle_in_detection_zone(self, lane_id: str, veh_id: str) -> bool:
        try:
            length = self._lane_length(lane_id)
            pos = float(traci.vehicle.getLanePosition(veh_id))
            return pos >= 0.75 * length
        except traci.exceptions.TraCIException:
            return False

    def _tick_green_gap_timer(self, detection_occupied: bool) -> None:
        if detection_occupied:
            self._seconds_since_green_detection = 0.0
        else:
            self._seconds_since_green_detection += float(self.step_length)

    def _max_competing_red_wait(self) -> float:
        green = self.controller.green_arms()
        max_wait = 0.0
        for arm in self.topology.arms:
            if arm in green:
                continue
            for lane in self.lanes.get(arm, []):
                try:
                    vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
                except traci.exceptions.TraCIException:
                    continue
                for vid in vehicle_ids:
                    if not self._vehicle_is_halted(vid):
                        continue
                    try:
                        wait = float(traci.vehicle.getWaitingTime(vid))
                    except traci.exceptions.TraCIException:
                        continue
                    if wait > max_wait:
                        max_wait = wait
        return max_wait

    def _green_movement_lanes(self) -> list[str]:
        lanes: list[str] = []
        seen: set[str] = set()
        for mid in self.controller.current_movements:
            mov = self.topology.movements.get(mid)
            if not mov:
                continue
            for lane in self.topology.queue_lanes_for_movement(mov):
                if lane not in seen:
                    seen.add(lane)
                    lanes.append(lane)
        return lanes

    def _green_flow_snapshot(self) -> GreenFlowSnapshot:
        flow_threshold = float(self.controller.flow_speed_threshold)
        moving_count = 0
        detection_occupied = False
        upstream_queued = 0
        for lane in self._green_movement_lanes():
            try:
                vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
            except traci.exceptions.TraCIException:
                continue
            for vid in vehicle_ids:
                try:
                    speed = float(traci.vehicle.getSpeed(vid))
                except traci.exceptions.TraCIException:
                    continue
                in_zone = self._vehicle_in_detection_zone(lane, vid)
                if in_zone:
                    detection_occupied = True
                if speed >= flow_threshold:
                    moving_count += 1
                elif self._vehicle_is_halted(vid) and not in_zone:
                    upstream_queued += 1
        return GreenFlowSnapshot(
            moving_count=moving_count,
            detection_occupied=detection_occupied,
            upstream_queued=upstream_queued,
            seconds_since_detection=float(self._seconds_since_green_detection),
            max_competing_red_wait=self._max_competing_red_wait(),
        )

    def _min_green_cap(self) -> float:
        train_cap = (
            float(self.min_green_seconds)
            if self.min_green_seconds is not None
            else float(self.min_green_time)
        )
        cap_kind = self.controller.current_baseline_cap()
        if cap_kind == "left":
            return min(train_cap, float(self._resolved_baseline_left_seconds()))
        return train_cap

    def _resolved_baseline_left_seconds(self) -> int:
        return baseline_left_duration(
            self.baseline_through_seconds,
            self.baseline_left_to_through_ratio,
        )

    def _baseline_cap_seconds(self) -> float:
        cap_kind = self.controller.current_baseline_cap()
        if cap_kind == "left":
            return float(self._resolved_baseline_left_seconds())
        return float(self.baseline_through_seconds)

    def _dynamic_min_green_params(self) -> tuple[float, float, float]:
        c = self.policy_config.constraints
        safety = float(c.absolute_safety_min_seconds)
        sec_per_car = float(c.sec_per_car)
        base_min_green = self._min_green_cap()
        return safety, sec_per_car, base_min_green

    def _effective_min_green(self, queues: dict[str, int] | None = None) -> float:
        safety, sec_per_car, base_min_green = self._dynamic_min_green_params()
        cars = self._cars_in_green_phase()
        required_time = float(cars) * sec_per_car
        dynamic = max(safety, min(base_min_green, required_time))
        absolute = self.controller.absolute_min_green_seconds()
        return max(dynamic, absolute, self.controller.min_green_time)

    def _green_timing_snapshot(self, queues: dict[str, int] | None = None) -> dict[str, float]:
        safety, sec_per_car, base_min_green = self._dynamic_min_green_params()
        cars = float(self._cars_in_green_phase())
        required_time = cars * sec_per_car
        dynamic = max(safety, min(base_min_green, required_time))
        absolute = self.controller.absolute_min_green_seconds()
        effective = max(dynamic, absolute, self.controller.min_green_time)
        return {
            "cars_in_green": cars,
            "required_time": required_time,
            "effective_min_green": effective,
            "absolute_safety_min": safety,
            "absolute_phase_min": absolute,
            "sec_per_car": sec_per_car,
            "base_min_green": base_min_green,
            "time_in_phase": float(self.time_since_last_switch),
        }

    def _should_force_switch_to_waiting(
        self,
        queues: dict[str, int],
        dynamic_floor: float,
        arm_waits: dict[str, float],
        lane_totals: dict[str, int] | None = None,
    ) -> bool:
        if self.time_since_last_switch < dynamic_floor:
            return False
        if self.controller.should_hold_green_for_bulk(queues):
            return False
        if not self._green_stop_zone_empty():
            return False
        if lane_totals is None:
            lane_totals = self._read_lane_totals()
        nxt = self.controller._next_phase_in_rotation(queues, lane_totals)
        if nxt is None or nxt.id == self.controller.current_phase_id:
            return False
        return self.controller._phase_has_vehicle_presence(nxt, lane_totals)

    def _is_emergency_vehicle(self, veh_id: str) -> bool:
        try:
            if traci.vehicle.getVehicleClass(veh_id) == "emergency":
                return True
            return traci.vehicle.getTypeID(veh_id) == "emergency"
        except traci.exceptions.TraCIException:
            return False

    def emergency_vehicle_ids(self) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for lanes in self.lanes.values():
            for lane in lanes:
                try:
                    for veh_id in traci.lane.getLastStepVehicleIDs(lane):
                        if veh_id not in seen and self._is_emergency_vehicle(veh_id):
                            seen.add(veh_id)
                            ids.append(veh_id)
                except traci.exceptions.TraCIException:
                    continue
        return ids

    def total_emergency_waiting_time(self) -> float:
        total = 0.0
        for veh_id in self.emergency_vehicle_ids():
            try:
                total += traci.vehicle.getWaitingTime(veh_id)
            except traci.exceptions.TraCIException:
                continue
        return total

    def transit_vehicle_ids(self) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for lanes in self.lanes.values():
            for lane in lanes:
                try:
                    for veh_id in traci.lane.getLastStepVehicleIDs(lane):
                        if veh_id not in seen and self._is_transit_vehicle(veh_id):
                            seen.add(veh_id)
                            ids.append(veh_id)
                except traci.exceptions.TraCIException:
                    continue
        return ids

    def total_transit_waiting_time(self) -> float:
        total = 0.0
        for veh_id in self.transit_vehicle_ids():
            try:
                total += traci.vehicle.getWaitingTime(veh_id)
            except traci.exceptions.TraCIException:
                continue
        return total

    def _detect_emergency_arm(self):
        for arm in self.topology.arms:
            for lane in self.lanes.get(arm, []):
                for veh_id in traci.lane.getLastStepVehicleIDs(lane):
                    if self._is_emergency_vehicle(veh_id):
                        return arm
        return None

    def _priority_arms_on_red(self) -> tuple[frozenset[str], frozenset[str]]:
        """Arms with bus or emergency waiting while not currently green."""
        green = self.controller.green_arms()
        emergency: set[str] = set()
        transit: set[str] = set()
        for arm in self.topology.arms:
            if arm in green:
                continue
            for lane in self.lanes.get(arm, []):
                try:
                    vids = traci.lane.getLastStepVehicleIDs(lane)
                except traci.exceptions.TraCIException:
                    continue
                for veh_id in vids:
                    if self._is_emergency_vehicle(veh_id):
                        emergency.add(arm)
                    elif self._is_transit_vehicle(veh_id):
                        transit.add(arm)
        return frozenset(emergency), frozenset(transit)

    def _deferred_priority_next_arm(self, queues: dict[str, int]) -> str | None:
        emg, bus = self._priority_arms_on_red()
        return self.controller._pick_deferred_priority_arm(
            queues,
            self._arm_wait_times(),
            emg,
            bus,
            self.policy_config.priority_service,
        )

    def enable_departure_recording(
        self,
        departures: list,
        seen_ids: set[str],
        flow_meta: dict | None = None,
    ) -> None:
        """Record each vehicle at insert time (compare baseline); see compare_replay."""
        self._departure_recorder = (departures, seen_ids, flow_meta or {})

    def disable_departure_recording(self) -> None:
        self._departure_recorder = None

    def _simulate_steps(self, n_steps):
        for _ in range(n_steps):
            if self._departure_recorder is not None:
                from flowgrid.eval.compare_replay import capture_departed_micro_step

                capture_departed_micro_step(*self._departure_recorder)
            traci.simulationStep()
            self.sim_time = traci.simulation.getTime()
            self.time_since_last_switch += 1
            self._accumulate_phase_second(1.0)

    def total_waiting_time(self) -> float:
        return self._total_waiting_time()

    def _total_waiting_time(self) -> float:
        total = 0.0
        for lanes in self.lanes.values():
            for lane in lanes:
                total += traci.lane.getWaitingTime(lane)
        return total

    def _delay_delta_for_reward(self) -> float:
        """All vehicles count equally; buses/emergency add optional extra weight on their delta."""
        rw = self.policy_config.reward
        total_wait = self._total_waiting_time()
        transit_wait = self.total_transit_waiting_time()
        emergency_wait = self.total_emergency_waiting_time()

        base_delta = total_wait - self._prev_wait
        transit_delta = transit_wait - self._prev_transit_wait
        emergency_delta = emergency_wait - self._prev_emergency_wait

        self._prev_wait = total_wait
        self._prev_transit_wait = transit_wait
        self._prev_emergency_wait = emergency_wait

        return (
            base_delta
            + rw.transit_priority_scale * transit_delta
            + rw.emergency_priority_scale * emergency_delta
        )

    def _get_state(self):
        obs_queues = self._read_observation_queues()
        full_queues = self._read_queues()
        max_q = 20.0
        max_transit = 8.0
        mov_features = [min(obs_queues.get(mid, 0) / max_q, 1.0) for mid in sorted(self.topology.movements.keys())]
        arm_empty = [1.0 if self.controller.is_arm_empty(obs_queues, arm) else 0.0 for arm in ARMS]
        green = self.controller.green_arms()
        arm_waits = self._observation_arm_wait_times()
        arm_red_wait = [
            0.0 if arm in green else min(arm_waits.get(arm, 0.0) / 120.0, 1.0) for arm in ARMS
        ]
        floor = self._effective_min_green(full_queues)
        cap = self._min_green_cap()
        time_norm = [min(self.time_since_last_switch / max(floor * 2.0, cap, 30.0), 1.0)]
        emergency_flag = [1.0 if self._emergency_active else 0.0]
        transit = self._observation_transit_counts()
        transit_norm = [min(transit.get(arm, 0) / max_transit, 1.0) for arm in ARMS]
        return np.array(
            mov_features + arm_empty + arm_red_wait + time_norm + emergency_flag + transit_norm,
            dtype=np.float32,
        )

    def _compute_reward(self) -> tuple[float, dict[str, float]]:
        rw = self.policy_config.reward
        delay_delta = self._delay_delta_for_reward()
        exp_wait_cap = 5.0
        progressive_cap = -500.0
        fairness_floor = -max(500.0, float(rw.fairness_cap))

        spillback = 0.0
        for lanes in self.lanes.values():
            for lane in lanes:
                if traci.lane.getLastStepHaltingNumber(lane) * 5.0 >= self.lane_lengths[lane]:
                    spillback += rw.spillback_penalty

        arrived = int(traci.simulation.getArrivedNumber())
        cleared = max(0, arrived - self._prev_arrived)
        self._prev_arrived = arrived

        queues = self._read_queues()
        green = self.controller.green_arms()
        threshold = int(self.controller.queue_threshold)
        current_demand = self.controller.current_phase_demand(queues)
        max_red_q = max(
            (int(self.controller.arm_demand(queues, arm)) for arm in self.topology.arms if arm not in green),
            default=0,
        )

        wait_tau = max(8.0, float(rw.inactive_wait_threshold) / 4.0)
        red_wait_weight = abs(rw.inactive_wait_weight) * 6.0
        progressive_red_wait = 0.0
        for arm in self.topology.arms:
            if arm in green:
                continue
            for lane in self.lanes.get(arm, []):
                try:
                    vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
                except traci.exceptions.TraCIException:
                    continue
                for vid in vehicle_ids:
                    try:
                        wait = float(traci.vehicle.getWaitingTime(vid))
                    except traci.exceptions.TraCIException:
                        continue
                    if wait > 0.0:
                        progressive_red_wait -= red_wait_weight * float(
                            np.expm1(min(wait / wait_tau, exp_wait_cap))
                        )
        progressive_red_wait = max(progressive_cap, progressive_red_wait)

        arm_waits = []
        for arm in self.topology.arms:
            arm_waits.append(sum(traci.lane.getWaitingTime(l) for l in self.lanes.get(arm, [])))
        inactive_wait = sum(
            arm_waits[i] for i, arm in enumerate(self.topology.arms) if arm not in green
        )

        fairness = 0.0
        if arm_waits:
            fairness += rw.fairness_imbalance_weight * (max(arm_waits) - min(arm_waits))
            peak_wait = max(arm_waits)
            starving_arms = sum(1 for w in arm_waits if w > peak_wait * 0.25 and w > 0.0)
            if starving_arms:
                fairness += rw.starving_arms_weight * float(starving_arms) * 3.0

        starvation_queue = 0.0
        if max_red_q >= threshold:
            starvation_queue += rw.starving_arms_weight * (float(max_red_q) ** 1.35) * 2.5
        if current_demand < threshold and max_red_q >= threshold:
            starvation_queue += rw.starving_arms_weight * float(max_red_q) * 5.0
        starvation_queue = max(fairness_floor, starvation_queue)

        inactive_penalty = 0.0
        if (
            inactive_wait > rw.inactive_wait_threshold
            and current_demand < threshold
            and not self.controller.should_hold_green_for_bulk(queues)
        ):
            inactive_ratio = min(inactive_wait / max(wait_tau * 2.0, 1.0), exp_wait_cap)
            inactive_penalty -= inactive_wait * abs(rw.inactive_wait_weight) * float(np.expm1(inactive_ratio))
        inactive_penalty = max(fairness_floor, inactive_penalty)

        throughput_scale = 1.0 / (1.0 + 0.35 * max(0, max_red_q - threshold + 1))
        throughput = rw.throughput_per_vehicle * cleared * throughput_scale

        switch_cost = rw.switch_penalty if self.time_since_last_switch == 0 else 0.0
        platoon_interrupt = 0.0
        if self._phase_switched_this_step and self._platoon_active_prev_step:
            platoon_interrupt = rw.platoon_interrupt_penalty
        consecutive_clear = 0.0
        if cleared > 0:
            streak_mult = min(1.0 + 0.1 * float(self._consecutive_clears_since_switch), 3.0)
            consecutive_clear = rw.consecutive_clear_bonus * float(cleared) * streak_mult
            self._consecutive_clears_since_switch += cleared
        if self._phase_switched_this_step:
            self._consecutive_clears_since_switch = 0
        delay_term = -rw.delay_delta_scale * delay_delta
        network_wait = self._total_waiting_time()
        total_wait_term = -rw.total_wait_scale * network_wait
        try:
            fleet_size = len(traci.vehicle.getIDList())
        except traci.exceptions.TraCIException:
            fleet_size = self._prev_fleet_size
        fleet_drop = max(0, self._prev_fleet_size - fleet_size)
        self._prev_fleet_size = fleet_size
        drain_term = rw.drain_bonus_per_vehicle * cleared + rw.drain_bonus_fleet_drop * fleet_drop
        invalid_term = rw.invalid_action_penalty if self._last_invalid_action else 0.0

        fairness_total = max(fairness_floor, fairness + starvation_queue + inactive_penalty)

        components = {
            "spillback": spillback,
            "delay_delta": delay_term,
            "total_wait": total_wait_term,
            "drain_bonus": drain_term,
            "throughput": throughput,
            "progressive_red_wait": progressive_red_wait,
            "fairness": fairness_total,
            "starvation_queue": starvation_queue,
            "inactive_penalty": inactive_penalty,
            "switch": switch_cost,
            "platoon_interrupt": platoon_interrupt,
            "consecutive_clear": consecutive_clear,
            "invalid_action": invalid_term,
        }
        total = sum(components.values())
        return total, components

    def _vehicles_for_view(self) -> list[dict]:
        if not self.live_updates:
            return []
        vehicles = []
        for arm in ARMS:
            for lane in self.lanes.get(arm, []):
                try:
                    length = max(traci.lane.getLength(lane), 1.0)
                except traci.exceptions.TraCIException:
                    continue
                for vid in traci.lane.getLastStepVehicleIDs(lane):
                    try:
                        pos = traci.vehicle.getLanePosition(vid) / length
                        waiting = traci.vehicle.getWaitingTime(vid) > 0.5
                    except traci.exceptions.TraCIException:
                        continue
                    vehicles.append(
                        {
                            "id": vid,
                            "arm": arm,
                            "lane": lane,
                            "t": float(pos),
                            "waiting": waiting,
                        }
                    )
        return vehicles

    def get_live_snapshot(self):
        queues = self._read_queues()
        arms = {}
        for arm in ARMS:
            mov_th = self.topology.movements[f"{arm}_TH"]
            mov_lt = self.topology.movements[f"{arm}_LT"]
            thru_lanes = self.topology.queue_lanes_for_movement(mov_th)
            left_lanes = self.topology.queue_lanes_for_movement(mov_lt)
            queue_straight = sum(self._lane_queue_count(lane) for lane in thru_lanes)
            wait_straight = sum(float(traci.lane.getWaitingTime(lane)) for lane in thru_lanes)
            left_lane = left_lanes[0] if left_lanes else ""
            arms[arm] = {
                "queue_straight": queue_straight,
                "queue_left": sum(self._lane_queue_count(lane) for lane in left_lanes),
                "wait_straight": int(wait_straight),
                "wait_left": int(sum(float(traci.lane.getWaitingTime(lane)) for lane in left_lanes)),
                "signal_straight": approach_signal(self._tls_state, arm, "straight", self.topology),
                "signal_left": approach_signal(self._tls_state, arm, "left", self.topology),
                "opposite_empty": self.controller.is_arm_empty(queues, self.topology.opposing.get(arm, "")),
                "transit_count": self._transit_counts().get(arm, 0),
            }

        movements = {}
        for arm in ARMS:
            mov_th = self.topology.movements[f"{arm}_TH"]
            mov_lt = self.topology.movements[f"{arm}_LT"]
            thru_lanes = self.topology.queue_lanes_for_movement(mov_th)
            left_lanes = self.topology.queue_lanes_for_movement(mov_lt)
            thru_lane_a = thru_lanes[0] if thru_lanes else ""
            movements[f"{arm}_straight"] = {
                "signal": movement_signal(self._tls_state, thru_lane_a, self.topology),
                "queue": queues.get(f"{arm}_TH", 0),
            }
            left_lane = left_lanes[0] if left_lanes else ""
            movements[f"{arm}_left"] = {
                "signal": movement_signal(self._tls_state, left_lane, self.topology),
                "queue": queues.get(f"{arm}_LT", 0),
            }

        return {
            "phase": self.controller.current_phase_id.replace("_", " "),
            "phase_description": self.controller.last_description,
            "phase_index": self.controller.ring_index,
            "sim_time": self.sim_time,
            "time_in_phase": self.time_since_last_switch,
            "active_movements": sorted(self.controller.current_movements),
            "queue_lengths": {a: arms[a]["queue_straight"] + arms[a]["queue_left"] for a in arms},
            "wait_times": {a: int(arms[a]["wait_straight"] + arms[a]["wait_left"]) for a in arms},
            "arms": arms,
            "movements": movements,
            "vehicles": self._vehicles_for_view(),
            "emergency_active": self._emergency_active,
        }

    def close(self):
        self._traci_active = False
        try:
            traci.close(wait=True)
        except traci.exceptions.FatalTraCIError:
            pass
        except Exception:
            pass
