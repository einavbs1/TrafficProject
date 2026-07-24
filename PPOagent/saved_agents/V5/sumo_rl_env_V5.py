"""
V5 Architecture: Binary "Keep or Switch" Traffic Light Controller
================================================================

Identical to V4 except for the reward function.

V5 Reward â€” Pressure-based:
    reward = (halting_at_red - halting_at_green) / num_lanes
             - total_halting / num_lanes * 0.1

Why pressure instead of diff_waiting_time (V4):
    diff_waiting_time is nearly zero in low/sparse traffic â†’ near-zero gradient
    â†’ agent cannot learn in low-traffic episodes.

    Pressure uses halting vehicle COUNTS, not accumulated wait deltas.
    Even 1 halting vehicle in a red lane gives a clear non-zero gradient signal.
    The agent learns to clear green lanes and switch when red is backing up.
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


# =============================================================================
# BASE ENVIRONMENT SETUP
# =============================================================================

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


# =============================================================================
# CURRICULUM TRAINING WRAPPER
# =============================================================================

class MultiRouteWrapper(gym.Wrapper):
    def __init__(self, env, route_files):
        super().__init__(env)
        self.route_files = route_files

    def reset(self, **kwargs):
        if self.route_files and isinstance(self.route_files, list):
            self.unwrapped._route = random.choice(self.route_files)
        return self.env.reset(**kwargs)


# =============================================================================
# V5 WRAPPER: BINARY "KEEP OR SWITCH" WITH PRESSURE REWARD
# =============================================================================

class SwitchOrKeepWrapper(gym.Wrapper):
    """
    Same wrapper as V4 â€” only _compute_reward() is different.
    """

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

    # Which OBSERVATION_LANE_GROUPS indices are green for each phase
    GREEN_GROUPS = {
        0: [0, 4],   # Phase 0 (N/S Left):     N-left, S-left
        1: [1, 5],   # Phase 1 (N/S Straight): N-straight, S-straight
        2: [2, 6],   # Phase 2 (E/W Left):     E-left, W-left
        3: [3, 7],   # Phase 3 (E/W Straight): E-straight, W-straight
    }

    YELLOW_TIME = 3
    MIN_GREEN   = 10
    MAX_GREEN   = 60
    DELTA_TIME  = 5
    AVG_VEHICLE_LENGTH = 5.0

    def __init__(self, env):
        super().__init__(env)
        self.action_space = spaces.Discrete(2)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(21,), dtype=np.float32)
        self.current_phase_index = 0
        self.current_state_string = self.STANDARD_STATES[0]
        self.elapsed_green_time = 0
        self._ts = None
        self._sumo = None

    def reset(self, **kwargs):
        _obs, info = self.env.reset(**kwargs)
        ts_id = list(self.unwrapped.traffic_signals.keys())[0]
        self._ts = self.unwrapped.traffic_signals[ts_id]
        self._sumo = self.unwrapped.sumo
        self.current_phase_index = 0
        self.elapsed_green_time = 0
        state = self._resolve_phase_state(0)
        if state is None:
            state = self._advance_to_next_valid_phase()
        self.current_state_string = state
        self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, self.current_state_string)
        return self._compute_observation(), info

    def _resolve_phase_state(self, phase_index):
        if phase_index == 0:
            n_left = self._sumo.lane.getLastStepVehicleNumber(self.LEFT_LANES["north"])
            s_left = self._sumo.lane.getLastStepVehicleNumber(self.LEFT_LANES["south"])
            if n_left == 0 and s_left == 0:
                return None
            elif n_left > 0 and s_left == 0:
                return self.OVERLAP_STATES[(0, "north_only")]
            elif s_left > 0 and n_left == 0:
                return self.OVERLAP_STATES[(0, "south_only")]
            else:
                return self.STANDARD_STATES[0]
        elif phase_index == 2:
            e_left = self._sumo.lane.getLastStepVehicleNumber(self.LEFT_LANES["east"])
            w_left = self._sumo.lane.getLastStepVehicleNumber(self.LEFT_LANES["west"])
            if e_left == 0 and w_left == 0:
                return None
            elif e_left > 0 and w_left == 0:
                return self.OVERLAP_STATES[(2, "east_only")]
            elif w_left > 0 and e_left == 0:
                return self.OVERLAP_STATES[(2, "west_only")]
            else:
                return self.STANDARD_STATES[2]
        elif phase_index == 1:
            n_str = sum(self._sumo.lane.getLastStepVehicleNumber(l) for l in self.STRAIGHT_LANES["north"])
            s_str = sum(self._sumo.lane.getLastStepVehicleNumber(l) for l in self.STRAIGHT_LANES["south"])
            if n_str == 0 and s_str == 0:
                return None
            else:
                return self.STANDARD_STATES[1]
        elif phase_index == 3:
            e_str = sum(self._sumo.lane.getLastStepVehicleNumber(l) for l in self.STRAIGHT_LANES["east"])
            w_str = sum(self._sumo.lane.getLastStepVehicleNumber(l) for l in self.STRAIGHT_LANES["west"])
            if e_str == 0 and w_str == 0:
                return None
            else:
                return self.STANDARD_STATES[3]

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
        obs = self._compute_observation()
        reward = self._compute_reward()
        info = {"max_vehicle_wait_time": self._get_max_vehicle_wait()}
        return obs, reward, False, done, info

    def _compute_observation(self):
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
                total_vehicles += self._sumo.lane.getLastStepVehicleNumber(lane)
                lane_length = self._ts.lanes_length.get(lane, 100.0)
                total_capacity += lane_length / (TrafficSignal.MIN_GAP + self.AVG_VEHICLE_LENGTH)
                for veh_id in self._sumo.lane.getLastStepVehicleIDs(lane):
                    try:
                        w = self._sumo.vehicle.getWaitingTime(veh_id)
                        if w > max_wait_group:
                            max_wait_group = w
                    except Exception:
                        pass
            demand = min(total_vehicles / max(total_capacity, 1.0), 1.0)
            lane_demands.append(demand)
            lane_starvation.append(min(max_wait_group / 90.0, 1.0))
        return np.array(phase_onehot + [elapsed_norm] + lane_demands + lane_starvation, dtype=np.float32)

    def _compute_reward(self):
        """
        V5 Pressure reward.

        For each of the 8 lane groups, count vehicles that are halting (speed=0).
        Groups currently served by the green phase â†’ green_halting.
        All other groups â†’ red_halting.

        reward = (red_halting - green_halting) / num_lanes   â† pressure signal
                 - total_halting / num_lanes * 0.1            â† queue penalty

        Pressure is positive when red lanes have more queue than green (green phase
        is efficient â†’ keep or about to be done). Negative when green is backing up.
        Queue penalty shrinks with total queue size regardless of direction.

        Unlike diff_waiting_time, this is non-zero even with a single waiting vehicle,
        giving clear gradient in sparse (low) traffic.
        """
        green_groups = self.GREEN_GROUPS.get(self.current_phase_index, [])
        green_halting = 0
        red_halting = 0
        for i, lane_group in enumerate(self.OBSERVATION_LANE_GROUPS):
            for lane in lane_group:
                halting = self._sumo.lane.getLastStepHaltingNumber(lane)
                if i in green_groups:
                    green_halting += halting
                else:
                    red_halting += halting
        num_lanes = max(len(self._ts.lanes), 1)
        total_halting = green_halting + red_halting
        pressure = (red_halting - green_halting) / num_lanes
        queue_penalty = total_halting / num_lanes * 0.1
        return float(pressure - queue_penalty)

    def _get_max_vehicle_wait(self):
        max_wait = 0.0
        for lane in self._ts.lanes:
            for veh_id in self._sumo.lane.getLastStepVehicleIDs(lane):
                try:
                    wait = self._sumo.vehicle.getWaitingTime(veh_id)
                    if wait > max_wait:
                        max_wait = wait
                except Exception:
                    pass
        return max_wait

