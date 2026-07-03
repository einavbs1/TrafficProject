"""
V4.1 Architecture: Binary "Keep or Switch" Traffic Light Controller, camera-limited.

Change from V4:
    V4:   demand/starvation computed from ALL vehicles anywhere in the lane.
    V4.1: demand/starvation computed only from vehicles within CAMERA_RANGE (100m)
          of the stop line -- matches a real detector/camera's limited coverage
          instead of omniscient full-lane visibility.

    Ghost Car Logic (phase skip/overlap decisions) also uses the camera-filtered
    count, so the agent's phase-skipping behavior matches what it can "see".

    Reward (diff_waiting_time) is unchanged -- still computed from true full-lane
    state, since the reward reflects the real optimization objective even though
    the agent's observation is partial (POMDP-style: full-state reward, partial
    observation).

Action Space: Discrete(2) -- 0=Keep, 1=Switch
Phase Sequence: N/S Left -> N/S Straight -> E/W Left -> E/W Straight (hardcoded)

Features:
- Phase Overlap (Ghost Car Logic): If a left-turn phase has demand on only one
  side, that side gets both left AND straight green simultaneously.
- Phase Skipping: If a left-turn phase has zero demand on both sides, it's skipped.
- Custom Yellow Transitions: Computed character-by-character to handle overlaps safely.
- Action Masking: min_green forces Keep, max_green forces Switch.
- Diff-waiting-time reward: reward = (prev_total_wait - current_total_wait) / num_lanes
- 21-feature observation: [phase_onehot(4), elapsed(1), lane_demands(8), lane_starvation(8)]
  Demand and starvation only count vehicles within CAMERA_RANGE of the stop line.
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
# BASE ENVIRONMENT SETUP (minimal -- the wrapper handles everything)
# =============================================================================

def dummy_reward(traffic_signal):
    """Placeholder reward for the base env. Real reward is computed in the wrapper."""
    return 0.0


class DummyObservationFunction(ObservationFunction):
    """Minimal observation for the base env. The wrapper computes the real 13-dim observation."""
    def __init__(self, ts):
        super().__init__(ts)

    def __call__(self) -> np.ndarray:
        return np.zeros(1, dtype=np.float32)

    def observation_space(self) -> spaces.Box:
        return spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32)


def create_sumo_env(net_file, route_file, use_gui=False, out_csv_name=None, sumo_seed="random"):
    """Create the base SUMO environment. Must be wrapped with SwitchOrKeepWrapper."""
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
        time_to_teleport=-1,      # Disabled: no teleporting cheats
        yellow_time=3,
        min_green=10,
        max_green=60,
        delta_time=5,             # Agent decides every 5 simulation seconds
        single_agent=True
    )
    return env


# =============================================================================
# CURRICULUM TRAINING WRAPPER (unchanged from v2)
# =============================================================================

class MultiRouteWrapper(gym.Wrapper):
    """Randomly selects a new route file on reset for curriculum training."""
    def __init__(self, env, route_files):
        super().__init__(env)
        self.route_files = route_files

    def reset(self, **kwargs):
        if self.route_files and isinstance(self.route_files, list):
            self.unwrapped._route = random.choice(self.route_files)
        return self.env.reset(**kwargs)


# =============================================================================
# V3 WRAPPER: BINARY "KEEP OR SWITCH" WITH PHASE OVERLAP
# =============================================================================

class SwitchOrKeepWrapper(gym.Wrapper):
    """
    V3 Architecture wrapper. The AI only learns TIMING -- the phase sequence is
    hardcoded. At each decision step the agent chooses:
        Action 0 (Keep): Extend the current green phase by delta_time seconds.
        Action 1 (Switch): End current phase -> yellow -> advance to next phase.

    The wrapper manages:
    - Phase sequence pointer (cycles through 0->1->2->3->0...)
    - Ghost Car Logic (phase overlap when one left-turn direction is empty)
    - Phase skipping (skip left-turn phases with zero demand)
    - Custom yellow state computation (safe transitions between any state pair)
    - Action masking (min_green / max_green enforcement)
    - Reward computation (diff_waiting_time: decrease in accumulated wait per lane)
    - Observation computation (13-dim vector)

    It bypasses sumo_rl's internal phase management and directly controls SUMO's
    traffic light via setRedYellowGreenState(), stepping the simulation manually.
    """

    # --- Phase Configuration ---------------------------------------------
    PHASE_NAMES = ["N/S Left", "N/S Straight", "E/W Left", "E/W Straight"]

    # Standard green phase state strings (from network.net.xml)
    # 16 characters, one per link index (0-15). G=protected, g=permissive, r=red.
    #
    # Link mapping:
    #  0: N->W right    4: E->N right    8:  S->E right   12: W->S right
    #  1: N->S str L1   5: E->W str L1   9:  S->N str L1  13: W->E str L1
    #  2: N->S str L2   6: E->W str L2   10: S->N str L2  14: W->E str L2
    #  3: N->E left     7: E->S left     11: S->W left    15: W->N left
    STANDARD_STATES = {
        0: "grrGgrrrgrrGgrrr",   # N/S Left turns (N->E, S->W protected)
        1: "gGGrgrrrgGGrgrrr",   # N/S Straight   (N->S, S->N protected)
        2: "grrrgrrGgrrrgrrG",   # E/W Left turns (E->S, W->N protected)
        3: "grrrgGGrgrrrgGGr",   # E/W Straight   (E->W, W->E protected)
    }

    # Safe overlap states for left-turn phases (Ghost Car Logic)
    #
    # SAFETY RULE: Only combine left + straight from the SAME direction.
    # Opposite-direction straight is kept RED because it would conflict with
    # the left turn (classic left-turn vs oncoming through-traffic crash).
    #
    # Example: During "north_only" overlap, North gets left+straight green
    # but South stays red (except permissive right). This is safe because
    # N->E left and N->S straight both originate from the same approach.
    OVERLAP_STATES = {
        # Phase 0: N/S Left overlaps
        (0, "north_only"): "gGGGgrrrgrrrgrrr",  # N: left+straight, S: red
        (0, "south_only"): "grrrgrrrgGGGgrrr",  # S: left+straight, N: red
        # Phase 2: E/W Left overlaps
        (2, "east_only"):  "grrrgGGGgrrrgrrr",  # E: left+straight, W: red
        (2, "west_only"):  "grrrgrrrgrrrgGGG",  # W: left+straight, E: red
    }

    # --- Lane Names ------------------------------------------------------

    # Left-turn lanes for overlap demand detection
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

    # 8 controlled lane groups for the observation vector
    # Each group is [lane_names] for one movement direction.
    # Right-turn lanes excluded (they're always permissive green).
    OBSERVATION_LANE_GROUPS = [
        ["n_to_center_3"],                       # N-left
        ["n_to_center_1", "n_to_center_2"],      # N-straight (2 lanes combined)
        ["e_to_center_3"],                       # E-left
        ["e_to_center_1", "e_to_center_2"],      # E-straight
        ["s_to_center_3"],                       # S-left
        ["s_to_center_1", "s_to_center_2"],      # S-straight
        ["w_to_center_3"],                       # W-left
        ["w_to_center_1", "w_to_center_2"],      # W-straight
    ]

    # --- Timing Constants ------------------------------------------------
    YELLOW_TIME = 3    # seconds of yellow before new green
    MIN_GREEN   = 10   # minimum green time before switching is allowed
    MAX_GREEN   = 60   # maximum green time before switching is forced
    DELTA_TIME  = 5    # simulation seconds per decision step

    # --- Physics ---------------------------------------------------------
    AVG_VEHICLE_LENGTH = 5.0  # meters, for lane capacity estimation

    # --- Camera Range ------------------------------------------------------
    # Only vehicles within this distance of the stop line are visible to the
    # agent (detection range), matching real loop-detector / camera coverage
    # instead of seeing the entire lane regardless of length.
    CAMERA_RANGE = 100.0  # meters

    def __init__(self, env):
        super().__init__(env)

        # Override the action and observation spaces for SB3
        self.action_space = spaces.Discrete(2)   # 0=Keep, 1=Switch
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(21,), dtype=np.float32
        )

        # Internal state (initialized properly in reset())
        self.current_phase_index = 0
        self.current_state_string = self.STANDARD_STATES[0]
        self.elapsed_green_time = 0
        self._ts = None     # TrafficSignal object (cached for performance)
        self._sumo = None   # SUMO connection (cached for performance)
        self._prev_total_wait = 0.0  # accumulated waiting time from previous step

    # --- Reset -----------------------------------------------------------

    def reset(self, **kwargs):
        # Let the base env restart SUMO and recreate traffic signal objects
        _obs, info = self.env.reset(**kwargs)

        # Cache references (updated each reset since SUMO restarts)
        ts_id = list(self.unwrapped.traffic_signals.keys())[0]
        self._ts = self.unwrapped.traffic_signals[ts_id]
        self._sumo = self.unwrapped.sumo

        # Initialize phase pointer to the start of the sequence
        self.current_phase_index = 0
        self.elapsed_green_time = 0
        self._prev_total_wait = 0.0

        # Apply Ghost Car Logic for the initial phase
        state = self._resolve_phase_state(0)
        if state is None:
            # First phase (N/S Left) has no demand -- find the first valid phase
            state = self._advance_to_next_valid_phase()
        self.current_state_string = state

        # Set the initial traffic light state in SUMO
        self._sumo.trafficlight.setRedYellowGreenState(
            self._ts.id, self.current_state_string
        )

        return self._compute_observation(), info

    # --- Camera Range Filter -----------------------------------------------

    def _vehicles_in_range(self, lane):
        """Return vehicle IDs on `lane` within CAMERA_RANGE meters of the stop line."""
        lane_length = self._ts.lanes_length.get(lane, 100.0)
        visible = []
        for veh_id in self._sumo.lane.getLastStepVehicleIDs(lane):
            try:
                pos = self._sumo.vehicle.getLanePosition(veh_id)
                if (lane_length - pos) <= self.CAMERA_RANGE:
                    visible.append(veh_id)
            except Exception:
                pass  # Vehicle may have left between queries
        return visible

    def _vehicle_count_in_range(self, lane):
        return len(self._vehicles_in_range(lane))

    # --- Ghost Car Logic -------------------------------------------------

    def _resolve_phase_state(self, phase_index):
        """
        Determine the actual state string for a phase, applying overlap logic.

        For left-turn phases (0, 2):
          - Both sides have cars -> standard left-turn phase
          - One side empty -> overlap: the other side gets left + straight
          - Both sides empty -> return None (skip this phase)

        For straight phases (1, 3):
          - Always use the standard state (never skipped)
        """
        if phase_index == 0:  # N/S Left
            n_left = self._vehicle_count_in_range(self.LEFT_LANES["north"])
            s_left = self._vehicle_count_in_range(self.LEFT_LANES["south"])
            if n_left == 0 and s_left == 0:
                return None  # Skip: no left-turn demand at all
            elif n_left > 0 and s_left == 0:
                return self.OVERLAP_STATES[(0, "north_only")]
            elif s_left > 0 and n_left == 0:
                return self.OVERLAP_STATES[(0, "south_only")]
            else:
                return self.STANDARD_STATES[0]

        elif phase_index == 2:  # E/W Left
            e_left = self._vehicle_count_in_range(self.LEFT_LANES["east"])
            w_left = self._vehicle_count_in_range(self.LEFT_LANES["west"])
            if e_left == 0 and w_left == 0:
                return None  # Skip: no left-turn demand at all
            elif e_left > 0 and w_left == 0:
                return self.OVERLAP_STATES[(2, "east_only")]
            elif w_left > 0 and e_left == 0:
                return self.OVERLAP_STATES[(2, "west_only")]
            else:
                return self.STANDARD_STATES[2]

        elif phase_index == 1:  # N/S Straight
            n_str = sum(self._vehicle_count_in_range(l) for l in self.STRAIGHT_LANES["north"])
            s_str = sum(self._vehicle_count_in_range(l) for l in self.STRAIGHT_LANES["south"])
            if n_str == 0 and s_str == 0:
                return None  # Skip: no straight demand at all
            else:
                return self.STANDARD_STATES[1]

        elif phase_index == 3:  # E/W Straight
            e_str = sum(self._vehicle_count_in_range(l) for l in self.STRAIGHT_LANES["east"])
            w_str = sum(self._vehicle_count_in_range(l) for l in self.STRAIGHT_LANES["west"])
            if e_str == 0 and w_str == 0:
                return None  # Skip: no straight demand at all
            else:
                return self.STANDARD_STATES[3]

    def _advance_to_next_valid_phase(self):
        """
        Advance the phase pointer forward, skipping any left-turn phases with
        no demand. Returns the resolved state string of the next valid phase.
        Tries up to 4 phases (a full cycle) to avoid infinite loops.
        """
        for _ in range(4):
            self.current_phase_index = (self.current_phase_index + 1) % 4
            state = self._resolve_phase_state(self.current_phase_index)
            if state is not None:
                return state
        # Fallback: every phase was empty (extremely unlikely), use N/S Straight
        self.current_phase_index = 1
        return self.STANDARD_STATES[1]

    # --- Custom Yellow Transition ----------------------------------------

    def _compute_yellow_state(self, from_state, to_state):
        """
        Calculate the safe yellow transition state between two state strings.
        Always relies on the Base Green Phase (from_state) to prevent mid-yellow
        transition bugs.

        Rules (applied per-character / per-link):
          - Green (G/g) or Yellow (y/Y) -> Red (r): show Yellow (y)
          - Otherwise: keep the base from-state character.
        """
        yellow = []
        for f, t in zip(from_state, to_state):
            # If the from-state (even if it was a yellow 'y') is transitioning to red, it must be yellow
            if (f.lower() == 'g' or f.lower() == 'y') and t == 'r':
                yellow.append('y')
            else:
                yellow.append(f)
        return ''.join(yellow)

    # --- Action Masking --------------------------------------------------

    def action_masks(self):
        """Return binary action mask [can_keep, can_switch]."""
        can_keep = self.elapsed_green_time < self.MAX_GREEN
        can_switch = self.elapsed_green_time >= self.MIN_GREEN

        if not can_keep and not can_switch:
            can_keep = True
            can_switch = True

        return np.array([can_keep, can_switch], dtype=np.int8)

    # --- Step ------------------------------------------------------------

    def step(self, action):
        """
        Execute one decision step (DELTA_TIME seconds of simulation).

        Action 0 (Keep): Re-assert current state, advance DELTA_TIME seconds.
        Action 1 (Switch): Yellow transition -> advance to next valid phase.
        """
        # Enforce action masks for safety (even if the agent/baseline violates them)
        masks = self.action_masks()
        if not masks[action]:
            action = 1 - action  # Flip to the only valid action

        if action == 1:  # -- SWITCH --
            old_state = self.current_state_string

            # Advance to the next valid phase (handles skipping + overlap)
            new_state = self._advance_to_next_valid_phase()

            # 1) Compute and apply yellow transition
            yellow_state = self._compute_yellow_state(old_state, new_state)
            self._sumo.trafficlight.setRedYellowGreenState(
                self._ts.id, yellow_state
            )

            # 2) Step through the yellow period (YELLOW_TIME seconds)
            for _ in range(self.YELLOW_TIME):
                self._sumo.simulationStep()

            # 3) Apply the new green state
            self.current_state_string = new_state
            self._sumo.trafficlight.setRedYellowGreenState(
                self._ts.id, new_state
            )

            # 4) Step through the remaining green time
            remaining = self.DELTA_TIME - self.YELLOW_TIME
            for _ in range(remaining):
                self._sumo.simulationStep()

            # Reset elapsed: the new green phase started after yellow
            self.elapsed_green_time = remaining

        else:  # -- KEEP --
            # Re-assert current state (prevents SUMO from drifting) and step
            self._sumo.trafficlight.setRedYellowGreenState(
                self._ts.id, self.current_state_string
            )
            for _ in range(self.DELTA_TIME):
                self._sumo.simulationStep()

            self.elapsed_green_time += self.DELTA_TIME

        # Check if the simulation has exceeded its time limit
        done = self._sumo.simulation.getTime() >= self.unwrapped.sim_max_time

        # Compute observation and reward
        obs = self._compute_observation()
        reward = self._compute_reward()

        # terminated=False (no terminal states), truncated=done (time limit)
        info = {"max_vehicle_wait_time": self._get_max_vehicle_wait()}
        return obs, reward, False, done, info

    # --- Observation -----------------------------------------------------

    def _compute_observation(self):
        """
        21-dimensional observation vector:

        [0:4]   Phase index      -- one-hot encoded (which of the 4 phases is active)
        [4]     Elapsed time     -- normalized by MAX_GREEN (0.0 to 1.0)
        [5:13]  Lane demands     -- 8 lane groups, each normalized by capacity (0.0 to 1.0)
                                   Order: N-left, N-str, E-left, E-str,
                                          S-left, S-str, W-left, W-str
        [13:21] Lane starvation  -- 8 lane groups, each = max consecutive wait of any
                                   vehicle in that group / 90.0, capped at 1.0.
                                   Gives the network explicit per-lane urgency signal
                                   so a single stranded car (demand≈0.05) is not ignored.

        Camera range: only vehicles within CAMERA_RANGE meters of the stop line
        are visible (both for demand counts and starvation), matching a
        real-world detector/camera with limited coverage instead of seeing
        the entire lane regardless of length.
        """
        # 1. Phase one-hot (4 dims)
        phase_onehot = [0.0, 0.0, 0.0, 0.0]
        phase_onehot[self.current_phase_index] = 1.0

        # 2. Elapsed time, normalized (1 dim)
        elapsed_norm = min(self.elapsed_green_time / float(self.MAX_GREEN), 1.0)

        # 3. Lane demands + starvation scores (8 + 8 dims computed together)
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
                total_capacity += visible_length / (
                    TrafficSignal.MIN_GAP + self.AVG_VEHICLE_LENGTH
                )
                for veh_id in visible_ids:
                    try:
                        w = self._sumo.vehicle.getWaitingTime(veh_id)
                        if w > max_wait_group:
                            max_wait_group = w
                    except Exception:
                        pass  # Vehicle may have left between queries
            demand = min(total_vehicles / max(total_capacity, 1.0), 1.0)
            lane_demands.append(demand)
            lane_starvation.append(min(max_wait_group / 90.0, 1.0))

        obs = np.array(
            phase_onehot + [elapsed_norm] + lane_demands + lane_starvation,
            dtype=np.float32
        )
        return obs

    # --- Reward ----------------------------------------------------------

    def _compute_reward(self):
        """
        Reward = decrease in accumulated waiting time per lane.
        Directly aligns training signal with the evaluation metric (total waiting time).
        Always <= 0; the agent maximises by minimising queue buildup each step.
        """
        current_wait = sum(
            self._sumo.vehicle.getAccumulatedWaitingTime(v)
            for lane in self._ts.lanes
            for v in self._sumo.lane.getLastStepVehicleIDs(lane)
        )
        num_lanes = max(len(self._ts.lanes), 1)
        reward = (self._prev_total_wait - current_wait) / num_lanes
        self._prev_total_wait = current_wait
        return float(reward)

    def _get_max_vehicle_wait(self):
        """
        Get the maximum CONSECUTIVE waiting time of any vehicle at the intersection.

        Uses SUMO's getWaitingTime() which returns the time a vehicle has been
        continuously stopped (resets when the vehicle moves). This is the correct
        metric for starvation detection -- it measures how long a driver has been
        stuck at a red light RIGHT NOW, not their total trip delay.
        """
        max_wait = 0.0
        for lane in self._ts.lanes:
            for veh_id in self._sumo.lane.getLastStepVehicleIDs(lane):
                try:
                    wait = self._sumo.vehicle.getWaitingTime(veh_id)
                    if wait > max_wait:
                        max_wait = wait
                except Exception:
                    pass  # Vehicle may have left between queries
        return max_wait




# =============================================================================
# V4 WRAPPER: ACYCLIC PHASE SELECTION
# =============================================================================

class AcyclicWrapper(SwitchOrKeepWrapper):
    """
    V4 Architecture: Discrete(4) Phase Selection.
    The agent directly selects which of the 4 phases it wants (0, 1, 2, or 3).
    - If action == current_phase: Keep Green.
    - If action != current_phase: Switch immediately via Yellow.
    """
    def __init__(self, env):
        # Call grand-parent init, skip SwitchOrKeepWrapper init which sets Discrete(2)
        gym.Wrapper.__init__(self, env)
        
        self.action_space = spaces.Discrete(4)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(21,), dtype=np.float32
        )

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
            self.current_phase_index = 1
            state = self.STANDARD_STATES[1]
            
        self.current_state_string = state
        self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, self.current_state_string)
        
        return self._compute_observation(), info

    def action_masks(self):
        masks = [True, True, True, True]
        
        total_queued = 0
        if self._ts is not None and self._sumo is not None:
            total_queued = sum(self._sumo.lane.getLastStepHaltingNumber(lane) for lane in self._ts.lanes)
            
        dynamic_min_green = self.MIN_GREEN
        if total_queued > 30:
            dynamic_min_green = 30
        elif total_queued > 10:
            dynamic_min_green = 20
        
        if self.elapsed_green_time < dynamic_min_green:
            masks = [False, False, False, False]
            masks[self.current_phase_index] = True
            
        if self.elapsed_green_time >= self.MAX_GREEN:
            masks[self.current_phase_index] = False
            
        for p in [0, 2]:
            if p != self.current_phase_index and self._resolve_phase_state(p) is None:
                masks[p] = False

        if not any(masks):
            masks[self.current_phase_index] = True
            
        return np.array(masks, dtype=np.int8)

    def step(self, action):
        masks = self.action_masks()
        if not masks[action]:
            valid_actions = np.where(masks)[0]
            if self.current_phase_index in valid_actions:
                action = self.current_phase_index
            else:
                action = valid_actions[0]

        if action == self.current_phase_index:
            self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, self.current_state_string)
            for _ in range(self.DELTA_TIME):
                self._sumo.simulationStep()
            self.elapsed_green_time += self.DELTA_TIME
        else:
            old_state = self.current_state_string
            new_state = self._resolve_phase_state(action)
            if new_state is None:
                new_state = self.STANDARD_STATES[action]

            yellow_state = self._compute_yellow_state(old_state, new_state)
            self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, yellow_state)
            for _ in range(self.YELLOW_TIME):
                self._sumo.simulationStep()

            self.current_state_string = new_state
            self.current_phase_index = action
            self._sumo.trafficlight.setRedYellowGreenState(self._ts.id, new_state)
            
            remaining = self.DELTA_TIME - self.YELLOW_TIME
            for _ in range(remaining):
                self._sumo.simulationStep()
            self.elapsed_green_time = remaining

        done = self._sumo.simulation.getTime() >= self.unwrapped.sim_max_time
        obs = self._compute_observation()
        reward = self._compute_reward()
        info = {"max_vehicle_wait_time": self._get_max_vehicle_wait()}
        return obs, reward, False, done, info

