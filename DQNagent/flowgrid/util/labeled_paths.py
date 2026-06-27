from __future__ import annotations

import re
from pathlib import Path

from flowgrid.paths import DQN_TRAINING_LOG_PATH, LOGS_DIR


def slug_label(label: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "_", (label or "").strip())
    return s[:64] or "run"


def training_log_path_for_label(label: str | None) -> Path:
    if not label or not str(label).strip():
        return DQN_TRAINING_LOG_PATH
    return LOGS_DIR / f"dqn_training_log_{slug_label(label)}.jsonl"


def batch_eval_log_path_for_label(label: str | None) -> Path:
    if not label or not str(label).strip():
        return LOGS_DIR / "batch_evaluation.log"
    return LOGS_DIR / f"batch_evaluation_{slug_label(label)}.log"


def checkpoint_eval_log_path_for_label(label: str | None) -> Path:
    if not label or not str(label).strip():
        return LOGS_DIR / "checkpoint_evaluation.log"
    return LOGS_DIR / f"checkpoint_evaluation_{slug_label(label)}.log"
