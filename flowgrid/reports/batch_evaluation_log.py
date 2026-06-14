from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from flowgrid.paths import LOGS_DIR

BATCH_EVALUATION_LOG_PATH = LOGS_DIR / "batch_evaluation.log"

_BLOCK_SPLIT_RE = re.compile(r"(?=^Batch evaluation  )", re.MULTILINE)
_TS_RE = re.compile(r"^Batch evaluation\s+(.+)$", re.MULTILINE)
_MAP_RE = re.compile(r"^Map:\s+(.+?)\s+\(([^)]+)\)\s*$", re.MULTILINE)
_EPISODES_RE = re.compile(r"^Model Training Episodes:\s+(.+)$", re.MULTILINE)
_RUNS_RE = re.compile(
    r"^Runs:\s+(\d+)\s+Inject until:\s+([\d.]+)s\s+Baseline green:\s+([\d.]+)s\s*$",
    re.MULTILINE,
)
_SUCCESS_RE = re.compile(
    r"^Successful runs:\s+(\d+)\s+/\s+(\d+)\s+\(failed:\s+(\d+)\)\s*$",
    re.MULTILINE,
)
_WIN_RATE_RE = re.compile(
    r"^DQN win rate:\s+(\d+)\s+/\s+(\d+)\s+\(([\d.]+)%\)\s*$",
    re.MULTILINE,
)
_AVG_WAIT_RE = re.compile(
    r"^Avg total wait:\s+baseline\s+([\d,.]+)\s+\|\s+DQN\s+([\d,.]+)\s*$",
    re.MULTILINE,
)
_AVG_IMPROVE_RE = re.compile(
    r"^Avg wait improvement:\s+([+-]?[\d.]+)%",
    re.MULTILINE,
)
_ZERO_SUMMARY_RE = re.compile(r"^SUMMARY:\s+0 successful runs", re.MULTILINE)


@dataclass(frozen=True)
class BatchEvaluationRecord:
    timestamp: str
    map_display: str
    map_id: str
    training_episodes: int | None
    runs_total: int
    runs_ok: int
    runs_failed: int
    win_rate_pct: float | None
    avg_improvement_pct: float | None
    avg_baseline_wait: float | None
    avg_dqn_wait: float | None
    inject_seconds: float | None
    baseline_green: float | None


def batch_evaluation_log_path() -> Path:
    return BATCH_EVALUATION_LOG_PATH


def _parse_number(raw: str) -> float:
    return float(str(raw).replace(",", "").strip())


def _parse_episodes(raw: str | None) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() == "unknown":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _last_match(pattern: re.Pattern[str], text: str) -> re.Match[str] | None:
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    return matches[-1]


def _parse_block(block: str) -> BatchEvaluationRecord | None:
    stripped = block.strip()
    if not stripped.startswith("Batch evaluation"):
        return None
    ts_match = _TS_RE.search(stripped)
    map_match = _MAP_RE.search(stripped)
    if not ts_match or not map_match:
        return None

    summary_start = stripped.find("STATISTICAL SUMMARY")
    summary_text = stripped[summary_start:] if summary_start >= 0 else stripped
    header_text = stripped[:summary_start] if summary_start >= 0 else stripped

    episodes_match = _last_match(_EPISODES_RE, summary_text) or _last_match(_EPISODES_RE, header_text)
    runs_match = _RUNS_RE.search(header_text)
    success_match = _SUCCESS_RE.search(summary_text)
    win_match = _WIN_RATE_RE.search(summary_text)
    wait_match = _AVG_WAIT_RE.search(summary_text)
    improve_match = _AVG_IMPROVE_RE.search(summary_text)
    zero_summary = _ZERO_SUMMARY_RE.search(summary_text)

    runs_total = int(runs_match.group(1)) if runs_match else 0
    inject_seconds = _parse_number(runs_match.group(2)) if runs_match else None
    baseline_green = _parse_number(runs_match.group(3)) if runs_match else None

    if success_match:
        runs_ok = int(success_match.group(1))
        runs_total = int(success_match.group(2))
        runs_failed = int(success_match.group(3))
    elif zero_summary:
        runs_ok = 0
        failed_match = re.search(r"\(failed:\s*(\d+)\)", stripped)
        runs_failed = int(failed_match.group(1)) if failed_match else runs_total
    else:
        runs_ok = 0
        runs_failed = 0

    win_rate_pct = float(win_match.group(3)) if win_match else None
    avg_improvement_pct = float(improve_match.group(1)) if improve_match else None
    avg_baseline_wait = _parse_number(wait_match.group(1)) if wait_match else None
    avg_dqn_wait = _parse_number(wait_match.group(2)) if wait_match else None

    return BatchEvaluationRecord(
        timestamp=ts_match.group(1).strip(),
        map_display=map_match.group(1).strip(),
        map_id=map_match.group(2).strip(),
        training_episodes=_parse_episodes(episodes_match.group(1) if episodes_match else None),
        runs_total=runs_total,
        runs_ok=runs_ok,
        runs_failed=runs_failed,
        win_rate_pct=win_rate_pct,
        avg_improvement_pct=avg_improvement_pct,
        avg_baseline_wait=avg_baseline_wait,
        avg_dqn_wait=avg_dqn_wait,
        inject_seconds=inject_seconds,
        baseline_green=baseline_green,
    )


def parse_batch_evaluation_log(path: str | Path | None = None) -> list[BatchEvaluationRecord]:
    log_path = Path(path) if path is not None else batch_evaluation_log_path()
    if not log_path.is_file():
        return []
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return []
    blocks = _BLOCK_SPLIT_RE.split(text)
    records: list[BatchEvaluationRecord] = []
    for block in blocks:
        parsed = _parse_block(block)
        if parsed is not None:
            records.append(parsed)
    return records
