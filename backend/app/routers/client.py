"""
Client router: deposit, publish tasks, manage published tasks.
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_provider
from app.models.client import (
    CancelTaskResponse,
    ClientTaskDetailResponse,
    ClientTaskListResponse,
    CreateTaskRequest,
    CreateTaskResponse,
    DepositRequest,
    DepositResponse,
)
from app.services import client_service

router = APIRouter()


@router.post("/deposit", response_model=DepositResponse)
def deposit(
    payload: DepositRequest,
    current_provider: dict = Depends(get_current_provider),
) -> DepositResponse:
    """Simulate a CC deposit for the authenticated user."""
    result = client_service.deposit(
        client_id=current_provider["id"],
        amount=payload.amount,
    )
    return DepositResponse(**result)


@router.post("/tasks", response_model=CreateTaskResponse, status_code=201)
def create_task(
    payload: CreateTaskRequest,
    current_provider: dict = Depends(get_current_provider),
) -> CreateTaskResponse:
    """Publish a new task. Locks escrow = reward × total_slots from available balance."""
    result = client_service.create_task(
        client_id=current_provider["id"],
        title=payload.title,
        task_type=payload.task_type,
        description=payload.description,
        reward=payload.reward,
        difficulty=payload.difficulty,
        hardware_required=payload.hardware_required,
        total_slots=payload.total_slots,
        duration_min=payload.duration_min,
        duration_max=payload.duration_max,
        stages=payload.stages,
        requester_name=payload.requester_name,
    )
    return CreateTaskResponse(**result)


@router.get("/tasks", response_model=ClientTaskListResponse)
def list_my_tasks(
    current_provider: dict = Depends(get_current_provider),
) -> ClientTaskListResponse:
    """Return all tasks published by the authenticated client."""
    result = client_service.get_my_tasks(current_provider["id"])
    return ClientTaskListResponse(**result)


@router.get("/tasks/{task_id}", response_model=ClientTaskDetailResponse)
def get_task_detail(
    task_id: str,
    current_provider: dict = Depends(get_current_provider),
) -> ClientTaskDetailResponse:
    """Return full detail of a published task (assignments, escrow)."""
    result = client_service.get_task_detail(current_provider["id"], task_id)
    return ClientTaskDetailResponse(**result)


@router.post("/tasks/{task_id}/cancel", response_model=CancelTaskResponse)
def cancel_task(
    task_id: str,
    current_provider: dict = Depends(get_current_provider),
) -> CancelTaskResponse:
    """Cancel a task and refund the unreleased escrow."""
    result = client_service.cancel_task(current_provider["id"], task_id)
    return CancelTaskResponse(**result)
