"""Saved run reports and comparison history."""

from flowgrid.reports.comparison_history import (
    append_comparison_record,
    clear_history,
    comparison_history_path,
    load_history,
)

__all__ = [
    "append_comparison_record",
    "clear_history",
    "comparison_history_path",
    "load_history",
]
