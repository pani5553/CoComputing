"""
Database queries for tasks and task_assignments.
Atomic slot decrement uses a raw SQL UPDATE ... WHERE slots_left > 0 via psycopg2
to guarantee race-condition-free reservation.
"""
from typing import Any

import psycopg2
import psycopg2.extras

from app.core.config import settings
from app.db.client import get_supabase


# ──────────────────────────────────────────────────────────────────────────────
# Task queries
# ──────────────────────────────────────────────────────────────────────────────


def get_tasks(
    difficulty: list[str] | None = None,
    hardware: list[str] | None = None,
    task_type: str | None = None,
    min_reward: float | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch available tasks (status='disponible', slots_left>0) with optional filters.
    Returns at most 50 results ordered by reward DESC.
    """
    query = (
        get_supabase().table("tasks")
        .select("*")
        .eq("status", "disponible")
        .gt("slots_left", 0)
        .order("reward", desc=True)
        .limit(50)
    )

    if difficulty:
        query = query.in_("difficulty", difficulty)

    if hardware:
        query = query.in_("hardware_required", hardware)

    if task_type:
        query = query.eq("task_type", task_type)

    if min_reward is not None:
        query = query.gte("reward", min_reward)

    response = query.execute()
    return response.data or []


def get_task_by_id(task_id: str) -> dict[str, Any] | None:
    """Fetch a single task by UUID. Returns None if not found."""
    response = (
        get_supabase().table("tasks")
        .select("*")
        .eq("id", task_id)
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def decrement_slots_atomic(task_id: str) -> bool:
    """
    Atomically decrement slots_left by 1 using a raw SQL query with
    WHERE slots_left > 0 to prevent over-booking.

    Returns True if a slot was successfully claimed, False if no slots remain.
    """
    sql = """
        UPDATE tasks
        SET slots_left = slots_left - 1,
            updated_at = now()
        WHERE id = %s
          AND slots_left > 0
        RETURNING slots_left
    """
    with psycopg2.connect(settings.supabase_db_url, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (task_id,))
            result = cur.fetchone()
            conn.commit()
    return result is not None


# ──────────────────────────────────────────────────────────────────────────────
# Task assignment queries
# ──────────────────────────────────────────────────────────────────────────────


def get_assignment_by_id(assignment_id: str) -> dict[str, Any] | None:
    """Fetch a task_assignment row by UUID. Returns None if not found."""
    response = (
        get_supabase().table("task_assignments")
        .select("*")
        .eq("id", assignment_id)
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def get_active_assignment_for_provider_task(
    provider_id: str,
    task_id: str,
) -> dict[str, Any] | None:
    """
    Return the active assignment (status in aceptada, procesando) for a specific
    provider + task combination. Returns None if there is no active assignment.
    """
    response = (
        get_supabase().table("task_assignments")
        .select("*")
        .eq("provider_id", provider_id)
        .eq("task_id", task_id)
        .in_("status", ["aceptada", "procesando"])
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def get_provider_assignments_history(provider_id: str) -> list[dict[str, Any]]:
    """
    Fetch all assignments for a provider joined with the task title and type,
    ordered by created_at DESC.
    Uses a raw SQL query so we can join task data in one round-trip.
    """
    sql = """
        SELECT
            ta.id,
            ta.task_id,
            t.title    AS task_title,
            t.task_type,
            ta.status,
            ta.reward_paid,
            ta.trust_delta,
            ta.accepted_at,
            ta.started_at,
            ta.completed_at
        FROM task_assignments ta
        JOIN tasks t ON t.id = ta.task_id
        WHERE ta.provider_id = %s
        ORDER BY ta.created_at DESC
    """
    with psycopg2.connect(settings.supabase_db_url, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (provider_id,))
            rows = cur.fetchall()
    return [dict(row) for row in rows]


def create_assignment(task_id: str, provider_id: str) -> dict[str, Any]:
    """Insert a new task_assignment row with status='aceptada'."""
    response = (
        get_supabase().table("task_assignments")
        .insert(
            {
                "task_id": task_id,
                "provider_id": provider_id,
                "status": "aceptada",
            }
        )
        .execute()
    )
    return response.data[0]


def update_assignment_status(
    assignment_id: str,
    status: str,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Update the status of a task_assignment and optional extra fields
    (started_at, completed_at, reward_paid, trust_delta).
    Returns the updated row.
    """
    payload: dict[str, Any] = {"status": status}
    if extra_fields:
        payload.update(extra_fields)

    response = (
        get_supabase().table("task_assignments")
        .update(payload)
        .eq("id", assignment_id)
        .execute()
    )
    return response.data[0]


def count_provider_assignments_by_status(provider_id: str, status: str) -> int:
    """Count assignments for a provider filtered by status."""
    response = (
        get_supabase().table("task_assignments")
        .select("id", count="exact")
        .eq("provider_id", provider_id)
        .eq("status", status)
        .execute()
    )
    return response.count or 0


def get_assignment_with_task(assignment_id: str) -> dict[str, Any] | None:
    """
    Fetch assignment data joined with task (title, stages, duration_max).
    Used by the progress endpoint. Returns None if not found.
    """
    sql = """
        SELECT
            ta.id              AS assignment_id,
            ta.task_id,
            t.title            AS task_title,
            ta.status,
            ta.started_at,
            ta.completed_at,
            ta.provider_id,
            t.stages,
            t.duration_max
        FROM task_assignments ta
        JOIN tasks t ON t.id = ta.task_id
        WHERE ta.id = %s
        LIMIT 1
    """
    with psycopg2.connect(settings.supabase_db_url, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (assignment_id,))
            row = cur.fetchone()
    if row is None:
        return None
    return dict(row)
