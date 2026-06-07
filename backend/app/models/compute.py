"""
Pydantic models for the compute pipeline (jobs, chunks, work endpoints).
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ── Jobs ──────────────────────────────────────────────────────────────────────

class JobCreateRequest(BaseModel):
    job_type: str = Field(..., pattern="^data-processing$")
    params: dict[str, Any]


class JobPublic(BaseModel):
    id: UUID
    client_id: UUID
    job_type: str
    status: str
    params: dict[str, Any]
    total_chunks: int
    completed_chunks: int
    reward_total: float
    result: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None
    progress: float  # completed_chunks / total_chunks * 100, computed by backend

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    count: int
    jobs: list[JobPublic]


class JobResultResponse(BaseModel):
    id: UUID
    status: str
    result: dict[str, Any]
    total_chunks: int
    completed_chunks: int
    completed_at: datetime | None


# ── Chunks ────────────────────────────────────────────────────────────────────

class ChunkWithPayload(BaseModel):
    chunk_id: UUID
    job_id: UUID
    chunk_index: int
    job_type: str
    payload: dict[str, Any]


class ClaimRequest(BaseModel):
    max_chunks: int = Field(default=3, ge=1, le=10)


class ClaimResponse(BaseModel):
    chunks: list[ChunkWithPayload]


# ── Submit ────────────────────────────────────────────────────────────────────

class SubmitRequest(BaseModel):
    result: dict[str, Any]
    duration_ms: int = Field(..., gt=0)


class SubmitResponse(BaseModel):
    chunk_result_id: UUID
    chunk_id: UUID
    status: str   # chunk status after submit: "assigned" | "done" | "rejected"
    message: str
