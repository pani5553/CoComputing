from datetime import datetime

from pydantic import BaseModel


class ActiveAssignment(BaseModel):
    id: str
    status: str
    accepted_at: datetime
    started_at: datetime | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    task_type: str
    description: str
    reward: float
    duration_min: int
    duration_max: int
    difficulty: str
    hardware_required: str
    total_slots: int
    slots_left: int
    stages: list[str]
    requester_name: str
    status: str
    created_at: datetime
    active_assignment: ActiveAssignment | None = None


class TaskListResponse(BaseModel):
    count: int
    tasks: list[TaskResponse]


class AssignmentResponse(BaseModel):
    id: str
    task_id: str
    task_title: str
    provider_id: str
    status: str
    reward_paid: float | None = None
    trust_delta: float | None = None
    accepted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class StartTaskResponse(BaseModel):
    assignment_id: str
    task_id: str
    status: str
    started_at: datetime
    stages: list[str]
    stages_count: int
    duration_max_seconds: int


class CompleteTaskResponse(BaseModel):
    assignment_id: str
    task_id: str
    status: str
    reward_paid: float
    trust_delta: float
    new_trust_score: float
    new_rank: str
    completed_at: datetime


class FailTaskResponse(BaseModel):
    assignment_id: str
    task_id: str
    status: str
    reward_paid: float | None = None
    trust_delta: float
    new_trust_score: float
    new_rank: str
    completed_at: datetime


class HistoryAssignment(BaseModel):
    id: str
    task_id: str
    task_title: str
    task_type: str
    status: str
    reward_paid: float | None = None
    trust_delta: float | None = None
    accepted_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AssignmentHistoryResponse(BaseModel):
    count: int
    assignments: list[HistoryAssignment]


class ProgressResponse(BaseModel):
    assignment_id: str
    task_id: str
    task_title: str
    status: str
    progress: float
    current_stage_index: int
    stages: list[str]
    started_at: datetime | None = None
    can_complete: bool
