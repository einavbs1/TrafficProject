"""
Copy current DQN checkpoint + training log + config snapshot before a fresh start.

Does not delete or move anything. Output: data/reports/policy_backups/<stamp>_<label>/
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.maps.map_registry import list_maps_for_gui
from flowgrid.paths import DEFAULT_POLICY_CONFIG_PATH, DQN_TRAINING_LOG_PATH, REPORTS_DIR

from flowgrid.maps.map_registry import DEFAULT_MAP_ID


def backup_map_training(
    map_id: str,
    *,
    label: str = "pre_fresh_start",
    include_episode_checkpoints: bool = False,
) -> Path:
    maps = list_maps_for_gui()
    entry = next((m for m in maps if m["id"] == map_id), None)
    if not entry:
        raise SystemExit(f"Map not found: {map_id!r}")

    policy_dir = Path(entry["policy_path"]).parent
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = REPORTS_DIR / "policy_backups" / f"{stamp}_{label}"
    dest.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []

    def _copy_if_exists(src: Path, subdir: str = "") -> None:
        if not src.is_file():
            return
        out_dir = dest / subdir if subdir else dest
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / src.name
        shutil.copy2(src, target)
        copied.append(str(target.relative_to(ROOT)))

    _copy_if_exists(Path(entry["policy_path"]))
    _copy_if_exists(policy_dir / "dqn_policy_objectives.txt")
    _copy_if_exists(DEFAULT_POLICY_CONFIG_PATH, "config")
    _copy_if_exists(DQN_TRAINING_LOG_PATH, "logs")

    if include_episode_checkpoints:
        ep_dir = dest / "episode_checkpoints"
        ep_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(policy_dir.glob("dqn_policy_ep*.pth")):
            shutil.copy2(f, ep_dir / f.name)
            copied.append(str((ep_dir / f.name).relative_to(ROOT)))

    readme = dest / "BACKUP_README.txt"
    readme.write_text(
        "\n".join(
            [
                f"FlowGrid policy backup — {stamp}",
                f"Label: {label}",
                f"Map: {map_id}",
                "",
                "Contents:",
                "  dqn_policy.pth          — main checkpoint (restore to map folder)",
                "  dqn_policy_objectives.txt",
                "  config/dqn_policy_config.yaml — snapshot at backup time",
                "  logs/dqn_training_log.jsonl — training history copy",
                "",
                "Restore main checkpoint:",
                f"  copy dqn_policy.pth -> data/maps/{map_id}/dqn_policy.pth",
                "",
                "Fresh start (archive old + new log):",
                f"  python scripts/run_train.py --map {DEFAULT_MAP_ID} --fresh --episodes 500",
                "",
                f"Files copied: {len(copied)}",
            ]
        ),
        encoding="utf-8",
    )

    print(f"Backup folder: {dest}")
    print(f"  {len(copied)} file(s) copied")
    for p in copied[:15]:
        print(f"    {p}")
    if len(copied) > 15:
        print(f"    ... and {len(copied) - 15} more")
    return dest


def main():
    parser = argparse.ArgumentParser(description="Backup DQN checkpoint and logs (no delete).")
    parser.add_argument("--map", default=DEFAULT_MAP_ID)
    parser.add_argument("--label", default="pre_balanced_policy_20k", help="Suffix for backup folder name")
    parser.add_argument(
        "--all-episode-checkpoints",
        action="store_true",
        help="Also copy every dqn_policy_epNNN.pth (large; default is main .pth only)",
    )
    args = parser.parse_args()
    backup_map_training(
        args.map,
        label=args.label,
        include_episode_checkpoints=bool(args.all_episode_checkpoints),
    )


if __name__ == "__main__":
    main()
