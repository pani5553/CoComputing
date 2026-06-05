from datetime import datetime

from pydantic import BaseModel, Field


class TrustScoreDetail(BaseModel):
    completion_rate: float
    completion_rate_weight: float = 0.40
    accuracy: float
    accuracy_weight: float = 0.30
    response_time_score: float
    response_time_weight: float = 0.20
    client_rating: float
    client_rating_weight: float = 0.10


class RankInfo(BaseModel):
    current_rank: str
    current_rank_min: int
    current_rank_max: int
    next_rank: str | None = None
    next_rank_min: int | None = None
    points_to_next_rank: float | None = None


class HardwareInfo(BaseModel):
    cpu_model: str | None = None
    gpu_model: str | None = None
    ram_gb: int | None = None
    storage_gb: int | None = None


class ProviderProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    trust_score: float
    rank: str
    tasks_completed: int
    success_rate: float
    total_earned: float
    is_online: bool
    created_at: datetime
    trust_score_detail: TrustScoreDetail
    rank_info: RankInfo
    hardware: HardwareInfo


class HardwareUpdate(BaseModel):
    cpu_model: str = Field(..., min_length=1, max_length=200)
    gpu_model: str | None = Field(default=None, max_length=200)
    ram_gb: int = Field(..., ge=1)
    storage_gb: int = Field(..., ge=1)


class HardwareUpdateResponse(BaseModel):
    cpu_model: str | None
    gpu_model: str | None
    ram_gb: int | None
    storage_gb: int | None
    updated_at: datetime


class OnlineToggleRequest(BaseModel):
    is_online: bool


class OnlineToggleResponse(BaseModel):
    is_online: bool
    updated_at: datetime


class NameUpdateRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)


class NameUpdateResponse(BaseModel):
    full_name: str
    updated_at: datetime
