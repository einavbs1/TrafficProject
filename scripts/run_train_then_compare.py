"""Train N episodes with batch evaluate after every checkpoint save."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.core.sumo_env import SumoEnv
from flowgrid.eval.evaluate import _compare_yaml
from flowgrid.jobs.job_runner import JobRunner
from flowgrid.maps.map_env import sumo_env_extras
from flowgrid.maps.map_registry import DEFAULT_MAP_ID, list_maps_for_gui
from flowgrid.rl.policy_checkpoint import quarantine_incompatible
from flowgrid.util.labeled_paths import checkpoint_eval_log_path_for_label, training_log_path_for_label

from scripts.cli_poll import configure_stdout, poll_job

configure_stdout()

DEFAULT_MAP = DEFAULT_MAP_ID
DEFAULT_EVAL_RUNS = 10


def _pick_map(maps: list[dict], map_arg: str) -> dict:
    m = next((x for x in maps if x["id"] == map_arg or x["display_name"] == map_arg), None)
    if not m:
        raise SystemExit(f"Map not found: {map_arg!r}. Available: {[x['id'] for x in maps]}")
    return m


def _resolve_eval_runs(cli_value: int | None) -> int:
    if cli_value is not None:
        if cli_value < 1:
            raise SystemExit("--eval-runs must be >= 1")
        return cli_value
    if not sys.stdin.isatty():
        return DEFAULT_EVAL_RUNS
    try:
        raw = input(f"Eval runs per checkpoint [{DEFAULT_EVAL_RUNS}]: ").strip()
    except EOFError:
        return DEFAULT_EVAL_RUNS
    if not raw:
        return DEFAULT_EVAL_RUNS
    try:
        value = int(raw)
    except ValueError:
        raise SystemExit(f"Invalid eval runs: {raw!r}") from None
    if value < 1:
        raise SystemExit("--eval-runs must be >= 1")
    return value


def _run_checkpoint_eval(
    map_info: dict,
    checkpoint_episode: int,
    *,
    eval_runs: int,
    eval_seed: int,
    baseline_green: float,
    inject_seconds: float,
    eval_quiet: bool,
    label: str,
) -> None:
    print(
        f"Evaluating checkpoint episode {checkpoint_episode} ({eval_runs} runs, subprocess)...",
        flush=True,
    )
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_checkpoint_eval_once.py"),
        "--map",
        map_info["id"],
        "--checkpoint-episode",
        str(checkpoint_episode),
        "--eval-runs",
        str(eval_runs),
        "--eval-seed",
        str(eval_seed),
        "--baseline-green",
        str(baseline_green),
        "--inject-seconds",
        str(inject_seconds),
    ]
    if label:
        cmd.extend(["--label", label])
    if eval_quiet:
        cmd.append("--eval-quiet")
    else:
        cmd.append("--no-eval-quiet")

    proc = subprocess.run(cmd, cwd=str(ROOT))

    if proc.returncode != 0:
        raise SystemExit(f"Checkpoint eval subprocess failed (exit {proc.returncode})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FlowGrid: train with batch evaluate after each checkpoint save"
    )
    parser.add_argument("--map", default=DEFAULT_MAP)
    parser.add_argument("--episodes", type=int, default=500)
    parser.add_argument("--checkpoint-every", type=int, default=10)
    parser.add_argument("--fresh", action="store_true", help="Archive old policy + log before train")
    parser.add_argument("--resume", action="store_true", help="Continue from existing dqn_policy.pth")
    parser.add_argument("--train-seed", type=int, default=None, help="Base SUMO seed for training")
    parser.add_argument(
        "--eval-runs",
        type=int,
        default=None,
        help=f"Evaluate runs per checkpoint (default: prompt, else {DEFAULT_EVAL_RUNS})",
    )
    parser.add_argument("--eval-seed", type=int, default=42, help="Fixed SUMO seed for checkpoint eval runs")
    parser.add_argument(
        "--eval-quiet",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Suppress per-run lines during checkpoint eval (default: true)",
    )
    parser.add_argument("--inject-seconds", type=float, default=None)
    parser.add_argument("--baseline-green", type=float, default=60.0)
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Experiment label for training and checkpoint eval logs",
    )
    args = parser.parse_args()

    eval_runs = _resolve_eval_runs(args.eval_runs)

    if args.fresh:
        print("Archiving old checkpoints and training log (--fresh)...", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "reset_training.py")], check=True)

    maps = list_maps_for_gui()
    if not maps:
        raise SystemExit("No maps found.")
    m = _pick_map(maps, args.map)

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
    quarantine_incompatible(m["policy_path"], in_dim, out_dim)

    cmp = _compare_yaml()
    inject = float(
        args.inject_seconds if args.inject_seconds is not None else cmp.get("inject_seconds", 800)
    )
    curve = str(Path(m["policy_path"]).parent / "learning_curve.png")
    train_log = training_log_path_for_label(args.label or None)
    eval_log = checkpoint_eval_log_path_for_label(args.label or None)
    train_log.parent.mkdir(parents=True, exist_ok=True)
    mode = "resume" if args.resume else "fresh"

    print("=" * 60, flush=True)
    print("TRAIN + CHECKPOINT EVAL", flush=True)
    print(f"  Map:              {m['display_name']} ({m['id']})", flush=True)
    print(f"  Episodes:         {args.episodes} ({mode})", flush=True)
    print(f"  Checkpoint every: {args.checkpoint_every}", flush=True)
    print(f"  Eval runs:        {eval_runs}  seed={args.eval_seed}", flush=True)
    print(f"  Checkpoint log:   {eval_log}", flush=True)
    if args.label:
        print(f"  Training log:     {train_log}", flush=True)
    print("=" * 60, flush=True)

    runner = JobRunner()
    train_id = runner.start_train(
        m["sumocfg"],
        episodes=args.episodes,
        policy_path=m["policy_path"],
        learning_curve_path=curve,
        checkpoint_every=max(1, args.checkpoint_every),
        min_green_seconds=60,
        min_green_base_seconds=5,
        switch_min_vehicles=3,
        switch_min_wait_seconds=25.0,
        max_green_seconds=None,
        map_name=m["display_name"],
        map_id=m["id"],
        resume=bool(args.resume),
        train_seed=args.train_seed,
        training_log_path=str(train_log),
    )

    last_episodes_done = 0
    last_evaluated_ckpt = 0

    def on_train(msg: str, progress: float, result: dict) -> None:
        nonlocal last_episodes_done, last_evaluated_ckpt
        ep_done = int(result.get("episodes_done", 0) or 0)
        if ep_done > last_episodes_done:
            last_episodes_done = ep_done
            print(msg, flush=True)
        ckpt = int(result.get("checkpoint_episode") or result.get("last_saved_episode") or 0)
        if ckpt > last_evaluated_ckpt:
            _run_checkpoint_eval(
                m,
                ckpt,
                eval_runs=eval_runs,
                eval_seed=int(args.eval_seed),
                baseline_green=float(args.baseline_green),
                inject_seconds=inject,
                eval_quiet=bool(args.eval_quiet),
                label=args.label or "",
            )
            last_evaluated_ckpt = ckpt

    train_job = poll_job(runner, train_id, poll_s=0.5, on_message=on_train)
    if not train_job or train_job.status == "failed":
        print(f"TRAIN FAILED: {train_job.error if train_job else 'unknown'}", flush=True)
        sys.exit(1)

    tr = train_job.result or {}
    final_saved = int(tr.get("last_saved_episode") or tr.get("checkpoint_episode") or 0)
    if final_saved > last_evaluated_ckpt:
        _run_checkpoint_eval(
            m,
            final_saved,
            eval_runs=eval_runs,
            eval_seed=int(args.eval_seed),
            baseline_green=float(args.baseline_green),
            inject_seconds=inject,
            eval_quiet=bool(args.eval_quiet),
            label=args.label or "",
        )

    print(
        f"Train done. episodes={tr.get('episodes_done')} "
        f"epsilon={tr.get('epsilon', 0):.4f} avg_wait_last10={tr.get('avg_wait_last_10', 0):.0f}",
        flush=True,
    )
    print(f"Checkpoint eval log: {eval_log}", flush=True)


if __name__ == "__main__":
    main()
