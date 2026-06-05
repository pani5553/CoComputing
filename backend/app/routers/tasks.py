"""
Tasks router.

IMPORTANT: Route registration order matters in FastAPI.
Literal routes (/my/history, /assignments/{id}/progress) MUST be registered
BEFORE parameterized routes (/{task_id}) to prevent path conflicts.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_provider
from app.db.queries import task_queries
from app.models.task import (
    ActiveAssignment,
    AssignmentHistoryResponse,
    AssignmentResponse,
    CompleteTaskResponse,
    FailTaskResponse,
    HistoryAssignment,
    ProgressResponse,
    StartTaskResponse,
    TaskListResponse,
    TaskResponse,
)
from app.services import task_lifecycle
from app.services.progress_service import calculate_progress, get_current_stage_index

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/  — Listado de tareas disponibles con filtros
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/", response_model=TaskListResponse)
def list_tasks(
    difficulty: str | None = Query(default=None, description="Comma-separated: facil,medio,dificil"),
    hardware: str | None = Query(default=None, description="Comma-separated: cpu,gpu,mixto"),
    task_type: str | None = Query(default=None),
    min_reward: float | None = Query(default=None, gt=0),
    current_provider: dict = Depends(get_current_provider),
) -> TaskListResponse:
    """
    Return available tasks with optional filters.
    Filters are applied as AND. Only status='disponible' with slots_left > 0.
    Max 50 results ordered by reward DESC.
    """
    difficulty_list: list[str] | None = None
    hardware_list: list[str] | None = None

    if difficulty:
        difficulty_list = [d.strip() for d in difficulty.split(",") if d.strip()]

    if hardware:
        hardware_list = [h.strip() for h in hardware.split(",") if h.strip()]

    tasks = task_queries.get_tasks(
        difficulty=difficulty_list,
        hardware=hardware_list,
        task_type=task_type,
        min_reward=min_reward,
    )

    return TaskListResponse(
        count=len(tasks),
        tasks=[TaskResponse(**t) for t in tasks],
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/my/history  — Historial de asignaciones del proveedor
# MUST be registered BEFORE /{task_id}
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/my/history", response_model=AssignmentHistoryResponse)
def get_my_history(
    current_provider: dict = Depends(get_current_provider),
) -> AssignmentHistoryResponse:
    """Return all task assignments for the authenticated provider, newest first."""
    provider_id: str = current_provider["id"]
    rows = task_queries.get_provider_assignments_history(provider_id)

    assignments = [
        HistoryAssignment(
            id=row["id"],
            task_id=row["task_id"],
            task_title=row["task_title"],
            task_type=row["task_type"],
            status=row["status"],
            reward_paid=float(row["reward_paid"]) if row["reward_paid"] is not None else None,
            trust_delta=float(row["trust_delta"]) if row["trust_delta"] is not None else None,
            accepted_at=row["accepted_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )
        for row in rows
    ]

    return AssignmentHistoryResponse(count=len(assignments), assignments=assignments)


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/assignments/{assignment_id}/progress
# MUST be registered BEFORE /{task_id}
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/assignments/{assignment_id}/progress", response_model=ProgressResponse)
def get_assignment_progress(
    assignment_id: str,
    current_provider: dict = Depends(get_current_provider),
) -> ProgressResponse:
    """
    Return the simulated progress of a task assignment.
    Progress is deterministic: based on elapsed time vs duration_max.
    """
    row = task_queries.get_assignment_with_task(assignment_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada",
        )

    if row["provider_id"] != current_provider["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para realizar esta acción",
        )

    assignment_status: str = row["status"]
    stages: list[str] = row["stages"] if isinstance(row["stages"], list) else list(row["stages"])
    started_at = row["started_at"]

    # Terminal states: return 100% progress
    if assignment_status in ("completada", "fallida"):
        return ProgressResponse(
            assignment_id=row["assignment_id"],
            task_id=row["task_id"],
            task_title=row["task_title"],
            status=assignment_status,
            progress=100.0,
            current_stage_index=len(stages) - 1,
            stages=stages,
            started_at=_normalize_dt(started_at) if started_at else None,
            can_complete=False,
        )

    # Not yet started
    if assignment_status == "aceptada" or started_at is None:
        return ProgressResponse(
            assignment_id=row["assignment_id"],
            task_id=row["task_id"],
            task_title=row["task_title"],
            status=assignment_status,
            progress=0.0,
            current_stage_index=0,
            stages=stages,
            started_at=None,
            can_complete=False,
        )

    # In progress
    started_dt = _normalize_dt(started_at)
    progress = calculate_progress(started_dt, int(row["duration_max"]))
    stage_index = get_current_stage_index(progress, len(stages))
    can_complete = progress >= 80.0

    return ProgressResponse(
        assignment_id=row["assignment_id"],
        task_id=row["task_id"],
        task_title=row["task_title"],
        status=assignment_status,
        progress=progress,
        current_stage_index=stage_index,
        stages=stages,
        started_at=started_dt,
        can_complete=can_complete,
    )


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/{task_id}  — Detalle de tarea
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    current_provider: dict = Depends(get_current_provider),
) -> TaskResponse:
    """Return the full details of a single task, plus any active assignment info."""
    task = task_queries.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada",
        )

    active_assignment: ActiveAssignment | None = None
    assignment = task_queries.get_active_assignment_for_provider_task(
        current_provider["id"], task_id
    )
    if assignment:
        active_assignment = ActiveAssignment(
            id=assignment["id"],
            status=assignment["status"],
            accepted_at=assignment["accepted_at"],
            started_at=assignment.get("started_at"),
        )

    return TaskResponse(**task, active_assignment=active_assignment)


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/accept
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{task_id}/accept", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def accept_task(
    task_id: str,
    current_provider: dict = Depends(get_current_provider),
) -> AssignmentResponse:
    """Accept a task and create the assignment for the authenticated provider."""
    provider_id: str = current_provider["id"]
    assignment = task_lifecycle.accept_task(provider_id, task_id)
    return AssignmentResponse(
        id=assignment["id"],
        task_id=assignment["task_id"],
        task_title=assignment["task_title"],
        provider_id=assignment["provider_id"],
        status=assignment["status"],
        reward_paid=None,
        trust_delta=None,
        accepted_at=assignment["accepted_at"],
        started_at=assignment.get("started_at"),
        completed_at=assignment.get("completed_at"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/start
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{task_id}/start", response_model=StartTaskResponse)
def start_task(
    task_id: str,
    current_provider: dict = Depends(get_current_provider),
) -> StartTaskResponse:
    """Start processing a previously accepted task."""
    provider_id: str = current_provider["id"]
    result = task_lifecycle.start_task(provider_id, task_id)
    return StartTaskResponse(**result)


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/complete
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{task_id}/complete", response_model=CompleteTaskResponse)
def complete_task(
    task_id: str,
    current_provider: dict = Depends(get_current_provider),
) -> CompleteTaskResponse:
    """Complete a task that is currently in processing."""
    provider_id: str = current_provider["id"]
    result = task_lifecycle.complete_task(provider_id, task_id)
    return CompleteTaskResponse(**result)


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/fail
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{task_id}/fail", response_model=FailTaskResponse)
def fail_task(
    task_id: str,
    current_provider: dict = Depends(get_current_provider),
) -> FailTaskResponse:
    """Report failure for a task that is currently in processing."""
    provider_id: str = current_provider["id"]
    result = task_lifecycle.fail_task(provider_id, task_id)
    return FailTaskResponse(**result)


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_dt(value: Any) -> datetime:
    """Parse various datetime representations into a tz-aware UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
