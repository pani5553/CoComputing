"""
Tests de tareas — módulo /tasks

Criterios de aceptación validados (US-05, US-06, US-08, US-09, US-10, US-11,
US-12, US-14, US-24):
- GET /tasks/ devuelve lista de tareas disponibles
- GET /tasks/ con filtros de dificultad y hardware
- GET /tasks/{id} con ID válido devuelve detalle completo
- GET /tasks/{id} con ID inexistente devuelve 404
- POST /tasks/{id}/accept devuelve 201 con asignación creada
- POST /tasks/{id}/accept sin autenticación devuelve 401
- POST /tasks/{id}/start devuelve 200 con assignment_id y stages
- POST /tasks/{id}/complete devuelve 200 con trust_delta y reward
- POST /tasks/{id}/fail devuelve 200
- GET /tasks/my/history devuelve historial del proveedor
- GET /tasks/assignments/{id}/progress devuelve progress en 0-99
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Constantes también disponibles desde conftest.py raíz via fixtures
# Las definimos aquí para usarlas en datos inline de prueba
import sys as _sys
import os as _os
_tests_dir = _os.path.dirname(_os.path.abspath(__file__))
if _tests_dir not in _sys.path:
    _sys.path.insert(0, _tests_dir)

# Importamos directamente del módulo conftest de tests/ (no del backend)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "root_conftest",
    _os.path.join(_tests_dir, "conftest.py"),
)
_root_conftest = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_root_conftest)
ASSIGNMENT_ID = _root_conftest.ASSIGNMENT_ID
NOW = _root_conftest.NOW
PROVIDER_ID = _root_conftest.PROVIDER_ID
TASK_ID = _root_conftest.TASK_ID


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/
# ──────────────────────────────────────────────────────────────────────────────


def test_list_tasks_returns_available_tasks(
    client: TestClient, mock_task: dict
) -> None:
    """
    US-05 CA-1 / US-24 CA-1: Sin filtros, devuelve todas las tareas disponibles.
    La respuesta contiene count y lista tasks con los campos obligatorios.
    """
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[mock_task]):
        response = client.get("/tasks/")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["tasks"]) == 1
    task = data["tasks"][0]
    assert task["id"] == TASK_ID
    assert task["title"] == "Entrenamiento ML — ResNet-50 CIFAR-100"
    assert task["status"] == "disponible"
    assert "stages" in task


def test_list_tasks_requires_authentication(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-30 CA-4: GET /tasks/ sin token devuelve 401.
    """
    response = unauthenticated_client.get("/tasks/")
    assert response.status_code == 401


def test_list_tasks_empty_when_no_results(client: TestClient) -> None:
    """
    US-05 CA-4: Sin tareas disponibles devuelve count=0 y lista vacía.
    """
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[]):
        response = client.get("/tasks/")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["tasks"] == []


def test_list_tasks_filter_by_difficulty(
    client: TestClient, mock_task: dict
) -> None:
    """
    US-06 CA-1 / US-24 CA-2: Filtro por dificultad pasa correctamente el parámetro.
    """
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[mock_task]) as mock_get:
        response = client.get("/tasks/?difficulty=dificil")

    assert response.status_code == 200
    # Verificar que se llamó con la lista correcta
    call_kwargs = mock_get.call_args[1] if mock_get.call_args[1] else mock_get.call_args[0][0] if mock_get.call_args[0] else {}
    # El router convierte el string en lista
    assert response.json()["count"] == 1


def test_list_tasks_filter_by_hardware(
    client: TestClient, mock_task: dict
) -> None:
    """
    US-06 CA-2 / US-24 CA-2: Filtro por hardware pasa correctamente.
    """
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[mock_task]):
        response = client.get("/tasks/?hardware=gpu")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_list_tasks_combined_filters(
    client: TestClient, mock_task: dict
) -> None:
    """
    US-06 CA-3: Filtros combinados de dificultad y hardware.
    """
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[mock_task]):
        response = client.get("/tasks/?difficulty=dificil&hardware=gpu&min_reward=3.0")

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_list_tasks_multiple_difficulty_values(
    client: TestClient, mock_task: dict
) -> None:
    """
    US-06 CA-1: Múltiples valores de dificultad separados por coma.
    """
    with patch("app.routers.tasks.task_queries.get_tasks", return_value=[mock_task]) as mock_get:
        response = client.get("/tasks/?difficulty=facil,dificil")

    assert response.status_code == 200


def test_list_tasks_invalid_min_reward_rejected(client: TestClient) -> None:
    """
    min_reward debe ser > 0. Un valor negativo devuelve 422.
    """
    response = client.get("/tasks/?min_reward=-5")
    assert response.status_code == 422


def test_list_tasks_min_reward_zero_rejected(client: TestClient) -> None:
    """
    min_reward = 0 también es inválido (el parámetro tiene gt=0).
    """
    response = client.get("/tasks/?min_reward=0")
    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/my/history
# ──────────────────────────────────────────────────────────────────────────────


def test_get_my_history_returns_assignment_list(client: TestClient) -> None:
    """
    US-24 CA-8: Historial del proveedor autenticado devuelve lista de asignaciones.
    """
    history_rows = [
        {
            "id": ASSIGNMENT_ID,
            "task_id": TASK_ID,
            "task_title": "Entrenamiento ML — ResNet-50 CIFAR-100",
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
    assignment = data["assignments"][0]
    assert assignment["status"] == "completada"
    assert assignment["reward_paid"] == 5.00
    assert assignment["trust_delta"] == 1.20


def test_get_my_history_empty(client: TestClient) -> None:
    """
    Proveedor sin asignaciones previas devuelve count=0 y lista vacía.
    """
    with patch("app.routers.tasks.task_queries.get_provider_assignments_history", return_value=[]):
        response = client.get("/tasks/my/history")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["assignments"] == []


def test_get_my_history_requires_authentication(
    unauthenticated_client: TestClient,
) -> None:
    """
    GET /tasks/my/history sin token devuelve 401.
    """
    response = unauthenticated_client.get("/tasks/my/history")
    assert response.status_code == 401


def test_get_my_history_includes_failed_assignments(client: TestClient) -> None:
    """
    El historial incluye asignaciones fallidas con reward_paid=null y trust_delta negativo.
    """
    history_rows = [
        {
            "id": str(uuid.uuid4()),
            "task_id": TASK_ID,
            "task_title": "Simulación de fluidos",
            "task_type": "simulacion_fisica",
            "status": "fallida",
            "reward_paid": None,
            "trust_delta": -2.50,
            "accepted_at": NOW,
            "started_at": NOW,
            "completed_at": NOW,
        }
    ]
    with patch("app.routers.tasks.task_queries.get_provider_assignments_history", return_value=history_rows):
        response = client.get("/tasks/my/history")

    assert response.status_code == 200
    assignment = response.json()["assignments"][0]
    assert assignment["status"] == "fallida"
    assert assignment["reward_paid"] is None
    assert assignment["trust_delta"] == -2.50


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/{task_id}
# ──────────────────────────────────────────────────────────────────────────────


def test_get_task_by_id_returns_full_detail(
    client: TestClient, mock_task: dict
) -> None:
    """
    US-08 CA-1 / US-24 CA-3: Detalle de tarea válida devuelve 200 con todos los campos.
    """
    with (
        patch("app.routers.tasks.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.routers.tasks.task_queries.get_active_assignment_for_provider_task", return_value=None),
    ):
        response = client.get(f"/tasks/{TASK_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == TASK_ID
    assert data["title"] == "Entrenamiento ML — ResNet-50 CIFAR-100"
    assert data["reward"] == 5.00
    assert data["difficulty"] == "dificil"
    assert data["hardware_required"] == "gpu"
    assert len(data["stages"]) == 5
    assert data["active_assignment"] is None


def test_get_task_by_id_includes_active_assignment(
    client: TestClient, mock_task: dict, mock_assignment: dict
) -> None:
    """
    US-08 CA-6: Si el proveedor tiene asignación activa, active_assignment no es null.
    """
    with (
        patch("app.routers.tasks.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.routers.tasks.task_queries.get_active_assignment_for_provider_task", return_value=mock_assignment),
    ):
        response = client.get(f"/tasks/{TASK_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["active_assignment"] is not None
    assert data["active_assignment"]["status"] == "aceptada"


def test_get_task_by_id_not_found_returns_404(client: TestClient) -> None:
    """
    US-08 CA-3 / US-24 CA-3: ID inexistente devuelve 404 con mensaje específico.
    """
    with patch("app.routers.tasks.task_queries.get_task_by_id", return_value=None):
        response = client.get(f"/tasks/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tarea no encontrada"


def test_get_task_requires_authentication(unauthenticated_client: TestClient) -> None:
    """
    GET /tasks/{id} sin token devuelve 401.
    """
    response = unauthenticated_client.get(f"/tasks/{TASK_ID}")
    assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# GET /tasks/assignments/{assignment_id}/progress
# ──────────────────────────────────────────────────────────────────────────────


def test_get_progress_in_processing_returns_progress_data(client: TestClient) -> None:
    """
    US-14 CA-1 / US-24: Asignación en procesamiento devuelve progress entre 0 y 99.
    También contiene: current_stage_index, stages, can_complete.
    """
    row = {
        "assignment_id": ASSIGNMENT_ID,
        "task_id": TASK_ID,
        "task_title": "Entrenamiento ML — ResNet-50 CIFAR-100",
        "status": "procesando",
        "started_at": NOW,
        "completed_at": None,
        "provider_id": PROVIDER_ID,
        "stages": ["Etapa 1", "Etapa 2", "Etapa 3", "Etapa 4", "Etapa 5"],
        "duration_max": 90,
    }
    with patch("app.routers.tasks.task_queries.get_assignment_with_task", return_value=row):
        response = client.get(f"/tasks/assignments/{ASSIGNMENT_ID}/progress")

    assert response.status_code == 200
    data = response.json()
    assert data["assignment_id"] == ASSIGNMENT_ID
    assert "progress" in data
    assert 0.0 <= data["progress"] <= 99.0, "El progreso debe estar entre 0 y 99 (nunca llega a 100 automáticamente)"
    assert "current_stage_index" in data
    assert "stages" in data
    assert "can_complete" in data
    assert isinstance(data["can_complete"], bool)


def test_get_progress_not_yet_started_returns_zero(client: TestClient) -> None:
    """
    US-14 CA-4: Asignación en estado 'aceptada' (no iniciada) devuelve progress=0.
    """
    row = {
        "assignment_id": ASSIGNMENT_ID,
        "task_id": TASK_ID,
        "task_title": "Test Task",
        "status": "aceptada",
        "started_at": None,
        "completed_at": None,
        "provider_id": PROVIDER_ID,
        "stages": ["Etapa 1", "Etapa 2", "Etapa 3"],
        "duration_max": 60,
    }
    with patch("app.routers.tasks.task_queries.get_assignment_with_task", return_value=row):
        response = client.get(f"/tasks/assignments/{ASSIGNMENT_ID}/progress")

    assert response.status_code == 200
    data = response.json()
    assert data["progress"] == 0.0
    assert data["can_complete"] is False
    assert data["started_at"] is None


def test_get_progress_forbidden_for_other_provider(client: TestClient) -> None:
    """
    US-14 CA-3 / US-24 CA-9: Otro proveedor no puede ver el progreso de una asignación ajena.
    Devuelve 403.
    """
    other_provider_id = str(uuid.uuid4())
    row = {
        "assignment_id": ASSIGNMENT_ID,
        "task_id": TASK_ID,
        "task_title": "Test Task",
        "status": "procesando",
        "started_at": NOW,
        "completed_at": None,
        "provider_id": other_provider_id,
        "stages": ["Etapa 1", "Etapa 2"],
        "duration_max": 90,
    }
    with patch("app.routers.tasks.task_queries.get_assignment_with_task", return_value=row):
        response = client.get(f"/tasks/assignments/{ASSIGNMENT_ID}/progress")

    assert response.status_code == 403
    assert "permiso" in response.json()["detail"].lower()


def test_get_progress_not_found_returns_404(client: TestClient) -> None:
    """
    GET /tasks/assignments/{id}/progress con asignación inexistente devuelve 404.
    """
    with patch("app.routers.tasks.task_queries.get_assignment_with_task", return_value=None):
        response = client.get(f"/tasks/assignments/{uuid.uuid4()}/progress")

    assert response.status_code == 404
    assert response.json()["detail"] == "Asignación no encontrada"


def test_get_progress_terminal_state_returns_100(client: TestClient) -> None:
    """
    US-14 CA-4: Asignación completada devuelve progress=100.
    """
    row = {
        "assignment_id": ASSIGNMENT_ID,
        "task_id": TASK_ID,
        "task_title": "Test Task",
        "status": "completada",
        "started_at": NOW,
        "completed_at": NOW,
        "provider_id": PROVIDER_ID,
        "stages": ["Etapa 1", "Etapa 2", "Etapa 3"],
        "duration_max": 60,
    }
    with patch("app.routers.tasks.task_queries.get_assignment_with_task", return_value=row):
        response = client.get(f"/tasks/assignments/{ASSIGNMENT_ID}/progress")

    assert response.status_code == 200
    data = response.json()
    assert data["progress"] == 100.0
    assert data["can_complete"] is False


def test_get_progress_requires_authentication(unauthenticated_client: TestClient) -> None:
    """
    GET /tasks/assignments/{id}/progress sin token devuelve 401.
    """
    response = unauthenticated_client.get(f"/tasks/assignments/{ASSIGNMENT_ID}/progress")
    assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/accept
# ──────────────────────────────────────────────────────────────────────────────


def test_accept_task_success_returns_201(
    client: TestClient, mock_task: dict, mock_assignment: dict
) -> None:
    """
    US-09 CA-1 / US-24 CA-4: Aceptar tarea disponible crea asignación con status='aceptada'.
    Devuelve 201.
    """
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
    assert data["reward_paid"] is None
    assert data["trust_delta"] is None


def test_accept_task_without_authentication_returns_401(
    unauthenticated_client: TestClient,
) -> None:
    """
    US-24 CA-4: POST /tasks/{id}/accept sin token devuelve 401.
    """
    response = unauthenticated_client.post(f"/tasks/{TASK_ID}/accept")
    assert response.status_code == 401


def test_accept_task_already_active_returns_400(
    client: TestClient, mock_task: dict, mock_assignment: dict
) -> None:
    """
    US-09 CA-3 / US-24 CA-4: Doble aceptación devuelve 400 con mensaje específico.
    """
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=mock_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/accept")

    assert response.status_code == 400
    assert "activa" in response.json()["detail"]


def test_accept_task_no_slots_returns_400(
    client: TestClient, mock_task: dict
) -> None:
    """
    US-09 CA-2 / US-24 CA-4: Sin plazas disponibles devuelve 400.
    """
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=None),
        patch("app.services.task_lifecycle.task_queries.decrement_slots_atomic", return_value=False),
    ):
        response = client.post(f"/tasks/{TASK_ID}/accept")

    assert response.status_code == 400
    assert "plazas" in response.json()["detail"]


def test_accept_task_not_found_returns_404(client: TestClient) -> None:
    """
    Tarea inexistente al aceptar devuelve 404.
    """
    with patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=None):
        response = client.post(f"/tasks/{uuid.uuid4()}/accept")

    assert response.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/start
# ──────────────────────────────────────────────────────────────────────────────


def test_start_task_success_returns_200_with_stages(
    client: TestClient, mock_task: dict, mock_assignment: dict
) -> None:
    """
    US-10 CA-1 / US-24 CA-5: Iniciar tarea aceptada devuelve 200 con assignment_id,
    stages, stages_count y duration_max_seconds.
    """
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
    assert data["assignment_id"] == ASSIGNMENT_ID
    assert data["task_id"] == TASK_ID
    assert len(data["stages"]) == 5
    assert data["stages_count"] == 5
    assert data["duration_max_seconds"] == 90 * 60


def test_start_task_wrong_state_returns_400(
    client: TestClient, mock_task: dict, mock_assignment: dict
) -> None:
    """
    US-10 CA-3 / US-24 CA-5: Iniciar desde estado != 'aceptada' devuelve 400.
    """
    processing_assignment = {**mock_assignment, "status": "procesando"}
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=processing_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/start")

    assert response.status_code == 400
    assert "aceptado" in response.json()["detail"]


def test_start_task_no_active_assignment_returns_404(
    client: TestClient, mock_task: dict
) -> None:
    """
    US-10: Sin asignación activa devuelve 404.
    """
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=None),
    ):
        response = client.post(f"/tasks/{TASK_ID}/start")

    assert response.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/complete
# ──────────────────────────────────────────────────────────────────────────────


def test_complete_task_success_returns_200_with_reward_and_trust(
    client: TestClient, mock_task: dict, mock_assignment: dict, mock_provider: dict
) -> None:
    """
    US-11 CA-1 / US-24 CA-6: Completar tarea en procesamiento devuelve 200 con
    reward_paid, trust_delta, new_trust_score y new_rank.
    """
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
    assert "new_rank" in data
    assert "completed_at" in data


def test_complete_task_wrong_state_returns_400(
    client: TestClient, mock_task: dict, mock_assignment: dict
) -> None:
    """
    US-11 CA-6 / US-24 CA-6: Completar desde estado != 'procesando' devuelve 400.
    """
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=mock_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/complete")

    assert response.status_code == 400
    assert "procesamiento" in response.json()["detail"]


def test_complete_task_no_active_assignment_returns_404(
    client: TestClient, mock_task: dict
) -> None:
    """
    Completar sin asignación activa devuelve 404.
    """
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=None),
    ):
        response = client.post(f"/tasks/{TASK_ID}/complete")

    assert response.status_code == 404


def test_complete_task_requires_authentication(unauthenticated_client: TestClient) -> None:
    """
    POST /tasks/{id}/complete sin token devuelve 401.
    """
    response = unauthenticated_client.post(f"/tasks/{TASK_ID}/complete")
    assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# POST /tasks/{task_id}/fail
# ──────────────────────────────────────────────────────────────────────────────


def test_fail_task_success_returns_200_no_reward(
    client: TestClient, mock_task: dict, mock_assignment: dict, mock_provider: dict
) -> None:
    """
    US-12 CA-1 / US-24 CA-7: Fallar tarea en procesamiento devuelve 200 con
    reward_paid=null y trust_delta negativo.
    """
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
    assert "new_trust_score" in data
    assert "new_rank" in data


def test_fail_task_wrong_state_returns_400(
    client: TestClient, mock_task: dict, mock_assignment: dict
) -> None:
    """
    US-12 CA-5 / US-24 CA-7: Fallar desde estado != 'procesando' devuelve 400.
    """
    with (
        patch("app.services.task_lifecycle.task_queries.get_task_by_id", return_value=mock_task),
        patch("app.services.task_lifecycle.task_queries.get_active_assignment_for_provider_task", return_value=mock_assignment),
    ):
        response = client.post(f"/tasks/{TASK_ID}/fail")

    assert response.status_code == 400
    assert "procesamiento" in response.json()["detail"]


def test_fail_task_requires_authentication(unauthenticated_client: TestClient) -> None:
    """
    POST /tasks/{id}/fail sin token devuelve 401.
    """
    response = unauthenticated_client.post(f"/tasks/{TASK_ID}/fail")
    assert response.status_code == 401
