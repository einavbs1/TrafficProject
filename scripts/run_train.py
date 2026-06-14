import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.core.sumo_env import SumoEnv
from flowgrid.jobs.job_runner import JobRunner
from flowgrid.util.terminal_log import terminal_line, terminal_print
from flowgrid.maps.map_env import sumo_env_extras
from flowgrid.maps.map_registry import DEFAULT_MAP_ID, list_maps_for_gui
from flowgrid.maps.policy_paths import canonical_policy_path, promote_latest_checkpoint_to_canonical
from flowgrid.rl.policy_checkpoint import quarantine_incompatible
from flowgrid.util.labeled_paths import training_log_path_for_label

from scripts.cli_poll import configure_stdout

configure_stdout()

DEFAULT_TRAIN_MAP_ID = DEFAULT_MAP_ID


def _pick_train_map(maps: list[dict], map_arg: str) -> dict:
    if map_arg:
        for item in maps:
            if item["display_name"] == map_arg or item["id"] == map_arg:
                return item
        raise SystemExit(f"Map not found: {map_arg!r}. Available: {[m['id'] for m in maps]}")
    for item in maps:
        if item["id"] == DEFAULT_TRAIN_MAP_ID:
            return item
    for item in maps:
        if item["id"] != "flowgrid":
            return item
    return maps[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--map", type=str, default="")
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--fresh", action="store_true", help="Archive old checkpoints and train from scratch")
    parser.add_argument("--resume", action="store_true", help="Continue from existing dqn_policy.pth if present")
    parser.add_argument("--seed", type=int, default=None, help="Base SUMO seed for training episodes")
    parser.add_argument(
        "--busy-fraction",
        type=float,
        default=None,
        help="Fraction of episodes that start from a busy snapshot (default from config)",
    )
    parser.add_argument(
        "--compact-progress",
        action="store_true",
        help="Overwrite one status line instead of printing each episode on its own line",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["auto", "cpu", "cuda", "directml"],
        help="PyTorch device for DQN training (auto: CUDA, then DirectML, then CPU)",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Experiment label; writes to logs/dqn_training_log_<label>.jsonl instead of default",
    )
    args = parser.parse_args()

    if args.fresh:
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "reset_training.py")], check=True)

    maps = list_maps_for_gui()
    if not maps:
        print("No maps found.")
        sys.exit(1)
    m = _pick_train_map(maps, args.map)

    env_extras = sumo_env_extras(m)
    phase_ring = env_extras.pop("phase_ring", None)
    topology = env_extras.pop("topology", None)
    env_probe = SumoEnv(
        m["sumocfg"],
        gui=False,
        quit_on_end=True,
        live_updates=False,
        topology=topology,
        phase_ring=phase_ring,
        **env_extras,
    )
    in_dim = env_probe.observation_space.shape[0]
    out_dim = env_probe.action_space.n
    env_probe.close()
    canonical = str(canonical_policy_path(m["policy_path"]))
    quarantine_incompatible(canonical, in_dim, out_dim)
    if args.resume:
        promote_latest_checkpoint_to_canonical(canonical)

    curve = str(Path(m["policy_path"]).parent / "learning_curve.png")
    train_log = training_log_path_for_label(args.label or None)
    train_log.parent.mkdir(parents=True, exist_ok=True)
    if args.label:
        terminal_print(f"Training log: {train_log}")
    runner = JobRunner()
    job_id = runner.start_train(
        m["sumocfg"],
        episodes=args.episodes,
        policy_path=m["policy_path"],
        learning_curve_path=curve,
        checkpoint_every=args.checkpoint_every,
        min_green_seconds=60,
        min_green_base_seconds=5,
        switch_min_vehicles=3,
        switch_min_wait_seconds=25.0,
        max_green_seconds=None,
        map_name=m["display_name"],
        map_id=m["id"],
        resume=bool(args.resume),
        train_seed=args.seed,
        busy_fraction=args.busy_fraction,
        device=args.device,
        training_log_path=str(train_log),
    )
    mode = "resume" if args.resume else "fresh"
    terminal_print(f"Training job {job_id} - {args.episodes} episodes ({mode}) on {m['display_name']}")
    terminal_print(f"Policy: {m['policy_path']}")
    terminal_print(f"Map id: {m['id']}")

    last_episodes_done = 0
    while True:
        job = runner.get_job(job_id)
        if not job:
            time.sleep(1)
            continue

        msg = (job.message or "").encode("ascii", errors="replace").decode("ascii")
        result = job.result or {}
        episodes_done = int(result.get("episodes_done", 0) or 0)

        if args.compact_progress:
            pct = int(job.progress * 100)
            print(f"\r[{pct:3d}%] {msg}", end="", flush=True)
        elif episodes_done > last_episodes_done:
            terminal_print(msg)
            last_episodes_done = episodes_done

        if job.status == "completed":
            if args.compact_progress:
                print()
            r = job.result or {}
            terminal_print(
                f"Done. episodes={r.get('episodes_done')} "
                f"last_reward={r.get('last_reward', 0):.1f} "
                f"avg_wait_last10={r.get('avg_wait_last_10', 0):.0f} "
                f"epsilon={r.get('epsilon', 0):.4f}"
            )
            if r.get("last_saved_episode"):
                terminal_print(f"Last checkpoint: episode {r.get('last_saved_episode')}")
            break
        if job.status == "failed":
            if args.compact_progress:
                print()
            terminal_print(f"FAILED: {job.error}")
            sys.exit(1)
        time.sleep(1)


if __name__ == "__main__":
    main()
