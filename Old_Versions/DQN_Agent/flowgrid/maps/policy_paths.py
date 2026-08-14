from __future__ import annotations

import re
from pathlib import Path

from flowgrid.paths import PROJECT_ROOT

_EPISODE_CHECKPOINT_RE = re.compile(r"^dqn_policy_ep(\d+)\.pth$", re.IGNORECASE)


def canonical_policy_path(policy_path: str | Path) -> Path:
    path = Path(policy_path)
    if path.is_absolute():
        return path
    return (PROJECT_ROOT / path).resolve()


def policy_directory(policy_path: str | Path) -> Path:
    return canonical_policy_path(policy_path).parent


def _numbered_checkpoints(policy_dir: Path) -> list[Path]:
    candidates: list[tuple[int, Path]] = []
    for item in policy_dir.glob("dqn_policy_ep*.pth"):
        if not item.is_file():
            continue
        match = _EPISODE_CHECKPOINT_RE.match(item.name)
        if match:
            candidates.append((int(match.group(1)), item))
    candidates.sort(key=lambda pair: pair[0])
    return [path for _, path in candidates]


def resolve_policy_path(policy_path: str | Path) -> Path | None:
    canonical = canonical_policy_path(policy_path)
    if canonical.is_file():
        return canonical
    policy_dir = canonical.parent
    if not policy_dir.is_dir():
        return None
    best = policy_dir / "dqn_policy_best.pth"
    if best.is_file():
        return best.resolve()
    numbered = _numbered_checkpoints(policy_dir)
    if numbered:
        return numbered[-1].resolve()
    return None


def resolved_policy_path(policy_path: str | Path) -> str:
    found = resolve_policy_path(policy_path)
    if found is not None:
        return str(found)
    return str(canonical_policy_path(policy_path))


def policy_checkpoint_exists(policy_path: str | Path) -> bool:
    return resolve_policy_path(policy_path) is not None


def _quarantined_policy_candidates(policy_dir: Path) -> list[Path]:
    stem = "dqn_policy.pth"
    candidates: list[tuple[int, Path]] = []
    for item in policy_dir.iterdir():
        if not item.is_file():
            continue
        name = item.name
        if name == f"{stem}.old":
            candidates.append((0, item))
            continue
        if name.startswith(f"{stem}.old") and name[len(stem) + 3 :].isdigit():
            candidates.append((int(name[len(stem) + 3 :]), item))
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return [path for _, path in candidates]


def restore_compatible_quarantine(policy_path: str | Path) -> Path | None:
    from flowgrid.rl.policy_checkpoint import is_compatible

    canonical = canonical_policy_path(policy_path)
    if canonical.is_file():
        return canonical
    policy_dir = canonical.parent
    if not policy_dir.is_dir():
        return None
    for candidate in _quarantined_policy_candidates(policy_dir):
        if not is_compatible(candidate):
            continue
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_bytes(candidate.read_bytes())
        return canonical
    return None


def promote_latest_checkpoint_to_canonical(policy_path: str | Path) -> Path | None:
    canonical = canonical_policy_path(policy_path)
    if canonical.is_file():
        return canonical
    latest = resolve_policy_path(policy_path)
    if latest is None or latest == canonical:
        return restore_compatible_quarantine(policy_path)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_bytes(latest.read_bytes())
    return canonical
