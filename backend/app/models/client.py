"""
Pydantic models for the client-side API (deposit, publish tasks, escrow).
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ─── Deposit ──────────────────────────────────────────────────────────────────

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in CC to deposit (simulated)")

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)


class DepositResponse(BaseModel):
    transaction_id: str
    amount: float
    new_available_balance: float
    message: str


# ─── Create task ──────────────────────────────────────────────────────────────

class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    task_type: Literal[
        "renderizado_3d",
        "entrenamiento_ml",
        "transcodificacion_video",
        "analisis_datos",
        "simulacion_fisica",
    ]
    description: str = Field(..., min_length=10, max_length=2000)
    reward: float = Field(..., gt=0)
    difficulty: Literal["facil", "medio", "dificil"]
    hardware_required: Literal["cpu", "gpu", "mixto"]
    total_slots: int = Field(..., ge=1, le=100)
    duration_min: int = Field(..., ge=1)
    duration_max: int = Field(..., ge=1)
    stages: list[str] = Field(..., min_length=1, max_length=10)
    requester_name: str = Field(..., min_length=1, max_length=200)

    @field_validator("reward")
    @classmethod
    def round_reward(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("duration_max")
    @classmethod
    def duration_max_gte_min(cls, v: int, info) -> int:
        duration_min = info.data.get("duration_min")
        if duration_min is not None and v < duration_min:
            raise ValueError("duration_max must be >= duration_min")
        return v

    @field_validator("stages")
    @classmethod
    def stages_not_empty_strings(cls, v: list[str]) -> list[str]:
        for s in v:
            if not s.strip():
                raise ValueError("Each stage must be a non-empty string")
        return v


class CreateTaskResponse(BaseModel):
    task_id: str
    title: str
    reward: float
    total_slots: int
    escrow_total: float
    new_available_balance: float
    message: str


# ─── Client task list ─────────────────────────────────────────────────────────

class ClientTaskSummary(BaseModel):
    id: str
    title: str
    task_type: str
    reward: float
    total_slots: int
    slots_left: int
    slots_completed: int
    status: str
    escrow_held: float
    escrow_released: float
    created_at: datetime


class ClientTaskListResponse(BaseModel):
    count: int
    tasks: list[ClientTaskSummary]


# ─── Client task detail ───────────────────────────────────────────────────────

class AssignmentInfo(BaseModel):
    id: str
    provider_id: str
    provider_name: str
    status: str
    reward_paid: float | None = None
    accepted_at: datetime
    completed_at: datetime | None = None


class ClientTaskDetailResponse(BaseModel):
    id: str
    title: str
    task_type: str
    description: str
    reward: float
    difficulty: str
    hardware_required: str
    total_slots: int
    slots_left: int
    status: str
    escrow_held: float
    escrow_released: float
    assignments: list[AssignmentInfo]
    created_at: datetime


# ─── Cancel task ──────────────────────────────────────────────────────────────

class CancelTaskResponse(BaseModel):
    task_id: str
    refund_amount: float
    new_available_balance: float
    message: str
