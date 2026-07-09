"""
Tests for authentication endpoints.

Coverage:
- POST /auth/register: success, duplicate email, short password
- POST /auth/login: success, wrong email, wrong password
- GET /auth/me: success, invalid token
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.auth import RegisterRequest
from tests.conftest import PROVIDER_ID


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/register
# ──────────────────────────────────────────────────────────────────────────────


def test_register_success(unauthenticated_client: TestClient, mock_provider: dict) -> None:
    """Happy path: new provider registers successfully."""
    with (
        patch("app.routers.auth.get_provider_by_email", return_value=None),
        patch("app.routers.auth.create_provider", return_value=mock_provider),
        patch("app.routers.auth.create_wallet_for_provider", return_value={"id": "wallet-1"}),
    ):
        response = unauthenticated_client.post(
            "/auth/register",
            json={
                "full_name": "Test Provider",
                "email": "test@example.com",
                "password": "password123",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test Provider"
    assert "password_hash" not in data
    assert data["rank"] == "confiable"
    assert data["tasks_completed"] == 5


def test_register_duplicate_email(unauthenticated_client: TestClient, mock_provider: dict) -> None:
    """Registration fails with 409 when email already exists."""
    with patch("app.routers.auth.get_provider_by_email", return_value=mock_provider):
        response = unauthenticated_client.post(
            "/auth/register",
            json={
                "full_name": "Another Provider",
                "email": "test@example.com",
                "password": "password123",
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Este email ya está registrado"


def test_register_short_password(unauthenticated_client: TestClient) -> None:
    """Registration fails with 422 when password is shorter than 8 chars."""
    response = unauthenticated_client.post(
        "/auth/register",
        json={
            "full_name": "Test Provider",
            "email": "test@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_register_invalid_email(unauthenticated_client: TestClient) -> None:
    """Registration fails with 422 when email format is invalid."""
    response = unauthenticated_client.post(
        "/auth/register",
        json={
            "full_name": "Test Provider",
            "email": "not-an-email",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_register_email_consecutive_dots(unauthenticated_client: TestClient) -> None:
    """
    Registration fails with 422 when the email contains consecutive dots.
    Note: EmailStr's own RFC validation (email-validator) already rejects
    consecutive dots before our custom `email_format_strict` validator runs,
    so this end-to-end test exercises EmailStr's rejection, not our
    "puntos consecutivos" branch specifically — see
    test_email_format_strict_rejects_consecutive_dots below for a direct
    unit test of that branch.
    """
    response = unauthenticated_client.post(
        "/auth/register",
        json={
            "full_name": "Test Provider",
            "email": "test..user@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_register_email_local_part_too_long(unauthenticated_client: TestClient) -> None:
    """Registration fails with 422 when the local part exceeds 64 characters."""
    local_part = "a" * 65
    response = unauthenticated_client.post(
        "/auth/register",
        json={
            "full_name": "Test Provider",
            "email": f"{local_part}@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_email_format_strict_rejects_consecutive_dots() -> None:
    """
    Direct unit test of RegisterRequest.email_format_strict's "consecutive
    dots" branch (backend/app/models/auth.py:33), which had 0% coverage.
    Called directly on the validator classmethod because, in practice,
    Pydantic's EmailStr already rejects consecutive dots before this
    custom validator ever runs (see test_register_email_consecutive_dots),
    so this branch is otherwise unreachable through the public API.
    """
    with pytest.raises(ValueError, match="puntos consecutivos"):
        RegisterRequest.email_format_strict("test..user@example.com")


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ──────────────────────────────────────────────────────────────────────────────


def test_login_success(unauthenticated_client: TestClient, mock_provider: dict) -> None:
    """Happy path: valid credentials return a JWT."""
    with patch("app.routers.auth.get_provider_by_email", return_value=mock_provider):
        response = unauthenticated_client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 604800  # 7 days
    assert data["provider"]["email"] == "test@example.com"
    assert "password_hash" not in data["provider"]


def test_login_case_insensitive_email_matches_registered_account(
    unauthenticated_client: TestClient, mock_provider: dict
) -> None:
    """
    Regression test for the QA-reported bug: a provider registers with an
    uppercase email (RegisterRequest normalizes and stores it lowercase),
    then logs in typing the email exactly as they registered it, uppercase
    included. `get_provider_by_email` does an exact `.eq("email", email)`
    match against a plain `text` column (no `citext`, no `lower()` index),
    so LoginRequest must normalize to lowercase before the lookup or this
    misses and returns a false "Credenciales incorrectas".
    """

    def fake_get_provider_by_email(email: str) -> dict | None:
        # Simulates the real DB: the row was stored with the lowercased
        # email by RegisterRequest, and the query is an exact string match.
        return mock_provider if email == mock_provider["email"] else None

    with patch(
        "app.routers.auth.get_provider_by_email",
        side_effect=fake_get_provider_by_email,
    ):
        response = unauthenticated_client.post(
            "/auth/login",
            json={"email": "Test@Example.COM", "password": "password123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["provider"]["email"] == "test@example.com"


def test_login_wrong_email(unauthenticated_client: TestClient) -> None:
    """Login fails with 401 when email does not exist."""
    with patch("app.routers.auth.get_provider_by_email", return_value=None):
        response = unauthenticated_client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales incorrectas"


def test_login_wrong_password(unauthenticated_client: TestClient, mock_provider: dict) -> None:
    """Login fails with 401 when password is incorrect."""
    with patch("app.routers.auth.get_provider_by_email", return_value=mock_provider):
        response = unauthenticated_client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales incorrectas"


# ──────────────────────────────────────────────────────────────────────────────
# GET /auth/me
# ──────────────────────────────────────────────────────────────────────────────


def test_me_success(client: TestClient) -> None:
    """Authenticated provider can fetch their own profile via /auth/me."""
    response = client.get("/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "completion_rate" in data
    assert "accuracy" in data
    assert "password_hash" not in data


def test_me_no_token(unauthenticated_client: TestClient) -> None:
    """GET /auth/me returns 401 when no token is provided."""
    response = unauthenticated_client.get("/auth/me")
    assert response.status_code == 401


def test_me_invalid_token(unauthenticated_client: TestClient) -> None:
    """GET /auth/me returns 401 when token is invalid."""
    response = unauthenticated_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401
