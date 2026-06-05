"""
Tests for task endpoints.

Coverage:
- GET /tasks/: list (ok, with filters), empty result
- GET /tasks/my/history: ok
- GET /tasks/{task_id}: ok, not found
- GET /tasks/assignments/{id}/progress: ok, forbidden, not found
- POST /tasks/{id}/accept: ok, already active, no slots
- POST /tasks/{id}/start: ok, wrong state
- POST /tasks/{id}/complete: ok, wrong state
- POST /tasks/{id}/fail: ok, wrong state
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import ASSIGNMENT_ID, NOW, PROVIDER_ID, TASK_ID


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/
# ──────────────────────────────────────────────────────────────────────────────


def test_list_tasks_ok(client: TestClient, mock_task: dict) -> None:
    """Happy path: returns list of available tasks."""
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[mock_task]):
        response = client.get("/tasks/")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["tasks"][0]["id"] == TASK_ID


def test_list_tasks_with_filters(client: TestClient, mock_task: dict) -> None:
    """Tasks list with difficulty and hardware filters."""
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[mock_task]) as mock_get:
        response = client.get("/tasks/?difficulty=dificil&hardware=gpu&min_reward=3.0")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_list_tasks_empty(client: TestClient) -> None:
    """Returns empty list when no tasks match filters."""
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[]):
        response = client.get("/tasks/?difficulty=facil")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["tasks"] == []


def test_list_tasks_invalid_min_reward(client: TestClient) -> None:
    """min_reward must be > 0 (validated by FastAPI query param gt=0)."""
    response = client.get("/tasks/?min_reward=-5")
    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/my/history
# ──────────────────────────────────────────────────────────────────────────────


def test_my_history_ok(client: TestClient) -> None:
    """Returns assignment history for the authenticated provider."""
    history_rows = [
        {
            "id": ASSIGNMENT_ID,
            "task_id": TASK_ID,
            "task_title": "Test Task",
            "task_type": "entrenamiento_ml",
            "status": "completada",
            "reward_paid": 5.00,
            "trust_delta": 1.20,
            "accepted_at": NOW,
            "started_at": NOW,
            "completed_at": NOW,
        }
    ]
    with patch("app.routers.tasks.task_queries.get_provider_assignments_history", return_value=history_rows):
        response = client.get("/tasks/my/history")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["assignments"][0]["status"] == "completada"


def test_my_history_empty(client: TestClient) -> None:
    """Returns empty list when provider has no assignments."""
    with patch("app.routers.tasks.task_queries.get_provider_assignments_history", return_value=[]):
        response = client.get("/tasks/my/history")

    assert response.status_code == 200
    assert response.json()["count"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/{task_id}
# ──────────────────────────────────────────────────────────────────────────────


def test_get_task_ok(client: TestClient, mock_task: dict) -> None:
    """Returns full task detail with active_assignment=null."""
    with (
        patch("app.routers.tasks.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.routers.tasks.task_queries.get_active_assignment_for_provider_task", return_value=None),
    ):
        response = client.get(f"/tasks/{TASK_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TASK_ID
    assert data["active_assignment"] is None


def test_get_task_not_found(client: TestClient) -> None:
    """Returns 404 when task does not exist."""
    with patch("app.routers.tasks.task_queries.get_task_by_id", return_value=None):
        response = client.get(f"/tasks/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tarea no encontrada"


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/assignments/{assignment_id}/progress
# ──────────────────────────────────────────────────────────────────────────────


def test_get_progress_ok(client: TestClient) -> None:
    """Returns progress data for an in-progress assignment."""
    row = {
        "assignment_id": ASSIGNMENT_ID,
        "task_id": TASK_ID,
        "task_title": "Test Task",
        "status": "procesando",
        "started_at": NOW,
        "completed_at": None,
        "provider_id": PROVIDER_ID,
        "stages": ["Etapa 1", "Etapa 2", "Etapa 3", "Etapa 4"],
        "duration_max": 90,
    }
    with patch("app.routers.tasks.task_queries.get_assignment_with_task", return_value=row):
        response = client.get(f"/tasks/assignments/{ASSIGNMENT_ID}/progress")

    assert response.status_code == 200
    data = response.json()
    assert data["assignment_id"] == ASSIGNMENT_ID
    assert "progress" in data
    assert "stages" in data
    assert "can_complete" in data


def test_get_progress_forbidden(client: TestClient) -> None:
    """Returns 403 when provider does not own the assignment."""
    other_provider_id = str(uuid.uuid4())
    row = {
        "assignment_id": ASSIGNMENT_ID,
        "task_id": TASK_ID,
        "task_title": "Test Task",
        "status": "procesando",
        "started_at": NOW,
        "completed_at": None,
        "provider_id": other_provider_id,  # Different provider
        "stages": ["Etapa 1", "Etapa 2"],
        "duration_max": 90,
    }
    with patch("app.routers.tasks.task_queries.get_assignment_with_task", return_value=row):
        response = client.get(f"/tasks/assignments/{ASSIGNMENT_ID}/progress")

    assert response.status_code == 403


def test_get_progress_not_found(client: TestClient) -> None:
    """Returns 404 when assignment does not exist."""
    with patch("app.routers.tasks.task_queries.get_assignment_with_task", return_value=None):
        response = client.get(f"/tasks/assignments/{uuid.uuid4()}/progress")

    assert response.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/accept
# ──────────────────────────────────────────────────────────────────────────────


def test_accept_task_ok(client: TestClient, mock_task: dict, mock_assignment: dict) -> None:
    """Happy path: provider accepts a task, assignment is created."""
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=None),
        patch("app.services.task_lifecycle.task_queries.decrement_slots_atomic", return_value=True),
        patch("app.services.task_lifecycle.task_queries.create_assignment", return_value=mock_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/accept")

    assert response.status_code == 201
    data = response.json()
    assert data["task_id"] == TASK_ID
    assert data["status"] == "aceptada"


def test_accept_task_already_active(client: TestClient, mock_task: dict, mock_assignment: dict) -> None:
    """Returns 400 when provider already has an active assignment for this task."""
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=mock_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/accept")

    assert response.status_code == 400
    assert "activa" in response.json()["detail"]


def test_accept_task_no_slots(client: TestClient, mock_task: dict) -> None:
    """Returns 400 when no slots remain."""
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=None),
        patch("app.services.task_lifecycle.task_queries.decrement_slots_atomic", return_value=False),
    ):
        response = client.post(f"/tasks/{TASK_ID}/accept")

    assert response.status_code == 400
    assert "plazas" in response.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/start
# ──────────────────────────────────────────────────────────────────────────────


def test_start_task_ok(client: TestClient, mock_task: dict, mock_assignment: dict) -> None:
    """Happy path: accepted assignment transitions to procesando."""
    updated_assignment = {**mock_assignment, "status": "procesando", "started_at": NOW}
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=mock_assignment),
        patch("app.services.task_lifecycle.task_queries.update_assignment_status", return_value=updated_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/start")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "procesando"
    assert "stages" in data
    assert data["stages_count"] == len(mock_task["stages"])
    assert data["duration_max_seconds"] == 90 * 60


def test_start_task_wrong_state(client: TestClient, mock_task: dict, mock_assignment: dict) -> None:
    """Returns 400 when assignment is not in 'aceptada' state."""
    processing_assignment = {**mock_assignment, "status": "procesando"}
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=processing_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/start")

    assert response.status_code == 400
    assert "aceptado" in response.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/complete
# ──────────────────────────────────────────────────────────────────────────────


def test_complete_task_ok(client: TestClient, mock_task: dict, mock_assignment: dict, mock_provider: dict) -> None:
    """Happy path: processing assignment marked as completed with reward."""
    processing_assignment = {**mock_assignment, "status": "procesando", "started_at": NOW}
    completed_assignment = {**processing_assignment, "status": "completada", "completed_at": NOW}
    updated_provider = {**mock_provider, "tasks_completed": 6}

    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=processing_assignment),
        patch("app.services.task_lifecycle.task_queries.update_assignment_status", return_value=completed_assignment),
        patch("app.services.task_lifecycle.task_queries.count_provider_assignments_by_status", return_value=1),
        patch("app.services.task_lifecycle.wallet_queries.update_wallet_on_task_complete", return_value={}),
        patch("app.services.task_lifecycle.wallet_queries.create_transaction", return_value={"id": "tx-1"}),
        patch("app.services.task_lifecycle.get_provider_by_id", return_value=mock_provider),
        patch("app.services.task_lifecycle.update_provider", return_value=updated_provider),
    ):
        response = client.post(f"/tasks/{TASK_ID}/complete")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completada"
    assert data["reward_paid"] == 5.00
    assert "trust_delta" in data
    assert "new_trust_score" in data


def test_complete_task_wrong_state(client: TestClient, mock_task: dict, mock_assignment: dict) -> None:
    """Returns 400 when assignment is not in 'procesando' state."""
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=mock_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/complete")

    assert response.status_code == 400
    assert "procesamiento" in response.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/fail
# ──────────────────────────────────────────────────────────────────────────────


def test_fail_task_ok(client: TestClient, mock_task: dict, mock_assignment: dict, mock_provider: dict) -> None:
    """Happy path: processing assignment marked as failed, no reward."""
    processing_assignment = {**mock_assignment, "status": "procesando", "started_at": NOW}
    failed_assignment = {**processing_assignment, "status": "fallida", "completed_at": NOW}

    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=processing_assignment),
        patch("app.services.task_lifecycle.task_queries.update_assignment_status", return_value=failed_assignment),
        patch("app.services.task_lifecycle.task_queries.count_provider_assignments_by_status", return_value=1),
        patch("app.services.task_lifecycle.get_provider_by_id", return_value=mock_provider),
        patch("app.services.task_lifecycle.update_provider", return_value=mock_provider),
    ):
        response = client.post(f"/tasks/{TASK_ID}/fail")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fallida"
    assert data["reward_paid"] is None
    assert "trust_delta" in data


def test_fail_task_wrong_state(client: TestClient, mock_task: dict, mock_assignment: dict) -> None:
    """Returns 400 when assignment is not in 'procesando' state."""
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=mock_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/fail")

    assert response.status_code == 400
    assert "procesamiento" in response.json()["detail"]
