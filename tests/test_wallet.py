"""
Tests de cartera — módulo /wallet

Criterios de aceptación validados (US-15, US-16, US-17, US-25):
- GET /wallet/ devuelve los cuatro saldos del proveedor autenticado
- GET /wallet/ sin autenticación devuelve 401
- GET /wallet/transactions devuelve historial paginado
- POST /wallet/withdraw con amount válido y saldo suficiente devuelve 200
- POST /wallet/withdraw con amount < 10 devuelve 400 (monto mínimo)
- POST /wallet/withdraw con amount > saldo disponible devuelve 400
- POST /wallet/withdraw con método inválido devuelve 422
- Todos los endpoints sin token devuelven 401
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

# Las constantes PROVIDER_ID, NOW y WALLET_ID se heredan del conftest.py raíz
# via los fixtures. Los usamos directamente en los datos de prueba inline.


# ──────────────────────────────────────────────────────────────────────────────
# GET /wallet/
# ──────────────────────────────────────────────────────────────────────────────


def test_get_wallet_returns_all_four_balances(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-15 CA-1 / US-25 CA-1: Devuelve los cuatro saldos: available, pending,
    total_earned y total_withdrawn. El provider_id coincide con el proveedor autenticado.
    """
    with patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet):
        response = client.get("/wallet/")

    assert response.status_code == 200
    data = response.json()
    assert data["available_balance"] == 15.00
    assert data["pending_balance"] == 0.00
    assert data["total_earned"] == 25.00
    assert data["total_withdrawn"] == 10.00
    assert "provider_id" in data


def test_get_wallet_returns_updated_at(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    La cartera incluye el campo updated_at para que la UI pueda mostrar cuándo
    se actualizó por última vez.
    """
    with patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet):
        response = client.get("/wallet/")

    assert response.status_code == 200
    assert "updated_at" in response.json()


def test_get_wallet_without_authentication_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-25 CA-6: GET /wallet/ sin token devuelve 401.
    """
    response = unauthenticated_client.get("/wallet/")
    assert response.status_code == 401


def test_get_wallet_all_balances_can_be_zero(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-15 CA-4: Proveedor nuevo con todos los saldos a cero. No debe generar errores.
    """
    zero_wallet = {
        **mock_wallet,
        "available_balance": 0.00,
        "pending_balance": 0.00,
        "total_earned": 0.00,
        "total_withdrawn": 0.00,
    }
    with patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=zero_wallet):
        response = client.get("/wallet/")

    assert response.status_code == 200
    data = response.json()
    assert data["available_balance"] == 0.00
    assert data["total_earned"] == 0.00


# ──────────────────────────────────────────────────────────────────────────────
# GET /wallet/transactions
# ──────────────────────────────────────────────────────────────────────────────


def test_get_transactions_returns_paginated_list(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-16 CA-1 / US-25 CA-2: Historial de transacciones devuelve count, total y lista.
    Incluye los campos obligatorios por transacción.
    """
    now = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)
    transactions = [
        {
            "id": str(uuid.uuid4()),
            "provider_id": mock_wallet["provider_id"],
            "task_id": str(uuid.uuid4()),
            "amount": 5.00,
            "tx_type": "pago_tarea",
            "status": "completada",
            "description": "Recompensa por tarea: Entrenamiento ML",
            "withdraw_method": None,
            "withdraw_destination": None,
            "created_at": now,
        }
    ]
    with patch("app.services.wallet_service.wallet_queries.get_transactions", return_value=(transactions, 1)):
        response = client.get("/wallet/transactions")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["total"] == 1
    tx = data["transactions"][0]
    assert tx["tx_type"] == "pago_tarea"
    assert tx["amount"] == 5.00
    assert tx["status"] == "completada"


def test_get_transactions_empty_history(client: TestClient) -> None:
    """
    US-16 CA-4: Sin transacciones previas devuelve lista vacía sin errores.
    """
    with patch("app.services.wallet_service.wallet_queries.get_transactions", return_value=([], 0)):
        response = client.get("/wallet/transactions")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["total"] == 0
    assert data["transactions"] == []


def test_get_transactions_pagination_parameters_forwarded(
    client: TestClient, mock_provider: dict
) -> None:
    """
    US-16 CA-5: Los parámetros limit y offset se pasan correctamente al servicio.
    """
    with patch("app.services.wallet_service.wallet_queries.get_transactions", return_value=([], 100)) as mock_get:
        response = client.get("/wallet/transactions?limit=10&offset=20")

    assert response.status_code == 200
    mock_get.assert_called_once_with(mock_provider["id"], limit=10, offset=20)


def test_get_transactions_limit_exceeds_maximum_returns_422(client: TestClient) -> None:
    """
    limit > 50 es rechazado con 422 (validado por FastAPI Query le=50).
    """
    response = client.get("/wallet/transactions?limit=100")
    assert response.status_code == 422


def test_get_transactions_includes_withdrawal_transactions(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-16 CA-2: Las transacciones de tipo 'retiro' incluyen withdraw_method
    y withdraw_destination.
    """
    now = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)
    transactions = [
        {
            "id": str(uuid.uuid4()),
            "provider_id": mock_wallet["provider_id"],
            "task_id": None,
            "amount": 10.00,
            "tx_type": "retiro",
            "status": "pendiente",
            "description": "Solicitud de retiro via PayPal",
            "withdraw_method": "paypal",
            "withdraw_destination": "test@paypal.com",
            "created_at": now,
        }
    ]
    with patch("app.services.wallet_service.wallet_queries.get_transactions", return_value=(transactions, 1)):
        response = client.get("/wallet/transactions")

    assert response.status_code == 200
    tx = response.json()["transactions"][0]
    assert tx["tx_type"] == "retiro"
    assert tx["withdraw_method"] == "paypal"
    assert tx["withdraw_destination"] == "test@paypal.com"


def test_get_transactions_without_authentication_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-25 CA-6: GET /wallet/transactions sin token devuelve 401.
    """
    response = unauthenticated_client.get("/wallet/transactions")
    assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# POST /wallet/withdraw
# ──────────────────────────────────────────────────────────────────────────────


def test_withdraw_success_returns_200_with_new_balance(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-17 CA-5 / US-25 CA-3: Retiro válido devuelve 200 con nuevo saldo disponible
    y mensaje de confirmación.
    """
    now = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)
    updated_wallet = {**mock_wallet, "available_balance": 5.00}
    tx = {
        "id": str(uuid.uuid4()),
        "provider_id": mock_wallet["provider_id"],
        "task_id": None,
        "amount": 10.00,
        "tx_type": "retiro",
        "status": "pendiente",
        "description": "Solicitud de retiro via PayPal",
        "withdraw_method": "paypal",
        "withdraw_destination": "test@paypal.com",
        "created_at": now,
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
    assert data["destination"] == "test@paypal.com"
    assert data["status"] == "pendiente"
    assert data["new_available_balance"] == 5.00
    assert "message" in data


def test_withdraw_success_with_transferencia_method(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-17 CA-1: Método 'transferencia' es válido.
    """
    now = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)
    updated_wallet = {**mock_wallet, "available_balance": 5.00}
    tx = {
        "id": str(uuid.uuid4()),
        "provider_id": mock_wallet["provider_id"],
        "task_id": None,
        "amount": 10.00,
        "tx_type": "retiro",
        "status": "pendiente",
        "description": "Solicitud de retiro via transferencia bancaria",
        "withdraw_method": "transferencia",
        "withdraw_destination": "ES12 0000 0000 0000 0000 0000",
        "created_at": now,
    }
    with (
        patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet),
        patch("app.services.wallet_service.wallet_queries.update_wallet_on_withdraw", return_value=updated_wallet),
        patch("app.services.wallet_service.wallet_queries.create_transaction", return_value=tx),
    ):
        response = client.post(
            "/wallet/withdraw",
            json={"amount": 10.00, "method": "transferencia", "destination": "ES12 0000 0000 0000 0000 0000"},
        )

    assert response.status_code == 200


def test_withdraw_success_with_cripto_method(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-17 CA-1: Método 'cripto' es válido.
    """
    now = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)
    updated_wallet = {**mock_wallet, "available_balance": 5.00}
    tx = {
        "id": str(uuid.uuid4()),
        "provider_id": mock_wallet["provider_id"],
        "task_id": None,
        "amount": 10.00,
        "tx_type": "retiro",
        "status": "pendiente",
        "description": "Solicitud de retiro via criptomoneda",
        "withdraw_method": "cripto",
        "withdraw_destination": "0xABCDEF1234567890",
        "created_at": now,
    }
    with (
        patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet),
        patch("app.services.wallet_service.wallet_queries.update_wallet_on_withdraw", return_value=updated_wallet),
        patch("app.services.wallet_service.wallet_queries.create_transaction", return_value=tx),
    ):
        response = client.post(
            "/wallet/withdraw",
            json={"amount": 10.00, "method": "cripto", "destination": "0xABCDEF1234567890"},
        )

    assert response.status_code == 200


def test_withdraw_below_minimum_returns_400(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-17 CA-4 / US-25 CA-5: Monto < 10 CC devuelve 400 con mensaje de mínimo.
    """
    with patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet):
        response = client.post(
            "/wallet/withdraw",
            json={"amount": 5.00, "method": "cripto", "destination": "0xABCDEF"},
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "mínimo" in detail.lower() or "minimo" in detail.lower()


def test_withdraw_exactly_minimum_succeeds(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    Límite: amount = 10.00 (exactamente el mínimo) debe ser aceptado.
    """
    now = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)
    updated_wallet = {**mock_wallet, "available_balance": 5.00}
    tx = {
        "id": str(uuid.uuid4()),
        "provider_id": mock_wallet["provider_id"],
        "task_id": None,
        "amount": 10.00,
        "tx_type": "retiro",
        "status": "pendiente",
        "description": "Retiro",
        "withdraw_method": "paypal",
        "withdraw_destination": "test@paypal.com",
        "created_at": now,
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


def test_withdraw_insufficient_balance_returns_400(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    US-17 CA-3 / US-25 CA-4: Monto > saldo disponible devuelve 400 con mensaje
    que incluye referencia al saldo disponible.
    """
    with patch("app.services.wallet_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet):
        response = client.post(
            "/wallet/withdraw",
            json={"amount": 100.00, "method": "transferencia", "destination": "ES12 0000"},
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "saldo disponible" in detail.lower()


def test_withdraw_invalid_method_returns_422(client: TestClient) -> None:
    """
    US-25 CA-3: Método de retiro inválido devuelve 422 (validación Pydantic Literal).
    """
    response = client.post(
        "/wallet/withdraw",
        json={"amount": 20.00, "method": "bitcoin", "destination": "somewhere"},
    )

    assert response.status_code == 422


def test_withdraw_missing_destination_returns_422(client: TestClient) -> None:
    """
    US-17 CA-7: Campo destination vacío devuelve 422.
    """
    response = client.post(
        "/wallet/withdraw",
        json={"amount": 20.00, "method": "paypal", "destination": ""},
    )

    assert response.status_code == 422


def test_withdraw_without_authentication_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-25 CA-6: POST /wallet/withdraw sin token devuelve 401.
    """
    response = unauthenticated_client.post(
        "/wallet/withdraw",
        json={"amount": 10.00, "method": "paypal", "destination": "test@paypal.com"},
    )

    assert response.status_code == 401
