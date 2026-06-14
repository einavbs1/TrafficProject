import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.maps.map_registry import list_maps_for_gui
from flowgrid.paths import DEFAULTS_DIR, DQN_TRAINING_LOG_PATH, REPORTS_DIR
from flowgrid.reports.curriculum import CURRICULUM_LOG_PATH


def reset_map_training(policy_dir: Path, archive_root: Path) -> list[str]:
    moved: list[str] = []
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = archive_root / stamp
    dest.mkdir(parents=True, exist_ok=True)
    patterns = (
        "dqn_policy*.pth*",
        "dqn_policy*.old*",
        "dqn_policy_best*",
        "learning_curve.png",
        "dqn_policy_objectives.txt",
    )
    for pat in patterns:
        for f in policy_dir.glob(pat):
            if f.is_file():
                target = dest / f.name
                shutil.move(str(f), str(target))
                moved.append(str(target))
    return moved


def main():
    maps = list_maps_for_gui()
    if not maps:
        print("No maps.")
        sys.exit(1)
    archive_root = REPORTS_DIR / "training_archive"
    all_moved: list[str] = []
    for m in maps:
        pdir = Path(m["policy_path"]).parent
        all_moved.extend(reset_map_training(pdir, archive_root))
    all_moved.extend(reset_map_training(DEFAULTS_DIR, archive_root))
    log_path = DQN_TRAINING_LOG_PATH
    if log_path.is_file():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = REPORTS_DIR / f"dqn_training_log_{stamp}.jsonl.bak"
        shutil.move(str(log_path), str(backup))
        all_moved.append(str(backup))
    if CURRICULUM_LOG_PATH.is_file():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = REPORTS_DIR / f"curriculum_log_{stamp}.jsonl.bak"
        shutil.move(str(CURRICULUM_LOG_PATH), str(backup))
        all_moved.append(str(backup))
    print(f"Archived {len(all_moved)} file(s) under {archive_root}")
    for p in all_moved[:20]:
        print(f"  {p}")
    if len(all_moved) > 20:
        print(f"  ... and {len(all_moved) - 20} more")


if __name__ == "__main__":
    main()
