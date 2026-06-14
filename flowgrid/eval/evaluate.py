import os
import tempfile
from dataclasses import replace
from pathlib import Path

import torch
import yaml
import traci
from flowgrid.core.episode_limits import EpisodeLimits
from flowgrid.core.sumo_env import SumoEnv
from flowgrid.eval.compare_replay import (
    CompareReplayManifest,
    ensure_compare_baseline_demand,
    load_flow_metadata,
    manifest_from_departures,
    write_compare_replay_files,
)
from flowgrid.rl.dqn_agent import DQNAgent
from flowgrid.rl.policy_checkpoint import is_compatible, quarantine_incompatible
from flowgrid.rl.policy_checkpoint_io import load_policy_weights_for_eval
from flowgrid.eval.compare_metrics import CompareEpisodeMetrics
from flowgrid.maps.policy_paths import (
    canonical_policy_path,
    promote_latest_checkpoint_to_canonical,
    resolve_policy_path,
)
from flowgrid.rl.policy_config import PolicyConfig, DEFAULT_CONFIG_PATH


def _print_phase_tracker_section(title: str) -> None:
    print(f"[PHASE_TRACKER] === {title} ===", flush=True)


def _try_load_policy(agent: DQNAgent, policy_path: str) -> tuple[bool, str]:
    if not policy_path or not os.path.exists(policy_path):
        return False, "No trained model for this map. Click ▶ Train first."
    in_dim = agent.policy_net.net[0].in_features
    out_dim = agent.policy_net.net[4].out_features
    if not is_compatible(policy_path, in_dim, out_dim):
        quarantine_incompatible(policy_path, in_dim, out_dim)
        return False, (
            "Removed outdated model (wrong input size). "
            "Click ▶ Train on this map, then ▶ Compare again."
        )
    try:
        if not load_policy_weights_for_eval(agent, policy_path):
            return False, "Could not load model weights from checkpoint file."
        return True, ""
    except RuntimeError as exc:
        msg = str(exc)
        if "size mismatch" in msg:
            quarantine_incompatible(policy_path, in_dim, out_dim)
            return False, (
                "Removed outdated model (wrong input size). "
                "Click ▶ Train on this map, then ▶ Compare again."
            )
        return False, f"Could not load model: {msg}"


COMPARE_MAX_STEPS = 400
COMPARE_MAX_SIM_SECONDS = 3600.0


def _compare_yaml() -> dict:
    if DEFAULT_CONFIG_PATH.is_file():
        raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        return dict(raw.get("compare") or {})
    return {}


def _compare_config(inject_seconds_override: float | None = None) -> tuple[float, EpisodeLimits, dict]:
    ep = PolicyConfig.load().episode_training
    cmp_raw = _compare_yaml()
    inject_seconds = float(
        inject_seconds_override
        if inject_seconds_override is not None
        else cmp_raw.get("inject_seconds", ep.busy_warmup_sim_seconds)
    )
    drain_seconds = float(cmp_raw.get("max_drain_sim_seconds", 3600.0))
    limits = EpisodeLimits(
        min_sim_seconds=float(ep.min_sim_seconds),
        clear_streak_steps=int(ep.clear_streak_steps),
        max_steps=5000,
        max_sim_seconds=inject_seconds + drain_seconds,
        require_empty_network=True,
    )
    return inject_seconds, limits, cmp_raw


def _dqn_compare_limits(baseline_sim_time: float, cmp_raw: dict) -> EpisodeLimits:
    cfg = PolicyConfig.load()
    ep = cfg.episode_training
    base = max(float(baseline_sim_time), 1.0)
    multiplier = float(cmp_raw.get("dqn_drain_time_multiplier", 1.5))
    flat_buffer = float(cmp_raw.get("dqn_drain_flat_buffer_seconds", 1000.0))
    extra = float(cmp_raw.get("dqn_drain_extra_seconds", 1000.0))
    max_sim = max(base * multiplier, base + flat_buffer, base + extra)
    absolute_cap = float(cmp_raw.get("dqn_drain_max_sim_seconds", 10800.0))
    if absolute_cap > 0:
        max_sim = min(max_sim, absolute_cap)
    step_length = max(float(cfg.training.step_length), 1.0)
    max_steps = max(5000, int(max_sim / step_length) + 500)
    return EpisodeLimits(
        min_sim_seconds=float(ep.min_sim_seconds),
        clear_streak_steps=int(ep.clear_streak_steps),
        max_steps=max_steps,
        max_sim_seconds=max_sim,
        require_empty_network=True,
    )


def _manifest_counts(manifest: CompareReplayManifest | None) -> tuple[int, int, int]:
    if not manifest:
        return 0, 0, 0
    return manifest.car_count, manifest.bus_count, manifest.emergency_count


def _apply_manifest_vehicle_counts(
    metrics: CompareEpisodeMetrics,
    manifest: CompareReplayManifest,
) -> CompareEpisodeMetrics:
    return replace(
        metrics,
        scheduled_cars=manifest.car_count,
        scheduled_transit=manifest.bus_count,
        scheduled_emergency=manifest.emergency_count,
        all_vehicles_seen=manifest.total_count,
        transit_vehicles_seen=manifest.bus_count,
        emergency_vehicles_seen=manifest.emergency_count,
    )


def _run_episode(
    env: SumoEnv,
    agent: DQNAgent | None,
    *,
    use_fixed_time: bool,
    seed: int,
    skip_reset: bool = False,
    max_steps: int | None = None,
    manifest: CompareReplayManifest | None = None,
    departed_ids: set[str] | None = None,
    inject_seconds: float | None = None,
    stall_control_steps: int = 0,
) -> CompareEpisodeMetrics:
    if skip_reset:
        state = env._get_state()
        action_mask = env._action_mask(env._read_queues())
    else:
        state, reset_info = env.reset(seed=seed)
        action_mask = reset_info.get("action_mask")
    done = False
    truncated = False
    wait_sum = 0.0
    emergency_wait_sum = 0.0
    emergency_max_step_wait = 0.0
    emergency_preempt_steps = 0
    emergency_seen: set[str] = set()
    transit_wait_sum = 0.0
    transit_max_step_wait = 0.0
    transit_seen: set[str] = set()
    all_seen: set[str] = set()
    step_cap = max_steps
    timeline_sim_t: list[float] = []
    timeline_emergency_wait: list[float] = []
    timeline_transit_wait: list[float] = []
    step_count = 0
    ended_reason = ""
    stall_streak = 0
    last_queue = -1
    inject_cutoff = float(inject_seconds) if inject_seconds is not None else None

    while not (done or truncated):
        if use_fixed_time:
            action = 0
        else:
            action = agent.select_action(state, action_mask)  # type: ignore[union-attr]
        state, reward, done, truncated, info = env.step(action)
        action_mask = info.get("action_mask")
        wait_sum += env.total_waiting_time()
        emg_wait = env.total_emergency_waiting_time()
        emergency_wait_sum += emg_wait
        emergency_max_step_wait = max(emergency_max_step_wait, emg_wait)
        for vid in env.emergency_vehicle_ids():
            emergency_seen.add(vid)
        if info.get("emergency_active"):
            emergency_preempt_steps += 1
        tr_wait = env.total_transit_waiting_time()
        transit_wait_sum += tr_wait
        transit_max_step_wait = max(transit_max_step_wait, tr_wait)
        for vid in env.transit_vehicle_ids():
            transit_seen.add(vid)
        for vid in env._active_vehicle_ids():
            all_seen.add(vid)
        if departed_ids is not None:
            all_seen.update(departed_ids)
        if info.get("ended_reason"):
            ended_reason = str(info["ended_reason"])
        if (
            not use_fixed_time
            and stall_control_steps > 0
            and inject_cutoff is not None
            and env.sim_time >= inject_cutoff
        ):
            q = int(env._total_approach_queue())
            if q > 0 and q == last_queue:
                stall_streak += 1
            else:
                stall_streak = 0
            last_queue = q
            if stall_streak >= stall_control_steps:
                truncated = True
                ended_reason = "stalled"
        timeline_sim_t.append(float(env.sim_time))
        timeline_emergency_wait.append(emg_wait)
        timeline_transit_wait.append(tr_wait)
        step_count += 1
        if step_cap is not None and step_count >= step_cap:
            truncated = True
        elif not env.end_when_clear:
            if step_count >= COMPARE_MAX_STEPS or env.sim_time >= COMPARE_MAX_SIM_SECONDS:
                truncated = True

    if env.end_when_clear:
        tracker_reason = env._episode_tracker.state.ended_reason
        if tracker_reason:
            ended_reason = tracker_reason
        elif env._traci_active:
            try:
                if len(traci.vehicle.getIDList()) == 0:
                    ended_reason = "drained"
            except traci.exceptions.TraCIException:
                pass

    sched_cars, sched_bus, sched_emg = _manifest_counts(manifest)
    fleet = len(departed_ids) if departed_ids is not None else len(all_seen)
    total_sched = sched_cars + sched_bus + sched_emg
    if manifest is not None:
        all_count = total_sched
        bus_count = sched_bus
        emg_count = sched_emg
    else:
        all_count = fleet
        bus_count = len(transit_seen)
        emg_count = len(emergency_seen)
    return CompareEpisodeMetrics(
        total_wait=wait_sum,
        all_vehicles_seen=all_count,
        emergency_wait_sum=emergency_wait_sum,
        emergency_max_step_wait=emergency_max_step_wait,
        emergency_vehicles_seen=emg_count,
        emergency_preempt_steps=emergency_preempt_steps,
        transit_wait_sum=transit_wait_sum,
        transit_max_step_wait=transit_max_step_wait,
        transit_vehicles_seen=bus_count,
        scheduled_cars=sched_cars,
        scheduled_transit=sched_bus,
        scheduled_emergency=sched_emg,
        steps_run=step_count,
        ended_reason=ended_reason,
        timeline_sim_t=timeline_sim_t,
        timeline_emergency_wait=timeline_emergency_wait,
        timeline_transit_wait=timeline_transit_wait,
    )


def _build_compare_env(
    sumocfg_file: str,
    *,
    gui: bool,
    gui_delay: int,
    baseline_green_seconds: float | None,
    seed_snapshot: str,
    end_when_clear: bool,
    on_step,
    through_cap: float,
    left_to_through_ratio: float,
    topology,
    phase_ring,
    separate_right_turn: bool,
    min_green_seconds: float,
    min_green_base_seconds: float,
    switch_min_vehicles: int,
    switch_min_wait_seconds: float,
    max_green: float | None,
    compare_limits: EpisodeLimits | None = None,
    step_length: int | None = None,
    log_phase_tracker: bool = False,
) -> SumoEnv:
    ctrl_step = int(step_length if step_length is not None else PolicyConfig.load().training.step_length)
    return SumoEnv(
        sumocfg_file=sumocfg_file,
        gui=gui,
        gui_delay=gui_delay,
        step_length=ctrl_step,
        baseline_green_seconds=baseline_green_seconds,
        baseline_through_seconds=through_cap,
        baseline_left_to_through_ratio=left_to_through_ratio,
        topology=topology,
        phase_ring=phase_ring,
        separate_right_turn=separate_right_turn,
        min_green_seconds=float(min_green_seconds),
        min_green_base_seconds=float(min_green_base_seconds),
        switch_min_vehicles=int(switch_min_vehicles),
        switch_min_wait_seconds=float(switch_min_wait_seconds),
        max_green_seconds=max_green,
        on_step=on_step,
        live_updates=gui,
        quit_on_end=False,
        snapshot_path=seed_snapshot,
        end_when_clear=end_when_clear,
        episode_limits=compare_limits if end_when_clear else None,
        log_phase_tracker=log_phase_tracker,
    )


def evaluate_compare_pair(
    sumocfg_file: str,
    policy_path: str,
    baseline_green_seconds: float,
    seed: int = 42,
    gui: bool = False,
    gui_delay: int = 50,
    dqn_gui_only: bool = False,
    on_step=None,
    on_phase=None,
    min_green_seconds: float = 60,
    min_green_base_seconds: float = 5.0,
    switch_min_vehicles: int = 3,
    switch_min_wait_seconds: float = 25.0,
    max_green_seconds: float | None = None,
    map_settings: dict | None = None,
    inject_seconds: float | None = None,
    log_phase_tracker: bool = False,
) -> tuple[CompareEpisodeMetrics, CompareEpisodeMetrics, str]:
    """
    Baseline: random flows until inject_seconds, then drain until 0 vehicles; record departures.
    DQN: replay exact departures (route, lane, time) and drain until 0 vehicles.
    """
    snap_dir = os.path.join(tempfile.gettempdir(), "flowgrid")
    os.makedirs(snap_dir, exist_ok=True)
    snapshot = os.path.join(snap_dir, f"compare_seed{seed}.xml")

    map_dir = Path(sumocfg_file).resolve().parent
    source_routes = map_dir / "routes.rou.xml"
    inject_seconds, compare_limits, cmp_raw = _compare_config(inject_seconds)
    stall_steps = int(cmp_raw.get("stall_control_steps", 15))
    baseline_routes, baseline_sumocfg = ensure_compare_baseline_demand(map_dir, inject_seconds)

    max_green = float(max_green_seconds) if max_green_seconds and max_green_seconds > 0 else None
    from flowgrid.maps.map_env import sumo_env_extras

    extras = sumo_env_extras(map_settings) if map_settings else {}
    phase_ring = extras.pop("phase_ring", None)
    topology = extras.pop("topology", None)
    through_cap = float(
        (map_settings or {}).get("baseline_through_seconds", baseline_green_seconds)
    )
    left_ratio = float(
        (map_settings or {}).get(
            "baseline_left_to_through_ratio",
            PolicyConfig.load().baseline_timing.left_to_through_ratio,
        )
    )
    dqn_max_green_cfg = float(cmp_raw.get("dqn_max_green_seconds", through_cap))
    baseline_gui = bool(gui) and not dqn_gui_only
    dqn_gui = bool(gui)
    env_kw = dict(
        through_cap=through_cap,
        left_to_through_ratio=left_ratio,
        topology=topology,
        phase_ring=phase_ring,
        separate_right_turn=bool(extras.get("separate_right_turn", True)),
        min_green_seconds=float(min_green_seconds),
        min_green_base_seconds=float(min_green_base_seconds),
        switch_min_vehicles=int(switch_min_vehicles),
        switch_min_wait_seconds=float(switch_min_wait_seconds),
        max_green=max_green,
    )

    model_error = ""
    baseline_metrics = CompareEpisodeMetrics()
    dqn_metrics = CompareEpisodeMetrics()
    departures: list = []
    departure_seen: set[str] = set()
    flow_meta = load_flow_metadata(source_routes)

    def _phase(name: str, state: str, value: float | None = None):
        if on_phase:
            on_phase(name, state, value)

    baseline_env = _build_compare_env(
        baseline_sumocfg,
        gui=baseline_gui,
        gui_delay=gui_delay,
        on_step=on_step if baseline_gui else None,
        baseline_green_seconds=baseline_green_seconds,
        seed_snapshot=snapshot,
        end_when_clear=True,
        compare_limits=compare_limits,
        log_phase_tracker=log_phase_tracker,
        **env_kw,
    )

    try:
        _phase("baseline", "running")
        if log_phase_tracker:
            _print_phase_tracker_section("Baseline actions")
        baseline_env.enable_departure_recording(departures, departure_seen, flow_meta)
        try:
            baseline_metrics = _run_episode(
                baseline_env,
                None,
                use_fixed_time=True,
                seed=seed,
                departed_ids=departure_seen,
                inject_seconds=inject_seconds,
            )
        finally:
            baseline_env.disable_departure_recording()

        remaining = 0
        if baseline_env._traci_active:
            try:
                remaining = len(traci.vehicle.getIDList())
            except traci.exceptions.TraCIException:
                remaining = -1

        _phase("baseline", "done", baseline_metrics.priority_wait_sum)

        if remaining > 0:
            model_error = (
                f"Baseline stopped with {remaining} vehicles still on the map "
                f"(reason: {baseline_metrics.ended_reason or 'unknown'}). "
                f"Increase compare.max_drain_sim_seconds in dqn_policy_config.yaml."
            )
            return baseline_metrics, dqn_metrics, model_error

        if not departures:
            model_error = "Baseline produced no vehicles; cannot replay for DQN."
            return baseline_metrics, dqn_metrics, model_error

        counts = manifest_from_departures(departures)
        baseline_metrics = _apply_manifest_vehicle_counts(baseline_metrics, counts)

        baseline_sim_time = float(baseline_env.sim_time)
        replay_manifest = write_compare_replay_files(
            map_dir,
            source_routes,
            departures,
            seed=int(seed),
            sim_end_seconds=baseline_sim_time,
        )

        dqn_limits = _dqn_compare_limits(baseline_sim_time, cmp_raw)
        dqn_max_green = max_green if max_green is not None else dqn_max_green_cfg

        in_dim = baseline_env.observation_space.shape[0]
        out_dim = baseline_env.action_space.n
        agent = DQNAgent(in_dim, out_dim)
        canonical = str(canonical_policy_path(policy_path))
        load_path = resolve_policy_path(canonical)
        if load_path is None:
            model_error = (
                f"No trained model for this map (expected {canonical!r}). "
                "Train on this map first (Train tab), then run Compare again."
            )
        else:
            load_policy = str(load_path)
            if load_path.resolve() != Path(canonical).resolve():
                promote_latest_checkpoint_to_canonical(canonical)
                load_policy = canonical if os.path.isfile(canonical) else load_policy
            ok, err = _try_load_policy(agent, load_policy)
            if not ok:
                model_error = err
            else:
                baseline_env.close()
                baseline_env = None

                _phase("dqn", "running")
                if log_phase_tracker:
                    _print_phase_tracker_section("DQN agent actions")
                if dqn_gui and baseline_gui:
                    import time

                    time.sleep(1.0)
                dqn_env = _build_compare_env(
                    replay_manifest.sumocfg_path,
                    gui=dqn_gui,
                    gui_delay=gui_delay,
                    on_step=on_step if dqn_gui else None,
                    baseline_green_seconds=None,
                    seed_snapshot=snapshot,
                    end_when_clear=True,
                    compare_limits=dqn_limits,
                    max_green=dqn_max_green,
                    log_phase_tracker=log_phase_tracker,
                    **{k: v for k, v in env_kw.items() if k != "max_green"},
                )
                try:
                    dqn_metrics = _run_episode(
                        dqn_env,
                        agent,
                        use_fixed_time=False,
                        seed=seed,
                        manifest=replay_manifest,
                        departed_ids={d.vehicle_id for d in departures},
                        inject_seconds=inject_seconds,
                        stall_control_steps=stall_steps,
                    )
                    remaining_dqn = 0
                    if dqn_env._traci_active:
                        try:
                            remaining_dqn = len(traci.vehicle.getIDList())
                        except traci.exceptions.TraCIException:
                            remaining_dqn = -1
                    if remaining_dqn > 0:
                        reason = dqn_metrics.ended_reason or "unknown"
                        hint = (
                            "DQN could not clear the queue (policy/gridlock)."
                            if reason == "stalled"
                            else f"DQN hit time limit ({dqn_limits.max_sim_seconds:.0f}s sim)."
                        )
                        model_error = (
                            f"DQN stopped with {remaining_dqn} vehicles on the map "
                            f"(reason: {reason}). {hint}"
                        )
                    else:
                        _phase("dqn", "done", dqn_metrics.priority_wait_sum)
                finally:
                    dqn_env.close()
    finally:
        if baseline_env is not None:
            baseline_env.close()
        try:
            if os.path.isfile(snapshot):
                os.remove(snapshot)
        except OSError:
            pass

    return baseline_metrics, dqn_metrics, model_error


def evaluate_agent(
    policy_path=None,
    use_fixed_time=False,
    fixed_time_green_seconds=40,
    seed=42,
    sumocfg_file="flowgrid.sumocfg",
    gui=False,
    gui_delay=80,
    on_step=None,
):
    """
    Run one evaluation episode. Returns total wait time (0 if DQN load failed).
    Raises only on simulation errors, not on model mismatch.
    """
    baseline_seconds = fixed_time_green_seconds if use_fixed_time else None
    ctrl_step = int(PolicyConfig.load().training.step_length)
    env = SumoEnv(
        sumocfg_file=sumocfg_file,
        gui=gui,
        gui_delay=gui_delay,
        step_length=ctrl_step,
        baseline_green_seconds=baseline_seconds,
        on_step=on_step,
        quit_on_end=True,
    )
    input_dim = env.observation_space.shape[0]
    output_dim = env.action_space.n
    agent = DQNAgent(input_dim, output_dim)

    if not use_fixed_time:
        ok, err = _try_load_policy(agent, policy_path)
        if not ok:
            env.close()
            raise ModelLoadError(err)

    try:
        metrics = _run_episode(
            env, agent if not use_fixed_time else None, use_fixed_time=use_fixed_time, seed=seed
        )
        return metrics.total_wait
    finally:
        env.close()


class ModelLoadError(Exception):
    """DQN checkpoint incompatible or missing."""
