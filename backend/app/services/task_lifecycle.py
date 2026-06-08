"""
Task lifecycle orchestration service.

Each function orchestrates DB queries + trust score updates + wallet updates.
Routers call these functions and only handle HTTP responses.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.db.queries import client_queries, task_queries, wallet_queries
from app.db.queries.profile_queries import get_provider_by_id, update_provider
from app.services import trust_score as ts


def accept_task(provider_id: str, task_id: str) -> dict[str, Any]:
    """
    Accept a task for the authenticated provider.

    Steps:
    1. Verify the task exists and is disponible.
    2. Verify the provider has no active assignment for this task.
    3. Atomically decrement slots_left.
    4. Create the assignment row.

    Returns the created assignment dict with task_title.
    """
    task = task_queries.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )

    # Check for existing active assignment
    existing = task_queries.get_active_assignment_for_provider_task(provider_id, task_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tienes esta tarea activa",
        )

    # Atomically decrement slots
    slot_claimed = task_queries.decrement_slots_atomic(task_id)
    if not slot_claimed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No quedan plazas disponibles para esta tarea",
        )

    assignment = task_queries.create_assignment(task_id, provider_id)
    # Attach task_title for the response
    assignment["task_title"] = task["title"]
    return assignment


def start_task(provider_id: str, task_id: str) -> dict[str, Any]:
    """
    Transition a task assignment from 'aceptada' to 'procesando'.

    Returns a dict with assignment details + stages + duration_max_seconds.
    """
    task = task_queries.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )

    assignment = task_queries.get_active_assignment_for_provider_task(provider_id, task_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes ninguna asignación activa para esta tarea",
        )

    if assignment["status"] != "aceptada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes iniciar una tarea que hayas aceptado previamente",
        )

    now_utc = datetime.now(timezone.utc)
    updated = task_queries.update_assignment_status(
        assignment["id"],
        "procesando",
        extra_fields={"started_at": now_utc.isoformat()},
    )

    return {
        "assignment_id": updated["id"],
        "task_id": task_id,
        "status": "procesando",
        "started_at": now_utc,
        "stages": task["stages"],
        "stages_count": len(task["stages"]),
        "duration_max_seconds": task["duration_max"] * 60,
    }


def complete_task(provider_id: str, task_id: str) -> dict[str, Any]:
    """
    Complete a task in processing. Applies all side effects:
    - assignment status → completada
    - wallet balance updated
    - transaction created
    - provider stats and trust score recalculated
    """
    task = task_queries.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )

    assignment = task_queries.get_active_assignment_for_provider_task(provider_id, task_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes ninguna asignación activa para esta tarea",
        )

    if assignment["status"] != "procesando":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes completar una tarea que esté en procesamiento",
        )

    reward = float(task["reward"])
    now_utc = datetime.now(timezone.utc)

    # Update assignment status (will update trust_delta after we compute it)
    task_queries.update_assignment_status(
        assignment["id"],
        "completada",
        extra_fields={
            "completed_at": now_utc.isoformat(),
            "reward_paid": reward,
        },
    )

    # Update provider wallet (credit reward)
    wallet_queries.update_wallet_on_task_complete(provider_id, reward)

    # Create transaction for provider
    wallet_queries.create_transaction(
        provider_id=provider_id,
        amount=reward,
        tx_type="pago_tarea",
        description=f"Recompensa por tarea: {task['title']}",
        status="completada",
        task_id=task_id,
    )

    # Release one escrow slot from the client (if task has a client/escrow)
    if task.get("client_id"):
        client_queries.release_escrow_slot(task_id, task["client_id"], reward)

    # Fetch current provider data
    provider = get_provider_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )

    # Count failed assignments directly from DB for accurate rate calculation
    tasks_failed = task_queries.count_provider_assignments_by_status(provider_id, "fallida")
    tasks_completed = provider["tasks_completed"] + 1  # includes the one just completed

    completion_rate = ts.compute_completion_rate(tasks_completed, tasks_failed)
    success_rate = ts.compute_success_rate(tasks_completed, tasks_failed)

    # Accuracy update
    new_accuracy = ts.update_accuracy_on_complete(float(provider["accuracy"]))

    # Response time update
    accepted_at = _parse_datetime(assignment["accepted_at"])
    started_at = _parse_datetime(assignment["started_at"])
    new_rts = ts.update_response_time_on_complete(
        float(provider["response_time_score"]), accepted_at, started_at
    )

    # Trust score
    new_trust_score = ts.calculate_trust_score(
        completion_rate,
        new_accuracy,
        new_rts,
        float(provider["client_rating"]),
    )
    new_rank = ts.get_rank(new_trust_score)
    trust_delta = round(new_trust_score - float(provider["trust_score"]), 2)

    # Persist updated provider fields (trust_score/rank recalculated by DB trigger too)
    update_provider(
        provider_id,
        {
            "tasks_completed": tasks_completed,
            "completion_rate": completion_rate,
            "accuracy": new_accuracy,
            "response_time_score": new_rts,
            "success_rate": success_rate,
            "total_earned": round(float(provider["total_earned"]) + reward, 2),
        },
    )

    # Persist trust_delta on the assignment
    task_queries.update_assignment_status(
        assignment["id"],
        "completada",
        extra_fields={"trust_delta": trust_delta},
    )

    return {
        "assignment_id": assignment["id"],
        "task_id": task_id,
        "status": "completada",
        "reward_paid": reward,
        "trust_delta": trust_delta,
        "new_trust_score": new_trust_score,
        "new_rank": new_rank,
        "completed_at": now_utc,
    }


def fail_task(provider_id: str, task_id: str) -> dict[str, Any]:
    """
    Report task failure. Applies side effects:
    - assignment status → fallida
    - provider accuracy and response_time_score decremented
    - trust score recalculated (no reward credited)
    """
    task = task_queries.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )

    assignment = task_queries.get_active_assignment_for_provider_task(provider_id, task_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes ninguna asignación activa para esta tarea",
        )

    if assignment["status"] != "procesando":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puedes reportar fallo en una tarea que esté en procesamiento",
        )

    now_utc = datetime.now(timezone.utc)

    # Update assignment
    task_queries.update_assignment_status(
        assignment["id"],
        "fallida",
        extra_fields={"completed_at": now_utc.isoformat()},
    )

    # Fetch current provider data
    provider = get_provider_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )

    tasks_completed = provider["tasks_completed"]
    # Count failed assignments; the current one is already marked 'fallida' above
    tasks_failed = task_queries.count_provider_assignments_by_status(provider_id, "fallida")

    completion_rate = ts.compute_completion_rate(tasks_completed, tasks_failed)
    success_rate = ts.compute_success_rate(tasks_completed, tasks_failed)

    # Accuracy update
    new_accuracy = ts.update_accuracy_on_fail(float(provider["accuracy"]))

    # Response time update
    accepted_at = _parse_datetime(assignment["accepted_at"])
    started_at = _parse_datetime(assignment["started_at"])
    new_rts = ts.update_response_time_on_fail(
        float(provider["response_time_score"]), accepted_at, started_at
    )

    # New trust score
    new_trust_score = ts.calculate_trust_score(
        completion_rate,
        new_accuracy,
        new_rts,
        float(provider["client_rating"]),
    )
    new_rank = ts.get_rank(new_trust_score)
    trust_delta = round(new_trust_score - float(provider["trust_score"]), 2)

    update_provider(
        provider_id,
        {
            "completion_rate": completion_rate,
            "accuracy": new_accuracy,
            "response_time_score": new_rts,
            "success_rate": success_rate,
        },
    )

    # Persist trust_delta on the assignment
    task_queries.update_assignment_status(
        assignment["id"],
        "fallida",
        extra_fields={"trust_delta": trust_delta},
    )

    return {
        "assignment_id": assignment["id"],
        "task_id": task_id,
        "status": "fallida",
        "reward_paid": None,
        "trust_delta": trust_delta,
        "new_trust_score": new_trust_score,
        "new_rank": new_rank,
        "completed_at": now_utc,
    }


def _parse_datetime(value: str | datetime | None) -> datetime:
    """Parse a datetime string or pass through a datetime object, ensuring UTC tzinfo."""
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    # String
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
