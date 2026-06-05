"""
Trust score calculation and component update logic.

Formula:
    trust_score = completion_rate * 0.40
                + accuracy * 0.30
                + response_time_score * 0.20
                + client_rating * 0.10

All component values are in the range [0, 100].
"""
from datetime import datetime, timezone
from typing import Any


RANK_THRESHOLDS = [
    ("elite", 90.0, 100.0),
    ("experto", 75.0, 89.99),
    ("confiable", 50.0, 74.99),
    ("nuevo", 0.0, 49.99),
]

RANK_BOUNDARIES = {
    "nuevo":     {"min": 0,  "max": 49},
    "confiable": {"min": 50, "max": 74},
    "experto":   {"min": 75, "max": 89},
    "elite":     {"min": 90, "max": 100},
}

RANK_ORDER = ["nuevo", "confiable", "experto", "elite"]


def calculate_trust_score(
    completion_rate: float,
    accuracy: float,
    response_time_score: float,
    client_rating: float,
) -> float:
    """Compute trust_score and clamp to [0.00, 100.00] with 2 decimal places."""
    score = (
        completion_rate * 0.40
        + accuracy * 0.30
        + response_time_score * 0.20
        + client_rating * 0.10
    )
    return round(max(0.0, min(100.0, score)), 2)


def get_rank(trust_score: float) -> str:
    """Return the rank string for a given trust_score."""
    if trust_score >= 90.0:
        return "elite"
    if trust_score >= 75.0:
        return "experto"
    if trust_score >= 50.0:
        return "confiable"
    return "nuevo"


def build_rank_info(trust_score: float, rank: str) -> dict[str, Any]:
    """Build the rank_info dict for the profile endpoint."""
    bounds = RANK_BOUNDARIES[rank]
    rank_index = RANK_ORDER.index(rank)

    if rank == "elite":
        return {
            "current_rank": rank,
            "current_rank_min": bounds["min"],
            "current_rank_max": bounds["max"],
            "next_rank": None,
            "next_rank_min": None,
            "points_to_next_rank": None,
        }

    next_rank = RANK_ORDER[rank_index + 1]
    next_bounds = RANK_BOUNDARIES[next_rank]
    points_to_next = round(next_bounds["min"] - trust_score, 2)

    return {
        "current_rank": rank,
        "current_rank_min": bounds["min"],
        "current_rank_max": bounds["max"],
        "next_rank": next_rank,
        "next_rank_min": next_bounds["min"],
        "points_to_next_rank": max(0.0, points_to_next),
    }


def update_accuracy_on_complete(current_accuracy: float) -> float:
    """Increase accuracy by 2 on task completion, clamped to 100."""
    return round(min(current_accuracy + 2.0, 100.0), 2)


def update_accuracy_on_fail(current_accuracy: float) -> float:
    """Decrease accuracy by 5 on task failure, clamped to 0."""
    return round(max(current_accuracy - 5.0, 0.0), 2)


def update_response_time_on_complete(
    current_rts: float,
    accepted_at: datetime,
    started_at: datetime,
) -> float:
    """
    +5 if started_at - accepted_at < 10 min,
    -5 if started_at - accepted_at > 60 min,
    no change otherwise.
    """
    elapsed_minutes = (started_at - accepted_at).total_seconds() / 60.0
    if elapsed_minutes < 10.0:
        return round(min(current_rts + 5.0, 100.0), 2)
    if elapsed_minutes > 60.0:
        return round(max(current_rts - 5.0, 0.0), 2)
    return round(current_rts, 2)


def update_response_time_on_fail(
    current_rts: float,
    accepted_at: datetime,
    started_at: datetime,
) -> float:
    """
    -5 if started_at - accepted_at > 60 min,
    no change otherwise.
    """
    elapsed_minutes = (started_at - accepted_at).total_seconds() / 60.0
    if elapsed_minutes > 60.0:
        return round(max(current_rts - 5.0, 0.0), 2)
    return round(current_rts, 2)


def compute_success_rate(tasks_completed: int, tasks_failed: int) -> float:
    """success_rate = completed / (completed + failed) * 100, or 0 if none."""
    total = tasks_completed + tasks_failed
    if total == 0:
        return 0.0
    return round((tasks_completed / total) * 100.0, 2)


def compute_completion_rate(tasks_completed: int, tasks_failed: int) -> float:
    """Same formula as success_rate — completion_rate component for Trust Score."""
    return compute_success_rate(tasks_completed, tasks_failed)
