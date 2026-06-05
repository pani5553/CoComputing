"""
Authentication router: register, login, and token validation.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.dependencies import get_current_provider
from app.core.security import create_access_token, hash_password, verify_password
from app.db.queries.auth_queries import (
    create_provider,
    create_wallet_for_provider,
    get_provider_by_email,
)
from app.models.auth import LoginRequest, ProviderMe, ProviderPublic, RegisterRequest, TokenResponse

router = APIRouter()


@router.post("/register", response_model=ProviderPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> ProviderPublic:
    """
    Register a new provider account.
    Creates the provider row and the linked wallet (all balances at 0).
    Returns 409 if the email is already registered.
    """
    existing = get_provider_by_email(payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este email ya está registrado",
        )

    password_hash = hash_password(payload.password)

    try:
        provider = create_provider(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=password_hash,
        )
    except Exception:
        # Catch any DB-level duplicate constraint race condition
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este email ya está registrado",
        )

    # Create the linked wallet
    create_wallet_for_provider(provider["id"])

    return ProviderPublic(**provider)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    """
    Authenticate a provider and return a JWT.
    Uses the same error message for unknown email and wrong password to prevent
    user enumeration.
    """
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales incorrectas",
    )

    provider = get_provider_by_email(payload.email)
    if provider is None:
        raise invalid_credentials

    if not verify_password(payload.password, provider["password_hash"]):
        raise invalid_credentials

    token = create_access_token(subject=provider["id"])

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_expire_seconds,
        provider=ProviderPublic(**provider),
    )


@router.get("/me", response_model=ProviderMe)
def me(current_provider: dict = Depends(get_current_provider)) -> ProviderMe:
    """Return the full profile of the authenticated provider."""
    return ProviderMe(**current_provider)
