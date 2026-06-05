from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="La contraseña debe tener al menos 8 caracteres",
    )

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class ProviderPublic(BaseModel):
    """Provider data that is safe to expose to the client."""

    id: str
    full_name: str
    email: str
    trust_score: float
    rank: str
    tasks_completed: int
    success_rate: float
    total_earned: float
    is_online: bool
    cpu_model: str | None = None
    gpu_model: str | None = None
    ram_gb: int | None = None
    storage_gb: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProviderMe(ProviderPublic):
    """Extended provider data returned by GET /auth/me."""

    completion_rate: float
    accuracy: float
    response_time_score: float
    client_rating: float
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    provider: ProviderPublic
