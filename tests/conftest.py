"""
Fixtures compartidas para los tests de Co-Computing.

Estrategia de mocking:
- Las dependencias de Supabase (DB queries) se mockean con unittest.mock.patch.
- La dependencia get_current_provider se sobreescribe via FastAPI dependency_overrides.
- No se llama a hash_password/bcrypt en los fixtures para evitar problemas de
  compatibilidad de passlib con Python 3.14+.
"""
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ──────────────────────────────────────────────────────────────────────────────
# Configurar variables de entorno ANTES de importar la app, para que
# pydantic-settings pueda construir el objeto Settings.
# ──────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "eyJtest_service_role_key")
os.environ.setdefault("SUPABASE_DB_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "testsecretkey32charsminimumrequired1234")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_DAYS", "7")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("ENVIRONMENT", "development")

# Añadir el directorio backend al path para poder importar 'app'
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(BACKEND_DIR))

from app.core.dependencies import get_current_provider  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402

# ──────────────────────────────────────────────────────────────────────────────
# Constantes compartidas entre fixtures y tests
# ──────────────────────────────────────────────────────────────────────────────

PROVIDER_ID = str(uuid.uuid4())
TASK_ID = str(uuid.uuid4())
ASSIGNMENT_ID = str(uuid.uuid4())
WALLET_ID = str(uuid.uuid4())

NOW = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)

# Hash de 'password123' pre-computado (formato $2b$ de bcrypt, rounds=4 para tests)
# Usar una cadena literal para no depender de passlib/bcrypt en fixture setup.
TEST_PASSWORD_PLAIN = "password123"
TEST_PASSWORD_HASH = "$2b$04$DAu7xKXn4q4ySq.9bJyBUejaShK.w3UV7Vjguec2.Y/5La7NDhIYG"


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures de datos de ejemplo
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_provider() -> dict:
    """Proveedor de prueba con datos completos. No llama a bcrypt en setup."""
    return {
        "id": PROVIDER_ID,
        "email": "test@example.com",
        "full_name": "Test Provider",
        "password_hash": TEST_PASSWORD_HASH,
        "trust_score": 55.00,
        "rank": "confiable",
        "tasks_completed": 5,
        "success_rate": 83.33,
        "total_earned": 25.00,
        "completion_rate": 83.33,
        "accuracy": 82.00,
        "response_time_score": 70.00,
        "client_rating": 70.00,
        "cpu_model": "Intel Core i9-13900K",
        "gpu_model": "NVIDIA RTX 4080",
        "ram_gb": 32,
        "storage_gb": 1000,
        "is_online": True,
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture
def mock_task() -> dict:
    """Tarea disponible con stages completos."""
    return {
        "id": TASK_ID,
        "title": "Entrenamiento ML — ResNet-50 CIFAR-100",
        "task_type": "entrenamiento_ml",
        "description": "Entrenamiento completo de ResNet-50 sobre CIFAR-100.",
        "reward": 5.00,
        "duration_min": 45,
        "duration_max": 90,
        "difficulty": "dificil",
        "hardware_required": "gpu",
        "total_slots": 5,
        "slots_left": 3,
        "stages": [
            "Preparando entorno",
            "Descargando dataset",
            "Entrenando modelo",
            "Validando precisión",
            "Guardando checkpoints",
        ],
        "requester_name": "AI Research Lab",
        "status": "disponible",
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture
def mock_assignment(mock_provider: dict, mock_task: dict) -> dict:
    """Asignación en estado 'aceptada'."""
    return {
        "id": ASSIGNMENT_ID,
        "task_id": TASK_ID,
        "provider_id": PROVIDER_ID,
        "status": "aceptada",
        "reward_paid": None,
        "trust_delta": None,
        "accepted_at": NOW,
        "started_at": None,
        "completed_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture
def mock_wallet() -> dict:
    """Cartera de prueba con saldos realistas."""
    return {
        "id": WALLET_ID,
        "provider_id": PROVIDER_ID,
        "available_balance": 15.00,
        "pending_balance": 0.00,
        "total_earned": 25.00,
        "total_withdrawn": 10.00,
        "created_at": NOW,
        "updated_at": NOW,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures de cliente HTTP
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def client(mock_provider: dict) -> Generator[TestClient, None, None]:
    """
    TestClient autenticado: get_current_provider devuelve mock_provider.
    Usar para endpoints que requieren autenticación.
    """

    def override_get_current_provider() -> dict:
        return mock_provider

    app.dependency_overrides[get_current_provider] = override_get_current_provider
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client() -> Generator[TestClient, None, None]:
    """
    TestClient sin override de autenticación.
    Usar para verificar comportamiento sin token o con token inválido.
    """
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def auth_headers(mock_provider: dict) -> dict:
    """Headers con JWT válido del proveedor de prueba."""
    token = create_access_token(subject=mock_provider["id"])
    return {"Authorization": f"Bearer {token}"}
