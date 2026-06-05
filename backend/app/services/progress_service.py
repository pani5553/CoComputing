"""
Deterministic progress simulation for task processing.

Progress is based solely on elapsed wall-clock time vs the task's
duration_max in minutes. No randomness — the same elapsed time always
yields the same percentage.
"""
import math
from datetime import datetime, timezone


def calculate_progress(started_at: datetime, duration_max_minutes: int) -> float:
    """
    Calculate simulated progress as a percentage.

    progress = min((elapsed_seconds / duration_max_seconds) * 100, 99.0)

    Returns a float rounded to 1 decimal, in the range [0.0, 99.0].
    The progress never reaches 100 automatically; the provider must press
    "Completar" to finalize the task.
    """
    now = datetime.now(timezone.utc)

    # Ensure started_at is tz-aware
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    elapsed_seconds = (now - started_at).total_seconds()
    duration_max_seconds = duration_max_minutes * 60

    if duration_max_seconds <= 0:
        return 99.0

    raw_progress = (elapsed_seconds / duration_max_seconds) * 100.0
    clamped = min(raw_progress, 99.0)
    return round(clamped, 1)


def get_current_stage_index(progress: float, total_stages: int) -> int:
    """
    Map a progress percentage [0..99] to a stage index [0..total_stages-1].

    current_stage_index = min(floor((progress / 100) * total_stages), total_stages - 1)
    """
    if total_stages <= 0:
        return 0
    index = math.floor((progress / 100.0) * total_stages)
    return min(index, total_stages - 1)
