from __future__ import annotations

import sys
from datetime import datetime, timezone


def terminal_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%d-%m-%Y %H:%M:%S")


def terminal_line(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return terminal_timestamp()
    return f"{terminal_timestamp()} {text}"


def terminal_print(message: str, *, end: str = "\n", flush: bool = True) -> None:
    print(terminal_line(message), end=end, flush=flush, file=sys.stdout)
