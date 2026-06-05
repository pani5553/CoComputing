"""
Tests for wallet endpoints.

Coverage:
- GET /wallet/: ok
- GET /wallet/transactions: ok, paginated
- POST /wallet/withdraw: ok, insufficient balance, below minimum
"""
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient

from tests.conftest import NOW, PROVIDER_ID


# ──────────────────────────────────────────────────────────────────────────────
# GET /wallet/
# ──────────────────────────────────────────────────────────────────────────────


def test_get_wallet_ok(client: TestClient, mock_wallet: dict) -> None:
    """Returns the current wallet balances."""
    with patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet):
        response = client.get("/wallet/")

    assert response.status_code == 200
    data = response.json()
    assert data["available_balance"] == 15.00
    assert data["total_earned"] == 25.00
    assert data["provider_id"] == PROVIDER_ID


def test_get_wallet_unauthenticated(unauthenticated_client: TestClient) -> None:
    """Returns 401 when not authenticated."""
    response = unauthenticated_client.get("/wallet/")
    assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# GET /wallet/transactions
# ──────────────────────────────────────────────────────────────────────────────


def test_get_transactions_ok(client: TestClient) -> None:
    """Returns paginated transaction list."""
    transactions = [
        {
            "id": str(uuid.uuid4()),
            "provider_id": PROVIDER_ID,
            "task_id": str(uuid.uuid4()),
            "amount": 5.00,
            "tx_type": "pago_tarea",
            "status": "completada",
            "description": "Recompensa por tarea: Test",
            "withdraw_method": None,
            "withdraw_destination": None,
            "created_at": NOW,
        }
    ]
    with patch("app.services.wallet_service.wallet_queries.get_transactions", return_value=(transactions, 1)):
        response = client.get("/wallet/transactions")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["total"] == 1
    assert data["transactions"][0]["tx_type"] == "pago_tarea"


def test_get_transactions_paginated(client: TestClient) -> None:
    """Pagination parameters are respected."""
    with patch("app.services.wallet_service.wallet_queries.get_transactions", return_value=([], 100)) as mock_get:
        response = client.get("/wallet/transactions?limit=10&offset=20")

    assert response.status_code == 200
    mock_get.assert_called_once_with(PROVIDER_ID, limit=10, offset=20)


def test_get_transactions_limit_too_high(client: TestClient) -> None:
    """limit > 50 is rejected with 422."""
    response = client.get("/wallet/transactions?limit=100")
    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# POST /wallet/withdraw
# ──────────────────────────────────────────────────────────────────────────────


def test_withdraw_ok(client: TestClient, mock_wallet: dict) -> None:
    """Happy path: withdrawal request is created successfully."""
    updated_wallet = {**mock_wallet, "available_balance": 5.00}
    tx = {
        "id": str(uuid.uuid4()),
        "provider_id": PROVIDER_ID,
        "task_id": None,
        "amount": 10.00,
        "tx_type": "retiro",
        "status": "pendiente",
        "description": "Solicitud de retiro via PayPal",
        "withdraw_method": "paypal",
        "withdraw_destination": "test@paypal.com",
        "created_at": NOW,
    }
    with (
        patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet),
        patch("app.services.wallet_service.wallet_queries.update_wallet_on_withdraw", return_value=updated_wallet),
        patch("app.services.wallet_service.wallet_queries.create_transaction", return_value=tx),
    ):
        response = client.post(
            "/wallet/withdraw",
            json={"amount": 10.00, "method": "paypal", "destination": "test@paypal.com"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 10.00
    assert data["method"] == "paypal"
    assert data["status"] == "pendiente"
    assert data["new_available_balance"] == 5.00
    assert "message" in data


def test_withdraw_insufficient_balance(client: TestClient, mock_wallet: dict) -> None:
    """Returns 400 when withdrawal amount exceeds available balance."""
    with patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet):
        response = client.post(
            "/wallet/withdraw",
            json={"amount": 100.00, "method": "transferencia", "destination": "ES12 0000 0000 0000"},
        )

    assert response.status_code == 400
    assert "saldo disponible" in response.json()["detail"]


def test_withdraw_below_minimum(client: TestClient, mock_wallet: dict) -> None:
    """Returns 400 when withdrawal amount is below the minimum (10.00 CC)."""
    with patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet):
        response = client.post(
            "/wallet/withdraw",
            json={"amount": 5.00, "method": "cripto", "destination": "0xABCDEF"},
        )

    assert response.status_code == 400
    assert "mínimo" in response.json()["detail"]


def test_withdraw_invalid_method(client: TestClient) -> None:
    """Returns 422 when withdrawal method is invalid."""
    response = client.post(
        "/wallet/withdraw",
        json={"amount": 20.00, "method": "bitcoin", "destination": "somewhere"},
    )
    assert response.status_code == 422
