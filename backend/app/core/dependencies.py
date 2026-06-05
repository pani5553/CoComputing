from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_token
from app.db.queries.auth_queries import get_provider_by_id

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_provider(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    FastAPI dependency that validates the Bearer JWT and returns the provider dict.

    Raises:
        401 if the token is missing, expired, or invalid.
        401 if the provider is not found in the database.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    provider_id = verify_token(credentials.credentials)
    if provider_id is None:
        raise unauthorized

    provider = get_provider_by_id(provider_id)
    if provider is None:
        raise unauthorized

    return provider
