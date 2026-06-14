"""Compare outcome checks and best-checkpoint management."""
from __future__ import annotations

import os
import shutil
from typing import Any


def best_policy_path(policy_path: str) -> str:
    root, ext = os.path.splitext(policy_path)
    ext = ext or ".pth"
    return f"{root}_best{ext}"


def is_catastrophic_compare(result: dict[str, Any]) -> bool:
    """True when Compare failed or DQN all-vehicle wait is far worse than baseline."""
    err = (result.get("model_error") or "").strip()
    if err:
        return True
    dqn_all = float(result.get("dqn_wait_all", 0) or 0)
    base_all = float(result.get("fixed_wait_all", 0) or result.get("baseline_wait_all", 0) or 0)
    if base_all > 0 and dqn_all > 2.0 * base_all:
        return True
    return False


def is_valid_improvement(result: dict[str, Any], best_dqn_wait_all: float | None) -> bool:
    """True when Compare completed cleanly and beat the previous best all-vehicle wait."""
    if (result.get("model_error") or "").strip():
        return False
    dqn_all = float(result.get("dqn_wait_all", 0) or 0)
    if dqn_all <= 0:
        return False
    if best_dqn_wait_all is None:
        return True
    return dqn_all < best_dqn_wait_all


def read_best_dqn_wait_all(policy_path: str) -> float | None:
    sidecar = best_policy_path(policy_path) + ".meta"
    if not os.path.isfile(sidecar):
        return None
    try:
        text = open(sidecar, encoding="utf-8").read().strip()
        return float(text) if text else None
    except (OSError, ValueError):
        return None


def save_best_policy(policy_path: str, dqn_wait_all: float) -> str:
    """Copy current policy to *_best.pth and record wait score."""
    best = best_policy_path(policy_path)
    if not os.path.isfile(policy_path):
        return best
    shutil.copy2(policy_path, best)
    meta = best + ".meta"
    with open(meta, "w", encoding="utf-8") as f:
        f.write(str(float(dqn_wait_all)))
    return best


def restore_best_policy(policy_path: str) -> bool:
    """Restore *_best.pth over main policy if best exists."""
    best = best_policy_path(policy_path)
    if not os.path.isfile(best):
        return False
    shutil.copy2(best, policy_path)
    return True


def print_compare_summary(result: dict[str, Any]) -> None:
    """CLI-friendly Compare summary; marks invalid runs clearly."""
    err = (result.get("model_error") or "").strip()
    invalid = bool(result.get("compare_invalid")) or is_catastrophic_compare(result)
    base_all = int(result.get("fixed_wait_all", 0) or result.get("baseline_wait_all", 0) or 0)
    dqn_all = int(result.get("dqn_wait_all", 0) or 0)
    imp_all = float(result.get("improvement_percent_all", 0) or 0)

    print("=" * 60, flush=True)
    if invalid:
        print("INVALID COMPARE (do not trust improvement %)", flush=True)
        if err:
            print(f"  Reason: {err}", flush=True)
        if result.get("policy_rolled_back"):
            print(f"  Policy restored from: {result.get('rollback_from', 'best checkpoint')}", flush=True)
    print("PRIMARY — all vehicles (main success metric):", flush=True)
    print(f"  Baseline: {base_all:,}", flush=True)
    print(f"  DQN:      {dqn_all:,}", flush=True)
    if not invalid and base_all > 0:
        print(f"  Change:   {imp_all:+.1f}%", flush=True)
    elif invalid:
        print("  Change:   n/a (invalid run)", flush=True)

    base_pri = int(result.get("fixed_wait_priority", 0) or result.get("baseline_wait", 0) or 0)
    dqn_pri = int(result.get("dqn_wait_priority", 0) or result.get("dqn_wait", 0) or 0)
    imp_pri = float(result.get("improvement_percent", 0) or result.get("improvement_percent_priority", 0) or 0)
    print("Secondary — bus + emergency:", flush=True)
    print(f"  Baseline: {base_pri:,}  DQN: {dqn_pri:,}", flush=True)
    if not invalid:
        print(f"  Change:   {imp_pri:+.1f}%", flush=True)
    if result.get("best_dqn_wait_all") is not None:
        print(f"  New best checkpoint saved (all-vehicle wait {int(result['best_dqn_wait_all']):,})", flush=True)
    print("=" * 60, flush=True)
