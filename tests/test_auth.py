"""
Tests de autenticación — módulo /auth

Criterios de aceptación validados (US-01, US-02, US-23):
- Registro exitoso devuelve 201 con datos del proveedor (sin password_hash)
- Registro con email duplicado devuelve 409
- Registro con password < 8 caracteres devuelve 422
- Registro con email inválido devuelve 422
- Login exitoso devuelve 200 con JWT válido
- Login con credenciales incorrectas devuelve 401 (mismo mensaje para ambos casos)
- GET /auth/me con token válido devuelve datos completos del proveedor
- GET /auth/me sin token devuelve 401
- GET /auth/me con token inválido devuelve 401
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# No se importa de tests.conftest para evitar conflicto con backend/tests/conftest.py


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/register
# ──────────────────────────────────────────────────────────────────────────────


def test_register_success_returns_201_with_provider_data(
    unauthenticated_client: TestClient, mock_provider: dict
) -> None:
    """
    US-01 CA-1: Registro exitoso devuelve 201 con datos del proveedor.
    El cuerpo de respuesta contiene email, full_name, rank, trust_score
    y NO contiene el campo password_hash.
    """
    with (
        patch("app.routers.auth.get_provider_by_email", return_value=None),
        patch("app.routers.auth.create_provider", return_value=mock_provider),
        patch("app.routers.auth.create_wallet_for_provider", return_value={"id": "wallet-1"}),
        patch("app.routers.auth.hash_password", return_value="$2b$12$hashed"),
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
    assert data["trust_score"] == 55.00
    assert data["rank"] == "confiable"
    assert "password_hash" not in data


def test_register_success_initializes_wallet(
    unauthenticated_client: TestClient, mock_provider: dict
) -> None:
    """
    US-01 CA-1: Al registrarse, se crea la cartera vinculada.
    Verificamos que create_wallet_for_provider se invoca con el ID del proveedor.
    """
    with (
        patch("app.routers.auth.get_provider_by_email", return_value=None),
        patch("app.routers.auth.create_provider", return_value=mock_provider),
        patch("app.routers.auth.hash_password", return_value="$2b$12$hashed"),
        patch("app.routers.auth.create_wallet_for_provider", return_value={"id": "wallet-1"}) as mock_wallet,
    ):
        unauthenticated_client.post(
            "/auth/register",
            json={
                "full_name": "Test Provider",
                "email": "test@example.com",
                "password": "password123",
            },
        )

    mock_wallet.assert_called_once_with(mock_provider["id"])


def test_register_duplicate_email_returns_409(
    unauthenticated_client: TestClient, mock_provider: dict
) -> None:
    """
    US-01 CA-2: Email duplicado devuelve 409 con mensaje específico.
    """
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


def test_register_short_password_returns_422(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-01 CA-3 / US-23 CA-3: Password < 8 caracteres devuelve 422 (validación Pydantic).
    """
    response = unauthenticated_client.post(
        "/auth/register",
        json={
            "full_name": "Test Provider",
            "email": "test@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_register_password_exactly_7_chars_returns_422(
    unauthenticated_client: TestClient,
) -> None:
    """
    Límite: exactamente 7 caracteres de password devuelve 422.
    """
    response = unauthenticated_client.post(
        "/auth/register",
        json={
            "full_name": "Test Provider",
            "email": "test@example.com",
            "password": "1234567",
        },
    )

    assert response.status_code == 422


def test_register_invalid_email_returns_422(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-01 CA-4: Email con formato inválido devuelve 422.
    """
    response = unauthenticated_client.post(
        "/auth/register",
        json={
            "full_name": "Test Provider",
            "email": "not-an-email",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_register_empty_name_returns_422(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-01 CA-5: Nombre vacío devuelve 422.
    """
    response = unauthenticated_client.post(
        "/auth/register",
        json={
            "full_name": "",
            "email": "test@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 422


def test_register_missing_fields_returns_422(
    unauthenticated_client: TestClient,
) -> None:
    """
    Campos obligatorios ausentes devuelven 422.
    """
    response = unauthenticated_client.post(
        "/auth/register",
        json={"email": "test@example.com"},
    )

    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ──────────────────────────────────────────────────────────────────────────────


def test_login_success_returns_200_with_jwt(
    unauthenticated_client: TestClient, mock_provider: dict
) -> None:
    """
    US-02 CA-1 / US-23 CA-4: Login exitoso devuelve 200 con access_token y datos del proveedor.
    El token_type es 'bearer' y expires_in corresponde a 7 días (604800 segundos).
    """
    with (
        patch("app.routers.auth.get_provider_by_email", return_value=mock_provider),
        patch("app.routers.auth.verify_password", return_value=True),
    ):
        response = unauthenticated_client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 604800
    assert data["provider"]["email"] == "test@example.com"
    assert "password_hash" not in data["provider"]


def test_login_success_jwt_is_non_empty_string(
    unauthenticated_client: TestClient, mock_provider: dict
) -> None:
    """
    El JWT devuelto no es vacío y tiene formato de tres segmentos separados por puntos.
    """
    with (
        patch("app.routers.auth.get_provider_by_email", return_value=mock_provider),
        patch("app.routers.auth.verify_password", return_value=True),
    ):
        response = unauthenticated_client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

    token = response.json()["access_token"]
    parts = token.split(".")
    assert len(parts) == 3, "JWT debe tener exactamente 3 segmentos"


def test_login_wrong_email_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-02 CA-3 / US-23 CA-5: Email no registrado devuelve 401 con mensaje genérico.
    El mensaje no revela si el email existe.
    """
    with patch("app.routers.auth.get_provider_by_email", return_value=None):
        response = unauthenticated_client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales incorrectas"


def test_login_wrong_password_returns_401(
    unauthenticated_client: TestClient, mock_provider: dict
) -> None:
    """
    US-02 CA-2 / US-23 CA-5: Password incorrecto devuelve 401 con mensaje genérico idéntico.
    """
    with (
        patch("app.routers.auth.get_provider_by_email", return_value=mock_provider),
        patch("app.routers.auth.verify_password", return_value=False),
    ):
        response = unauthenticated_client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales incorrectas"


def test_login_wrong_email_and_wrong_password_same_message(
    unauthenticated_client: TestClient, mock_provider: dict
) -> None:
    """
    US-02 CA-2 y CA-3: El mensaje de error es idéntico para email inexistente
    y password incorrecto (prevención de enumeración de usuarios).
    """
    with patch("app.routers.auth.get_provider_by_email", return_value=None):
        resp_no_email = unauthenticated_client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )

    with (
        patch("app.routers.auth.get_provider_by_email", return_value=mock_provider),
        patch("app.routers.auth.verify_password", return_value=False),
    ):
        resp_wrong_pw = unauthenticated_client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )

    assert resp_no_email.json()["detail"] == resp_wrong_pw.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# GET /auth/me
# ──────────────────────────────────────────────────────────────────────────────


def test_me_with_valid_token_returns_provider_data(
    client: TestClient,
) -> None:
    """
    US-23 CA-6: GET /auth/me con token válido devuelve 200 con datos completos.
    Incluye campos extendidos: completion_rate, accuracy, response_time_score, client_rating.
    """
    response = client.get("/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test Provider"
    assert "completion_rate" in data
    assert "accuracy" in data
    assert "response_time_score" in data
    assert "client_rating" in data
    assert "password_hash" not in data


def test_me_without_token_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-23 CA-7: GET /auth/me sin token devuelve 401.
    """
    response = unauthenticated_client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_invalid_token_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-23 CA-7: GET /auth/me con token malformado devuelve 401.
    """
    response = unauthenticated_client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )

    assert response.status_code == 401


def test_me_with_wrong_bearer_scheme_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-30 CA-4: Autenticación sin esquema Bearer devuelve 401.
    """
    response = unauthenticated_client.get(
        "/auth/me",
        headers={"Authorization": "Basic dGVzdDp0ZXN0"},
    )

    # FastAPI HTTPBearer con auto_error=False devuelve 401 vía la dependencia
    assert response.status_code == 401
