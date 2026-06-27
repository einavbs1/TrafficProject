"""Persist baseline vs DQN comparison runs to JSON for the Reports tab."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowgrid.paths import DATA_DIR

HISTORY_VERSION = 1
REPORTS_DIR = DATA_DIR / "reports"
COMPARISON_HISTORY_PATH = REPORTS_DIR / "comparison_history.json"


def comparison_history_path() -> Path:
    return COMPARISON_HISTORY_PATH


def _ensure_file() -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not COMPARISON_HISTORY_PATH.is_file():
        data = {"version": HISTORY_VERSION, "records": []}
        COMPARISON_HISTORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    try:
        data = json.loads(COMPARISON_HISTORY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {"version": HISTORY_VERSION, "records": []}
    if "records" not in data:
        data["records"] = []
    data["version"] = HISTORY_VERSION
    return data


def load_history() -> list[dict[str, Any]]:
    """All comparison records, oldest first."""
    data = _ensure_file()
    records = list(data.get("records", []))
    records.sort(key=lambda r: r.get("timestamp", ""))
    return records


def _save_all(records: list[dict[str, Any]]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"version": HISTORY_VERSION, "records": records}
    COMPARISON_HISTORY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_comparison_record(record: dict[str, Any]) -> dict[str, Any]:
    """Add one comparison run; returns the stored record (with id and timestamp)."""
    data = _ensure_file()
    records: list[dict[str, Any]] = list(data.get("records", []))
    now = datetime.now(timezone.utc).astimezone()
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": now.isoformat(timespec="seconds"),
        "timestamp_display": now.strftime("%Y-%m-%d %H:%M:%S"),
        **record,
    }
    records.append(entry)
    _save_all(records)
    return entry


def clear_history() -> int:
    """Remove all records. Returns count cleared."""
    data = _ensure_file()
    n = len(data.get("records", []))
    _save_all([])
    return n
