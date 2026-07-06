"""
Database queries for tasks and task_assignments.
Uses Supabase REST API exclusively (no psycopg2).
"""
from typing import Any
from datetime import datetime

from app.db.client import get_supabase
from app.db.supabase_client import supabase


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
    Atomically decrement slots_left by 1 using Supabase REST API.
    Uses a conditional update to prevent race conditions.
    
    Returns True if a slot was successfully claimed, False if no slots remain.
    """
    try:
        # Get current task state
        response = get_supabase().table("tasks").select("slots_left").eq("id", task_id).limit(1).execute()
        if not response.data:
            return False
        
        current_slots = response.data[0]["slots_left"]
        
        # If no slots left, return False
        if current_slots <= 0:
            return False
        
        # Try to update - decrement by 1
        # Using eq() for slots_left ensures only one client succeeds if multiple try simultaneously
        update_response = get_supabase().table("tasks").update({
            "slots_left": current_slots - 1,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }).eq("id", task_id).eq("slots_left", current_slots).execute()
        
        # If update succeeded (data is not empty), we got the slot
        return bool(update_response.data)
    except Exception as e:
        print(f"Error decrementing slots: {e}")
        return False


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
    Uses Supabase REST API.
    """
    try:
        response = supabase.table("task_assignments").select(
            "id, task_id, status, reward_paid, trust_delta, accepted_at, started_at, completed_at, tasks(title, task_type)"
        ).eq("provider_id", provider_id).order("created_at", desc=True).execute()
        
        # Flatten the nested task data
        result = []
        for row in response.data:
            flattened = {
                "id": row["id"],
                "task_id": row["task_id"],
                "task_title": row["tasks"]["title"] if row.get("tasks") else None,
                "task_type": row["tasks"]["task_type"] if row.get("tasks") else None,
                "status": row["status"],
                "reward_paid": row["reward_paid"],
                "trust_delta": row["trust_delta"],
                "accepted_at": row["accepted_at"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"]
            }
            result.append(flattened)
        
        return result
    except Exception as e:
        print(f"Error fetching provider history: {e}")
        return []


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
    Uses Supabase REST API with foreign key join.
    """
    try:
        response = (
            get_supabase().table("task_assignments")
            .select("id, task_id, status, started_at, completed_at, provider_id, tasks(title, stages, duration_max)")
            .eq("id", assignment_id)
            .limit(1)
            .execute()
        )
        
        if not response.data:
            return None
        
        row = response.data[0]
        task_data = row.get("tasks", {}) or {}
        
        # Flatten the structure
        return {
            "assignment_id": row["id"],
            "task_id": row["task_id"],
            "task_title": task_data.get("title"),
            "status": row["status"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "provider_id": row["provider_id"],
            "stages": task_data.get("stages"),
            "duration_max": task_data.get("duration_max")
        }
    except Exception as e:
        print(f"Error fetching assignment with task: {e}")
        return None