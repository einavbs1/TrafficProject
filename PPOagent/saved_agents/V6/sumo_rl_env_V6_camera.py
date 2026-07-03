"""
V6 Camera Architecture: diff_waiting_time + starvation penalty + 100m camera range.

Changes from V6:
    V6:        demand/starvation computed from ALL vehicles in the lane.
    V6_camera: demand/starvation computed only from vehicles within
               CAMERA_RANGE (100m) of the stop line.

Changes from V4:
    Reward: diff_waiting_time - starvation_penalty  (same as V6)
    Obs:    camera-limited demand + starvation       (new vs V6)

Why camera range:
    Real detectors/cameras only cover the near-intersection queue.
    Full-lane visibility gave the agent noisy, misleading demand signals
    for vehicles far from the intersection that won't arrive for many steps.
    Limiting to 100m gives a cleaner, more actionable observation.

Why starvation penalty:
    diff_waiting_time is ~0 in sparse (low) traffic -- the agent gets no
    gradient signal and locks onto one direction, causing catastrophic starvation.
    The penalty fires the moment any vehicle starts waiting:
        starvation_score[group] = max_wait_in_group / 90s, capped 1.0
        penalty = max(starvation_scores) * 0.05
    Non-zero gradient every step a vehicle exists, even in sparse traffic.

Reward is computed from full ground truth (all lanes, all vehicles) even though
observation is camera-limited. This is standard POMDP design: full-state reward,
partial observation.
"""

import os
import sys
import random
import gymnasium as gym
from gymnasium import spaces
import numpy as np

if "SUMO_HOME" not in os.environ:
    os.environ["SUMO_HOME"] = r"C:\Program Files (x86)\Eclipse\Sumo"

import sumo_rl
from sumo_rl.environment.observations import ObservationFunction
from sumo_rl.environment.traffic_signal import TrafficSignal


def dummy_reward(traffic_signal):
    return 0.0


class DummyObservationFunction(ObservationFunction):
    def __init__(self, ts):
        super().__init__(ts)

    def __call__(self) -> np.ndarray:
        return np.zeros(1, dtype=np.float32)

    def observation_space(self) -> spaces.Box:
        return spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)


def create_sumo_env(net_file, route_file, use_gui=False, out_csv_name=None, sumo_seed="random"):
    if not use_gui:
        os.environ["LIBSUMO_AS_TRACI"] = "1"
    elif "LIBSUMO_AS_TRACI" in os.environ:
        del os.environ["LIBSUMO_AS_TRACI"]

    env = sumo_rl.SumoEnvironment(
        net_file=net_file,
        route_file=route_file,
        use_gui=use_gui,
        out_csv_name=out_csv_name,
        sumo_seed=sumo_seed,
        reward_fn=dummy_reward,
        observation_class=DummyObservationFunction,
        time_to_teleport=-1,
        yellow_time=3,
        min_green=10,
        max_green=60,
        delta_time=5,
        single_agent=True
    )
    return env


class MultiRouteWrapper(gym.Wrapper):
    def __init__(self, env, route_files):
        super().__init__(env)
        self.route_files = route_files

    def reset(self, **kwargs):
        if self.route_files and isinstance(self.route_files, list):
            self.unwrapped._route = random.choice(self.route_files)
        return self.env.reset(**kwargs)


class SwitchOrKeepWrapper(gym.Wrapper):

    PHASE_NAMES = ["N/S Left", "N/S Straight", "E/W Left", "E/W Straight"]

    STANDARD_STATES = {
        0: "grrGgrrrgrrGgrrr",
        1: "gGGrgrrrgGGrgrrr",
        2: "grrrgrrGgrrrgrrG",
        3: "grrrgGGrgrrrgGGr",
    }

    OVERLAP_STATES = {
        (0, "north_only"): "gGGGgrrrgrrrgrrr",
        (0, "south_only"): "grrrgrrrgGGGgrrr",
        (2, "east_only"):  "grrrgGGGgrrrgrrr",
        (2, "west_only"):  "grrrgrrrgrrrgGGG",
    }

    LEFT_LANES = {
        "north": "n_to_center_3",
        "south": "s_to_center_3",
        "east":  "e_to_center_3",
        "west":  "w_to_center_3",
    }

    STRAIGHT_LANES = {
        "north": ["n_to_center_1", "n_to_center_2"],
        "south": ["s_to_center_1", "s_to_center_2"],
        "east":  ["e_to_center_1", "e_to_center_2"],
        "west":  ["w_to_center_1", "w_to_center_2"],
    }

    OBSERVATION_LANE_GROUPS = [
        ["n_to_center_3"],
        ["n_to_center_1", "n_to_center_2"],
        ["e_to_center_3"],
        ["e_to_center_1", "e_to_center_2"],
        ["s_to_center_3"],
        ["s_to_center_1", "s_to_center_2"],
        ["w_to_center_3"],
        ["w_to_center_1", "w_to_center_2"],
    ]

    STARVATION_THRESHOLD    = 90.0   # seconds until starvation score = 1.0
    STARVATION_PENALTY_COEF = 0.05   # penalty scale vs diff_waiting_time

    YELLOW_TIME = 3
    MIN_GREEN   = 10
    MAX_GREEN   = 60
    DELTA_TIME  = 5
    AVG_VEHICLE_LENGTH = 5.0

    CAMERA_RANGE = 100.0  # meters from stop line -- vehicles beyond this are invisible

    def __init__(self, env):
        super().__init__(env)
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(21,), dtype=np.float32)
        self.current_phase_index = 0
        self.current_state_string = self.STANDARD_STATES[0]
        self.elapsed_green_time = 0
        self._ts = None
        self._sumo = None
        self._prev_total_wait = 0.0
        self._max_starvation = 0.0

    def reset(self, **kwargs):
        _obs, info = self.env.reset(**kwargs)
        ts_id = list(self.unwrapped.traffic_signals.keys())[0]
        self._ts = self.unwrapped.traffic_signals[ts_id]
        self._sumo = self.unwrapped.sumo
        self.current_phase_index = 0
        self.elapsed_green_time = 0
        self._prev_total_wait = 0.0
        self._max_starvation = 0.0
        state = self._resolve_phase_state(0)
        if state is None:
            state = self._advance_to_next_valid_phase()
        self.current_state_string = state
        self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, self.current_state_string)
        return self._compute_observation(), info

    # --- Camera range filter -----------------------------------------------

    def _vehicles_in_range(self, lane):
        """Vehicle IDs on `lane` within CAMERA_RANGE meters of the stop line."""
        lane_length = self._ts.lanes_length.get(lane, 100.0)
        visible = []
        for veh_id in self._sumo.lane.getLastStepVehicleIDs(lane):
            try:
                pos = self._sumo.vehicle.getLanePosition(veh_id)
                if (lane_length - pos) <= self.CAMERA_RANGE:
                    visible.append(veh_id)
            except Exception:
                pass
        return visible

    def _vehicle_count_in_range(self, lane):
        return len(self._vehicles_in_range(lane))

    # --- Ghost Car Logic ---------------------------------------------------

    def _resolve_phase_state(self, phase_index):
        if phase_index == 0:
            n_left = self._vehicle_count_in_range(self.LEFT_LANES["north"])
            s_left = self._vehicle_count_in_range(self.LEFT_LANES["south"])
            if n_left == 0 and s_left == 0:
                return None
            elif n_left > 0 and s_left == 0:
                return self.OVERLAP_STATES[(0, "north_only")]
            elif s_left > 0 and n_left == 0:
                return self.OVERLAP_STATES[(0, "south_only")]
            else:
                return self.STANDARD_STATES[0]
        elif phase_index == 2:
            e_left = self._vehicle_count_in_range(self.LEFT_LANES["east"])
            w_left = self._vehicle_count_in_range(self.LEFT_LANES["west"])
            if e_left == 0 and w_left == 0:
                return None
            elif e_left > 0 and w_left == 0:
                return self.OVERLAP_STATES[(2, "east_only")]
            elif w_left > 0 and e_left == 0:
                return self.OVERLAP_STATES[(2, "west_only")]
            else:
                return self.STANDARD_STATES[2]
        elif phase_index == 1:
            n_str = sum(self._vehicle_count_in_range(l) for l in self.STRAIGHT_LANES["north"])
            s_str = sum(self._vehicle_count_in_range(l) for l in self.STRAIGHT_LANES["south"])
            return None if (n_str == 0 and s_str == 0) else self.STANDARD_STATES[1]
        elif phase_index == 3:
            e_str = sum(self._vehicle_count_in_range(l) for l in self.STRAIGHT_LANES["east"])
            w_str = sum(self._vehicle_count_in_range(l) for l in self.STRAIGHT_LANES["west"])
            return None if (e_str == 0 and w_str == 0) else self.STANDARD_STATES[3]

    def _advance_to_next_valid_phase(self):
        for _ in range(4):
            self.current_phase_index = (self.current_phase_index + 1) % 4
            state = self._resolve_phase_state(self.current_phase_index)
            if state is not None:
                return state
        self.current_phase_index = 1
        return self.STANDARD_STATES[1]

    def _compute_yellow_state(self, from_state, to_state):
        yellow = []
        for f, t in zip(from_state, to_state):
            if (f.lower() == 'g' or f.lower() == 'y') and t == 'r':
                yellow.append('y')
            else:
                yellow.append(f)
        return ''.join(yellow)

    def action_masks(self):
        can_keep = self.elapsed_green_time < self.MAX_GREEN
        can_switch = self.elapsed_green_time >= self.MIN_GREEN
        if not can_keep and not can_switch:
            can_keep = True
            can_switch = True
        return np.array([can_keep, can_switch], dtype=np.int8)

    def step(self, action):
        masks = self.action_masks()
        if not masks[action]:
            action = 1 - action

        if action == 1:
            old_state = self.current_state_string
            new_state = self._advance_to_next_valid_phase()
            yellow_state = self._compute_yellow_state(old_state, new_state)
            self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, yellow_state)
            for _ in range(self.YELLOW_TIME):
                self._sumo.simulationStep()
            self.current_state_string = new_state
            self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, new_state)
            remaining = self.DELTA_TIME - self.YELLOW_TIME
            for _ in range(remaining):
                self._sumo.simulationStep()
            self.elapsed_green_time = remaining
        else:
            self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, self.current_state_string)
            for _ in range(self.DELTA_TIME):
                self._sumo.simulationStep()
            self.elapsed_green_time += self.DELTA_TIME

        done = self._sumo.simulation.getTime() >= self.unwrapped.sim_max_time
        obs = self._compute_observation()   # sets self._max_starvation
        reward = self._compute_reward()     # reads self._max_starvation, no extra loop
        return obs, reward, False, done, {}

    def _compute_observation(self):
        """
        21-dim: [phase_onehot(4), elapsed(1), lane_demands(8), lane_starvation(8)]
        Demand and starvation only count vehicles within CAMERA_RANGE of stop line.
        self._max_starvation is cached here and reused in _compute_reward().
        """
        phase_onehot = [0.0, 0.0, 0.0, 0.0]
        phase_onehot[self.current_phase_index] = 1.0
        elapsed_norm = min(self.elapsed_green_time / float(self.MAX_GREEN), 1.0)
        lane_demands = []
        lane_starvation = []
        for lane_group in self.OBSERVATION_LANE_GROUPS:
            total_vehicles = 0
            total_capacity = 0.0
            max_wait_group = 0.0
            for lane in lane_group:
                visible_ids = self._vehicles_in_range(lane)
                total_vehicles += len(visible_ids)
                lane_length = self._ts.lanes_length.get(lane, 100.0)
                visible_length = min(lane_length, self.CAMERA_RANGE)
                total_capacity += visible_length / (TrafficSignal.MIN_GAP + self.AVG_VEHICLE_LENGTH)
                for veh_id in visible_ids:
                    try:
                        w = self._sumo.vehicle.getWaitingTime(veh_id)
                        if w > max_wait_group:
                            max_wait_group = w
                    except Exception:
                        pass
            demand = min(total_vehicles / max(total_capacity, 1.0), 1.0)
            lane_demands.append(demand)
            lane_starvation.append(min(max_wait_group / self.STARVATION_THRESHOLD, 1.0))
        self._max_starvation = max(lane_starvation) if lane_starvation else 0.0
        return np.array(phase_onehot + [elapsed_norm] + lane_demands + lane_starvation, dtype=np.float32)

    def _compute_reward(self):
        """
        V6 reward = diff_waiting_time - starvation_penalty (full ground truth).

        Reward uses ALL vehicles in ALL lanes (not camera-limited) because it
        reflects the true optimization objective -- we want to minimize real
        total wait, not just the visible portion.

        starvation_penalty reuses self._max_starvation set by _compute_observation()
        (camera-limited, but that is intentional: penalize based on what the
        agent CAN observe, so the gradient is coherent with the observation).
        """
        current_wait = sum(
            self._sumo.vehicle.getAccumulatedWaitingTime(v)
            for lane in self._ts.lanes
            for v in self._sumo.lane.getLastStepVehicleIDs(lane)
        )
        num_lanes = max(len(self._ts.lanes), 1)
        diff_wait = (self._prev_total_wait - current_wait) / num_lanes
        self._prev_total_wait = current_wait
        starvation_penalty = self._max_starvation * self.STARVATION_PENALTY_COEF
        return float(diff_wait - starvation_penalty)
