from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = PROJECT_ROOT / "logs" / "flowgrid_menu.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEVICE_CHOICES = ("auto", "cpu", "cuda", "directml")

ACTIONS: dict[str, dict[str, Any]] = {
    "train": {
        "title": "Train DQN",
        "script": "scripts/run_train.py",
        "options": [
            {"key": "label", "title": "Experiment label", "type": "str", "flag": "--label", "default": ""},
            {"key": "map", "title": "Map id", "type": "str", "flag": "--map", "default": "flowgrid"},
            {"key": "episodes", "title": "Episodes", "type": "int", "flag": "--episodes", "default": 500},
            {"key": "checkpoint_every", "title": "Checkpoint every", "type": "int", "flag": "--checkpoint-every", "default": 10},
            {"key": "fresh", "title": "Fresh start", "type": "bool", "flag": "--fresh", "default": False},
            {"key": "resume", "title": "Resume checkpoint", "type": "bool", "flag": "--resume", "default": False},
            {"key": "seed", "title": "Train seed", "type": "int", "flag": "--seed", "default": None, "optional": True},
            {"key": "compact_progress", "title": "Compact progress", "type": "bool", "flag": "--compact-progress", "default": False},
            {"key": "device", "title": "Device", "type": "choice", "flag": "--device", "default": "auto", "choices": DEVICE_CHOICES},
        ],
    },
    "evaluate": {
        "title": "Batch evaluate",
        "script": "scripts/run_evaluate.py",
        "options": [
            {"key": "label", "title": "Experiment label", "type": "str", "flag": "--label", "default": ""},
            {"key": "map", "title": "Map id", "type": "str", "flag": "--map", "default": "flowgrid"},
            {"key": "runs", "title": "Runs", "type": "int", "flag": "--runs", "default": 1},
            {"key": "seed", "title": "Seed", "type": "int", "flag": "--seed", "default": None, "optional": True},
            {"key": "quiet", "title": "Quiet", "type": "bool", "flag": "--quiet", "default": False},
            {"key": "gui", "title": "DQN GUI", "type": "bool", "flag": "--gui", "default": False},
            {"key": "phase_tracker", "title": "Phase tracker", "type": "bool", "flag": "--phase-tracker", "default": False},
            {"key": "baseline_green", "title": "Baseline green (s)", "type": "float", "flag": "--baseline-green", "default": 60.0},
            {"key": "inject_seconds", "title": "Inject seconds", "type": "float", "flag": "--inject-seconds", "default": None, "optional": True},
        ],
    },
    "compare": {
        "title": "Fair compare (1 run)",
        "script": "scripts/run_compare.py",
        "options": [
            {"key": "map", "title": "Map id", "type": "str", "flag": "--map", "default": "flowgrid"},
            {"key": "seed", "title": "Seed", "type": "int", "flag": "--seed", "default": 42},
            {"key": "gui", "title": "SUMO GUI", "type": "bool", "flag": "--gui", "default": False},
            {"key": "delay", "title": "GUI delay (ms)", "type": "int", "flag": "--delay", "default": 0},
            {"key": "baseline_green", "title": "Baseline green (s)", "type": "float", "flag": "--baseline-green", "default": 60.0},
            {"key": "inject_seconds", "title": "Inject seconds", "type": "float", "flag": "--inject-seconds", "default": None, "optional": True},
        ],
    },
    "train_then_compare": {
        "title": "Train with checkpoint eval",
        "script": "scripts/run_train_then_compare.py",
        "options": [
            {"key": "label", "title": "Experiment label", "type": "str", "flag": "--label", "default": ""},
            {"key": "map", "title": "Map id", "type": "str", "flag": "--map", "default": "flowgrid"},
            {"key": "episodes", "title": "Episodes", "type": "int", "flag": "--episodes", "default": 500},
            {"key": "checkpoint_every", "title": "Checkpoint every", "type": "int", "flag": "--checkpoint-every", "default": 10},
            {"key": "fresh", "title": "Fresh start", "type": "bool", "flag": "--fresh", "default": False},
            {"key": "resume", "title": "Resume checkpoint", "type": "bool", "flag": "--resume", "default": False},
            {"key": "train_seed", "title": "Train seed", "type": "int", "flag": "--train-seed", "default": None, "optional": True},
            {"key": "eval_runs", "title": "Eval runs per checkpoint", "type": "int", "flag": "--eval-runs", "default": None, "optional": True},
            {"key": "eval_seed", "title": "Eval seed", "type": "int", "flag": "--eval-seed", "default": 42},
            {"key": "inject_seconds", "title": "Inject seconds", "type": "float", "flag": "--inject-seconds", "default": None, "optional": True},
        ],
    },
    "curriculum": {
        "title": "Curriculum loop",
        "script": "scripts/run_curriculum.py",
        "options": [
            {"key": "label", "title": "Experiment label", "type": "str", "flag": "--label", "default": ""},
            {"key": "map", "title": "Map id", "type": "str", "flag": "--map", "default": "flowgrid"},
            {"key": "episodes_per_cycle", "title": "Episodes per cycle", "type": "int", "flag": "--episodes-per-cycle", "default": None, "optional": True},
            {"key": "max_cycles", "title": "Max cycles", "type": "int", "flag": "--max-cycles", "default": None, "optional": True},
            {"key": "compare_seed", "title": "Compare seed", "type": "int", "flag": "--compare-seed", "default": None, "optional": True},
            {"key": "compare_gui", "title": "Compare GUI", "type": "bool", "flag": "--compare-gui", "default": False},
            {"key": "fresh", "title": "Fresh start", "type": "bool", "flag": "--fresh", "default": False},
            {"key": "checkpoint_every", "title": "Checkpoint every", "type": "int", "flag": "--checkpoint-every", "default": 10},
            {"key": "inject_seconds", "title": "Inject seconds", "type": "float", "flag": "--inject-seconds", "default": None, "optional": True},
        ],
    },
    "check_device": {
        "title": "Check device",
        "script": "scripts/check_device.py",
        "options": [
            {"key": "device", "title": "Device", "type": "choice", "flag": "--device", "default": "auto", "choices": DEVICE_CHOICES},
        ],
    },
    "backup": {
        "title": "Backup training",
        "script": "scripts/backup_training.py",
        "options": [
            {"key": "map", "title": "Map id", "type": "str", "flag": "--map", "default": "flowgrid"},
            {"key": "label", "title": "Backup label", "type": "str", "flag": "--label", "default": "pre_fresh_start"},
            {"key": "all_episode_checkpoints", "title": "All episode checkpoints", "type": "bool", "flag": "--all-episode-checkpoints", "default": False},
        ],
    },
}


def ensure_project_root() -> None:
    markers = [PROJECT_ROOT / "flowgrid", PROJECT_ROOT / "scripts" / "run_train.py"]
    if not all(p.exists() for p in markers):
        print("ERROR: Cannot find FlowGrid project layout from this script location.", flush=True)
        print(f"  Expected root: {PROJECT_ROOT}", flush=True)
        sys.exit(1)
    cwd = Path.cwd().resolve()
    if cwd != PROJECT_ROOT.resolve():
        print("WARNING: Current directory is not the project root.", flush=True)
        print(f"  cwd:     {cwd}", flush=True)
        print(f"  project: {PROJECT_ROOT.resolve()}", flush=True)
        print("  Commands will run with project root as working directory.", flush=True)
        print(flush=True)


def default_options(action_id: str) -> dict[str, Any]:
    action = ACTIONS[action_id]
    return {opt["key"]: deepcopy(opt["default"]) for opt in action["options"]}


def default_state() -> dict[str, Any]:
    return {
        "action": "train",
        "options": default_options("train"),
        "last_argv": [],
    }


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return default_state()
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_state()
    action = raw.get("action", "train")
    if action not in ACTIONS:
        action = "train"
    opts = default_options(action)
    saved = raw.get("options") or {}
    if isinstance(saved, dict):
        for key in opts:
            if key in saved:
                opts[key] = saved[key]
    last_argv = raw.get("last_argv") or []
    if not isinstance(last_argv, list):
        last_argv = []
    return {"action": action, "options": opts, "last_argv": [str(x) for x in last_argv]}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def format_value(opt: dict[str, Any], value: Any) -> str:
    if opt["type"] == "bool":
        return "ON" if value else "OFF"
    if value is None or value == "":
        return "(default)"
    return str(value)


def build_argv(action_id: str, options: dict[str, Any]) -> list[str]:
    action = ACTIONS[action_id]
    argv = [action["script"]]
    for opt in action["options"]:
        key = opt["key"]
        val = options.get(key, opt["default"])
        if opt["type"] == "bool":
            if val:
                argv.append(opt["flag"])
            continue
        if val is None or val == "":
            continue
        if opt["type"] == "int":
            argv.extend([opt["flag"], str(int(val))])
        elif opt["type"] == "float":
            argv.extend([opt["flag"], str(float(val))])
        elif opt["type"] in ("str", "choice"):
            argv.extend([opt["flag"], str(val)])
    return argv


def format_command(argv: list[str]) -> str:
    parts = [sys.executable, *argv]
    return " ".join(parts)


def cwd_status_line() -> str:
    cwd = Path.cwd().resolve()
    root = PROJECT_ROOT.resolve()
    if cwd == root:
        return f"{root}  (OK)"
    return f"{cwd}  (using {root} for runs)"


def render_summary(state: dict[str, Any]) -> list[str]:
    action_id = state["action"]
    action = ACTIONS[action_id]
    opts = state["options"]
    lines = [
        "=" * 64,
        " FlowGrid Terminal Menu",
        "=" * 64,
        f" Cwd:        {cwd_status_line()}",
        f" Action:     {action['title']}",
        f" Config:     {STATE_PATH}",
    ]
    label = opts.get("label")
    if label is not None and str(label).strip():
        lines.append(f" Label:      {label}")
    parts: list[str] = []
    for opt in action["options"]:
        if opt["key"] == "label":
            continue
        parts.append(f"{opt['title']}: {format_value(opt, opts.get(opt['key']))}")
    if parts:
        line = " | ".join(parts[:4])
        lines.append(f" Options:    {line}")
        if len(parts) > 4:
            lines.append(f"             {' | '.join(parts[4:8])}")
        if len(parts) > 8:
            lines.append(f"             {' | '.join(parts[8:])}")
    lines.append("-" * 64)
    lines.append(" 1) Change action")
    lines.append(" 2) Edit options")
    lines.append(" 3) Preview command")
    lines.append(" 4) Reset action defaults")
    lines.append(" 5) START")
    lines.append(" 7) Repeat last run")
    lines.append(" 0) Quit")
    return lines


def pick_action(state: dict[str, Any]) -> None:
    ids = list(ACTIONS.keys())
    print("\nSelect action:", flush=True)
    for i, aid in enumerate(ids, start=1):
        print(f"  {i}) {ACTIONS[aid]['title']}", flush=True)
    print("  0) Cancel", flush=True)
    raw = input("> ").strip()
    if raw == "0" or not raw:
        return
    try:
        idx = int(raw)
    except ValueError:
        print("Invalid choice.", flush=True)
        return
    if idx < 1 or idx > len(ids):
        print("Invalid choice.", flush=True)
        return
    new_id = ids[idx - 1]
    state["action"] = new_id
    state["options"] = default_options(new_id)
    saved = load_state()
    if saved.get("action") == new_id and isinstance(saved.get("options"), dict):
        for key in state["options"]:
            if key in saved["options"]:
                state["options"][key] = saved["options"][key]


def list_map_ids() -> list[str]:
    try:
        from flowgrid.maps.map_registry import list_maps_for_gui

        return [m["id"] for m in list_maps_for_gui()]
    except Exception:
        return []


def edit_option_value(opt: dict[str, Any], current: Any) -> Any:
    if opt["type"] == "bool":
        return not bool(current)
    if opt["type"] == "choice":
        choices = list(opt.get("choices") or [])
        print(f"Choices: {', '.join(choices)}", flush=True)
        raw = input(f"New value [{current}]: ").strip()
        if not raw:
            return current
        if raw in choices:
            return raw
        print("Invalid choice.", flush=True)
        return current
    if opt["key"] == "map":
        maps = list_map_ids()
        if maps:
            print("Maps: " + ", ".join(maps), flush=True)
    optional = bool(opt.get("optional"))
    hint = "empty=default" if optional else ""
    raw = input(f"New value [{format_value(opt, current)}]{(' ' + hint) if hint else ''}: ").strip()
    if optional and not raw:
        return None
    if opt["type"] == "int":
        return int(raw)
    if opt["type"] == "float":
        return float(raw)
    return raw


def edit_options(state: dict[str, Any]) -> None:
    action = ACTIONS[state["action"]]
    opts = state["options"]
    while True:
        print(f"\nEdit options — {action['title']}", flush=True)
        for i, opt in enumerate(action["options"], start=1):
            val = opts.get(opt["key"])
            print(f"  {i}) {opt['title']}: {format_value(opt, val)}", flush=True)
        print("  0) Back", flush=True)
        raw = input("> ").strip()
        if raw == "0":
            return
        try:
            idx = int(raw)
        except ValueError:
            print("Invalid choice.", flush=True)
            continue
        if idx < 1 or idx > len(action["options"]):
            print("Invalid choice.", flush=True)
            continue
        opt = action["options"][idx - 1]
        try:
            opts[opt["key"]] = edit_option_value(opt, opts.get(opt["key"]))
        except ValueError:
            print("Invalid value.", flush=True)


def preview_command(state: dict[str, Any]) -> None:
    argv = build_argv(state["action"], state["options"])
    print("\nCommand:", flush=True)
    print(format_command(argv), flush=True)
    input("\nPress Enter...")


def reset_defaults(state: dict[str, Any]) -> None:
    state["options"] = default_options(state["action"])
    print("Options reset to defaults.", flush=True)


def run_argv(argv: list[str], state: dict[str, Any]) -> int:
    state["last_argv"] = list(argv)
    save_state(state)
    print(f"\nRunning: {format_command(argv)}\n", flush=True)
    result = subprocess.run([sys.executable, *argv], cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\nExit code: {result.returncode}", flush=True)
    input("\nPress Enter to return to menu...")
    return int(result.returncode)


def repeat_last(state: dict[str, Any]) -> None:
    argv = state.get("last_argv") or []
    if not argv:
        print("\nNo previous run saved.", flush=True)
        input("Press Enter...")
        return
    print(f"\nRepeating: {format_command(argv)}\n", flush=True)
    state["last_argv"] = list(argv)
    save_state(state)
    result = subprocess.run([sys.executable, *argv], cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\nExit code: {result.returncode}", flush=True)
    input("\nPress Enter to return to menu...")


def main() -> None:
    ensure_project_root()
    state = load_state()
    while True:
        print(flush=True)
        for line in render_summary(state):
            print(line, flush=True)
        raw = input("> ").strip()
        if raw == "0":
            save_state(state)
            print("Goodbye.", flush=True)
            break
        if raw == "1":
            pick_action(state)
            save_state(state)
        elif raw == "2":
            edit_options(state)
            save_state(state)
        elif raw == "3":
            preview_command(state)
        elif raw == "4":
            reset_defaults(state)
            save_state(state)
        elif raw == "5":
            argv = build_argv(state["action"], state["options"])
            run_argv(argv, state)
        elif raw == "7":
            repeat_last(state)
        else:
            print("Invalid choice.", flush=True)


if __name__ == "__main__":
    main()
