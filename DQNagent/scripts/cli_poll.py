"""Shared terminal polling for FlowGrid background jobs."""
from __future__ import annotations

import sys
import time
from typing import Callable


def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def poll_job(
    runner,
    job_id: str,
    *,
    poll_s: float = 0.5,
    on_message: Callable[[str, float, dict], None] | None = None,
    on_episode_line: Callable[[str], None] | None = None,
) -> object | None:
    """
    Block until job completes. Calls on_message(message, progress_0_1, result_dict) when message changes.
    If on_episode_line set, also prints each new training episode line from result.
    """
    last_msg = ""
    last_episodes_done = 0
    while True:
        job = runner.get_job(job_id)
        if not job:
            time.sleep(poll_s)
            continue
        msg = job.message or job.status or ""
        result = job.result or {}
        episodes_done = int(result.get("episodes_done", 0) or 0)

        if on_episode_line and episodes_done > last_episodes_done:
            on_episode_line(msg)
            last_episodes_done = episodes_done
        elif msg != last_msg:
            last_msg = msg
            if on_message:
                on_message(msg, float(job.progress), result)

        if job.status in ("completed", "failed"):
            return job
        time.sleep(poll_s)
