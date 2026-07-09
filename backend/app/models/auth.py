import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# Mitigación básica de Sybil en /auth/register (docs/04-arquitectura.md §15.4):
# EmailStr ya valida sintaxis RFC, pero no detecta puntos consecutivos ni una
# parte local desproporcionadamente larga.
_CONSECUTIVE_DOTS = re.compile(r"\.\.")


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="La contraseña debe tener al menos 8 caracteres",
    )

    @field_validator("email")
    @classmethod
    def email_format_strict(cls, v: str) -> str:
        """
        Validación de formato adicional a EmailStr + normalización a
        minúsculas. La normalización es el cambio con más impacto real:
        sin ella, "Ana@Example.com" y "ana@example.com" se tratarían como
        cuentas distintas por `get_provider_by_email`, evadiendo el límite
        de "una cuenta por email" sin necesitar ningún ataque Sybil.
        """
        local_part = v.split("@", 1)[0]
        if _CONSECUTIVE_DOTS.search(v):
            raise ValueError("El email no puede contener puntos consecutivos")
        if len(local_part) > 64:
            raise ValueError("La parte local del email es demasiado larga")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def email_normalize(cls, v: str) -> str:
        """
        Normaliza el email a minúsculas para que coincida con el valor
        guardado por `RegisterRequest.email_format_strict` (que sí
        normaliza). Sin esto, un usuario que inicia sesión con el email
        exactamente como lo escribió al registrarse (p. ej. con
        mayúsculas) recibe un falso "Credenciales incorrectas", porque
        `get_provider_by_email` compara con `.eq("email", email)` contra
        una columna sin `citext` ni índice `lower()`. No se duplica aquí
        el resto de la validación estricta de formato (puntos
        consecutivos, longitud de la parte local): login no debe
        rechazar por formato, un email inexistente ya se maneja como
        credenciales incorrectas.
        """
        return v.lower()


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
