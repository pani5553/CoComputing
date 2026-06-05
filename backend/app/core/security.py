from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against the stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_data: dict[str, Any] | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The token subject (provider UUID string).
        extra_data: Optional additional claims to embed in the token.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.jwt_expire_days)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }

    if extra_data:
        payload.update(extra_data)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> str | None:
    """
    Verify a JWT token and return the subject (provider UUID).

    Returns:
        The provider UUID string, or None if the token is invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        subject: str | None = payload.get("sub")
        return subject
    except JWTError:
        return None
