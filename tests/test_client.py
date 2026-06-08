"""
Tests de lado cliente — módulo /client

Criterios de aceptación validados:
- POST /client/deposit recarga el saldo y crea transacción de tipo 'deposito'
- POST /client/deposit con importe inválido devuelve 400
- POST /client/tasks crea tarea, retiene escrow y devuelve 201 con los datos
- POST /client/tasks con saldo insuficiente devuelve 400
- POST /client/tasks con payload inválido devuelve 422
- GET /client/tasks devuelve las tareas del cliente autenticado
- GET /client/tasks/{id} devuelve detalle + asignaciones de la tarea
- GET /client/tasks/{id} de otra persona devuelve 404
- POST /client/tasks/{id}/cancel cancela la tarea y reembolsa el escrow
- POST /client/tasks/{id}/cancel en tarea ya completada devuelve 400
- Todos los endpoints sin token devuelven 401

Estrategia: mock de las queries de DB y wallet_service.
La lógica de negocio (validaciones, flujo de servicio) se prueba contra el servicio real.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Los fixtures usan PROVIDER_ID del conftest raíz; CLIENT_ID lo reutilizamos aquí
# (mismo valor que conftest.PROVIDER_ID para que el mock de autenticación funcione)
from conftest import PROVIDER_ID, WALLET_ID, NOW  # noqa: E402  (injected by conftest into sys.path)

CLIENT_ID = PROVIDER_ID  # El mismo usuario actúa como cliente
TASK_ID = str(uuid.uuid4())
ESCROW_ID = str(uuid.uuid4())


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_wallet_rich(mock_wallet: dict) -> dict:
    """Cartera con saldo suficiente para escrow."""
    return {**mock_wallet, "available_balance": 500.00, "pending_balance": 0.00}


@pytest.fixture
def mock_client_task() -> dict:
    """Tarea publicada por el cliente."""
    return {
        "id": TASK_ID,
        "client_id": CLIENT_ID,
        "title": "Test ML Training",
        "task_type": "entrenamiento_ml",
        "description": "Entrena un modelo de prueba.",
        "reward": 5.00,
        "duration_min": 30,
        "duration_max": 90,
        "difficulty": "medio",
        "hardware_required": "gpu",
        "total_slots": 3,
        "slots_left": 3,
        "stages": ["Prep", "Train", "Validate"],
        "requester_name": "Test Corp",
        "status": "disponible",
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture
def mock_escrow() -> dict:
    return {
        "id": ESCROW_ID,
        "task_id": TASK_ID,
        "client_id": CLIENT_ID,
        "amount_per_slot": 5.00,
        "total_slots": 3,
        "amount_held": 15.00,
        "amount_released": 0.00,
        "status": "activo",
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture
def mock_deposit_tx() -> dict:
    return {
        "id": str(uuid.uuid4()),
        "provider_id": CLIENT_ID,
        "task_id": None,
        "amount": 100.00,
        "tx_type": "deposito",
        "status": "completada",
        "description": "Depósito simulado de 100.00 CC",
        "withdraw_method": None,
        "withdraw_destination": None,
        "created_at": NOW,
    }


@pytest.fixture
def mock_escrow_tx() -> dict:
    return {
        "id": str(uuid.uuid4()),
        "provider_id": CLIENT_ID,
        "task_id": TASK_ID,
        "amount": 15.00,
        "tx_type": "escrow",
        "status": "completada",
        "description": "Escrow retenido para tarea: Test ML Training (3 plazas × 5.00 CC)",
        "withdraw_method": None,
        "withdraw_destination": None,
        "created_at": NOW,
    }


@pytest.fixture
def mock_refund_tx() -> dict:
    return {
        "id": str(uuid.uuid4()),
        "provider_id": CLIENT_ID,
        "task_id": TASK_ID,
        "amount": 15.00,
        "tx_type": "reembolso",
        "status": "completada",
        "description": "Reembolso de escrow por cancelación de tarea: Test ML Training",
        "withdraw_method": None,
        "withdraw_destination": None,
        "created_at": NOW,
    }


# ─── POST /client/deposit ─────────────────────────────────────────────────────

def test_deposit_success_returns_200_with_new_balance(
    client: TestClient, mock_wallet_rich: dict, mock_deposit_tx: dict
) -> None:
    """
    CA-1: Depósito válido devuelve 200, nuevo saldo y transaction_id.
    """
    updated_wallet = {**mock_wallet_rich, "available_balance": 600.00, "total_earned": 625.00}
    with (
        patch("app.services.client_service.client_queries.deposit_to_wallet", return_value=updated_wallet),
        patch("app.services.client_service.wallet_queries.create_transaction", return_value=mock_deposit_tx),
    ):
        response = client.post("/client/deposit", json={"amount": 100.00})

    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 100.00
    assert data["new_available_balance"] == 600.00
    assert "transaction_id" in data
    assert "message" in data


def test_deposit_zero_amount_returns_422(client: TestClient) -> None:
    """
    CA-2: amount = 0 es rechazado por validación Pydantic (gt=0) → 422.
    """
    response = client.post("/client/deposit", json={"amount": 0})
    assert response.status_code == 422


def test_deposit_negative_amount_returns_422(client: TestClient) -> None:
    """
    CA-2: amount negativo es rechazado → 422.
    """
    response = client.post("/client/deposit", json={"amount": -50})
    assert response.status_code == 422


def test_deposit_without_auth_returns_401(unauthenticated_client: TestClient) -> None:
    """
    CA-6: Sin token → 401.
    """
    response = unauthenticated_client.post("/client/deposit", json={"amount": 50.00})
    assert response.status_code == 401


# ─── POST /client/tasks ───────────────────────────────────────────────────────

VALID_TASK_PAYLOAD = {
    "title": "Test ML Training",
    "task_type": "entrenamiento_ml",
    "description": "Entrena un modelo de prueba con los datos proporcionados.",
    "reward": 5.00,
    "difficulty": "medio",
    "hardware_required": "gpu",
    "total_slots": 3,
    "duration_min": 30,
    "duration_max": 90,
    "stages": ["Preparando", "Entrenando", "Validando"],
    "requester_name": "Test Corp",
}


def test_create_task_success_returns_201(
    client: TestClient,
    mock_wallet_rich: dict,
    mock_client_task: dict,
    mock_escrow: dict,
    mock_escrow_tx: dict,
) -> None:
    """
    CA-3: Publicar tarea con saldo suficiente → 201 con task_id, escrow_total y nuevo saldo.
    """
    updated_wallet = {**mock_wallet_rich, "available_balance": 485.00, "pending_balance": 15.00}
    with (
        patch("app.services.client_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet_rich),
        patch("app.services.client_service.client_queries.create_client_task", return_value=mock_client_task),
        patch("app.services.client_service.client_queries.hold_escrow", return_value=mock_escrow),
        patch("app.services.client_service.wallet_queries.create_transaction", return_value=mock_escrow_tx),
        patch("app.services.client_service.wallet_queries.get_wallet_by_provider_id", return_value=updated_wallet),
    ):
        response = client.post("/client/tasks", json=VALID_TASK_PAYLOAD)

    assert response.status_code == 201
    data = response.json()
    assert "task_id" in data
    assert data["escrow_total"] == 15.00  # 5.00 × 3 plazas
    assert data["reward"] == 5.00
    assert data["total_slots"] == 3
    assert "new_available_balance" in data
    assert "message" in data


def test_create_task_insufficient_balance_returns_400(
    client: TestClient, mock_wallet: dict
) -> None:
    """
    CA-4: Saldo disponible (15 CC) < escrow necesario (50 CC) → 400.
    """
    # mock_wallet tiene available_balance = 15.00
    with patch("app.services.client_service.wallet_queries.get_wallet_by_provider_id", return_value=mock_wallet):
        response = client.post("/client/tasks", json={**VALID_TASK_PAYLOAD, "reward": 10.00, "total_slots": 5})

    assert response.status_code == 400
    assert "saldo" in response.json()["detail"].lower()


def test_create_task_invalid_task_type_returns_422(client: TestClient) -> None:
    """
    CA-5: task_type inválido → 422.
    """
    response = client.post("/client/tasks", json={**VALID_TASK_PAYLOAD, "task_type": "mineria_cripto"})
    assert response.status_code == 422


def test_create_task_duration_max_less_than_min_returns_422(client: TestClient) -> None:
    """
    CA-5: duration_max < duration_min → 422 (validador de campo).
    """
    response = client.post("/client/tasks", json={**VALID_TASK_PAYLOAD, "duration_min": 60, "duration_max": 30})
    assert response.status_code == 422


def test_create_task_empty_stages_returns_422(client: TestClient) -> None:
    """
    CA-5: stages vacío → 422 (min_length=1).
    """
    response = client.post("/client/tasks", json={**VALID_TASK_PAYLOAD, "stages": []})
    assert response.status_code == 422


def test_create_task_without_auth_returns_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post("/client/tasks", json=VALID_TASK_PAYLOAD)
    assert response.status_code == 401


# ─── GET /client/tasks ────────────────────────────────────────────────────────

def test_list_my_tasks_returns_client_tasks(
    client: TestClient, mock_client_task: dict
) -> None:
    """
    CA-7: GET /client/tasks devuelve lista con count y tasks del cliente.
    """
    task_summary = {
        **mock_client_task,
        "escrow_held": 15.00,
        "escrow_released": 0.00,
        "slots_completed": 0,
    }
    with patch("app.services.client_service.client_queries.get_client_tasks", return_value=[task_summary]):
        response = client.get("/client/tasks")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["tasks"]) == 1
    task = data["tasks"][0]
    assert task["title"] == "Test ML Training"
    assert task["escrow_held"] == 15.00
    assert task["slots_completed"] == 0


def test_list_my_tasks_empty(client: TestClient) -> None:
    """
    CA-7: Sin tareas publicadas devuelve lista vacía.
    """
    with patch("app.services.client_service.client_queries.get_client_tasks", return_value=[]):
        response = client.get("/client/tasks")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["tasks"] == []


def test_list_my_tasks_without_auth_returns_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get("/client/tasks")
    assert response.status_code == 401


# ─── GET /client/tasks/{id} ───────────────────────────────────────────────────

def test_get_task_detail_returns_assignments(
    client: TestClient, mock_client_task: dict
) -> None:
    """
    CA-8: GET /client/tasks/{id} devuelve el detalle de la tarea con sus asignaciones.
    """
    detail = {
        **mock_client_task,
        "escrow_held": 15.00,
        "escrow_released": 5.00,
        "assignments": [
            {
                "id": str(uuid.uuid4()),
                "provider_id": str(uuid.uuid4()),
                "provider_name": "Provider A",
                "status": "completada",
                "reward_paid": 5.00,
                "accepted_at": NOW,
                "completed_at": NOW,
            }
        ],
    }
    with patch("app.services.client_service.client_queries.get_client_task_detail", return_value=detail):
        response = client.get(f"/client/tasks/{TASK_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TASK_ID
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["provider_name"] == "Provider A"
    assert data["escrow_released"] == 5.00


def test_get_task_detail_not_found_returns_404(client: TestClient) -> None:
    """
    CA-8: Tarea inexistente o de otro cliente → 404.
    """
    with patch("app.services.client_service.client_queries.get_client_task_detail", return_value=None):
        response = client.get(f"/client/tasks/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_task_detail_without_auth_returns_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.get(f"/client/tasks/{TASK_ID}")
    assert response.status_code == 401


# ─── POST /client/tasks/{id}/cancel ──────────────────────────────────────────

def test_cancel_task_success_returns_refund(
    client: TestClient, mock_client_task: dict, mock_wallet_rich: dict, mock_refund_tx: dict
) -> None:
    """
    CA-9: Cancelar tarea disponible → 200 con refund_amount y nuevo saldo.
    El escrow no liberado (15 CC) se reembolsa al cliente.
    """
    refund_wallet = {**mock_wallet_rich, "available_balance": 515.00, "pending_balance": 0.00}
    with (
        patch("app.services.client_service.client_queries.cancel_task_db", return_value=mock_client_task),
        patch("app.services.client_service.client_queries.refund_escrow", return_value=15.00),
        patch("app.services.client_service.wallet_queries.create_transaction", return_value=mock_refund_tx),
        patch("app.services.client_service.wallet_queries.get_wallet_by_provider_id", return_value=refund_wallet),
    ):
        response = client.post(f"/client/tasks/{TASK_ID}/cancel")

    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == TASK_ID
    assert data["refund_amount"] == 15.00
    assert data["new_available_balance"] == 515.00
    assert "reembolsado" in data["message"].lower() or "reembolso" in data["message"].lower()


def test_cancel_task_not_found_or_unauthorized_returns_400(
    client: TestClient
) -> None:
    """
    CA-10: Tarea no encontrada o ya completada/cancelada → 400.
    """
    with patch("app.services.client_service.client_queries.cancel_task_db", return_value=None):
        response = client.post(f"/client/tasks/{uuid.uuid4()}/cancel")

    assert response.status_code == 400


def test_cancel_task_seed_task_no_escrow_returns_zero_refund(
    client: TestClient, mock_client_task: dict, mock_wallet_rich: dict
) -> None:
    """
    Tarea sin escrow (del seed) → cancela correctamente con refund_amount = 0.
    """
    refund_wallet = {**mock_wallet_rich, "available_balance": 500.00}
    with (
        patch("app.services.client_service.client_queries.cancel_task_db", return_value=mock_client_task),
        patch("app.services.client_service.client_queries.refund_escrow", side_effect=ValueError("escrow_not_active")),
        patch("app.services.client_service.wallet_queries.get_wallet_by_provider_id", return_value=refund_wallet),
    ):
        response = client.post(f"/client/tasks/{TASK_ID}/cancel")

    assert response.status_code == 200
    data = response.json()
    assert data["refund_amount"] == 0.0


def test_cancel_task_without_auth_returns_401(unauthenticated_client: TestClient) -> None:
    response = unauthenticated_client.post(f"/client/tasks/{TASK_ID}/cancel")
    assert response.status_code == 401


# ─── Happy path integration (mocked DB) ──────────────────────────────────────

def test_happy_path_deposit_create_cancel(
    client: TestClient, mock_wallet: dict, mock_client_task: dict,
    mock_deposit_tx: dict, mock_escrow: dict, mock_escrow_tx: dict, mock_refund_tx: dict
) -> None:
    """
    Flujo completo (mocked): depositar → publicar tarea → cancelar y reembolsar.
    Verifica la cadena de estados sin necesidad de DB real.
    """
    # Step 1: Deposit 100 CC
    wallet_after_deposit = {**mock_wallet, "available_balance": 115.00, "total_earned": 125.00}
    with (
        patch("app.services.client_service.client_queries.deposit_to_wallet", return_value=wallet_after_deposit),
        patch("app.services.client_service.wallet_queries.create_transaction", return_value=mock_deposit_tx),
    ):
        r1 = client.post("/client/deposit", json={"amount": 100.00})
    assert r1.status_code == 200
    assert r1.json()["new_available_balance"] == 115.00

    # Step 2: Publish task (escrow = 5 × 3 = 15 CC)
    wallet_after_escrow = {**mock_wallet, "available_balance": 100.00, "pending_balance": 15.00}
    with (
        patch("app.services.client_service.wallet_queries.get_wallet_by_provider_id",
              side_effect=[wallet_after_deposit, wallet_after_escrow]),
        patch("app.services.client_service.client_queries.create_client_task", return_value=mock_client_task),
        patch("app.services.client_service.client_queries.hold_escrow", return_value=mock_escrow),
        patch("app.services.client_service.wallet_queries.create_transaction", return_value=mock_escrow_tx),
    ):
        r2 = client.post("/client/tasks", json=VALID_TASK_PAYLOAD)
    assert r2.status_code == 201
    assert r2.json()["escrow_total"] == 15.00

    # Step 3: Cancel task, get full refund
    wallet_after_refund = {**mock_wallet, "available_balance": 115.00, "pending_balance": 0.00}
    with (
        patch("app.services.client_service.client_queries.cancel_task_db", return_value=mock_client_task),
        patch("app.services.client_service.client_queries.refund_escrow", return_value=15.00),
        patch("app.services.client_service.wallet_queries.create_transaction", return_value=mock_refund_tx),
        patch("app.services.client_service.wallet_queries.get_wallet_by_provider_id", return_value=wallet_after_refund),
    ):
        r3 = client.post(f"/client/tasks/{TASK_ID}/cancel")
    assert r3.status_code == 200
    assert r3.json()["refund_amount"] == 15.00
    assert r3.json()["new_available_balance"] == 115.00
