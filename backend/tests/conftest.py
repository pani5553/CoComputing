"""
Test configuration: TestClient, fixtures, and dependency overrides.

All database calls are mocked via unittest.mock.patch on the query modules.
No real database connections are made during testing.
"""
import uuid
from datetime import datetime, timezone
from typing import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_provider
from app.core.security import create_access_token, hash_password
from app.main import app
from app.routers.auth import login_rate_limiter, register_rate_limiter
from app.routers.work import claim_rate_limiter, submit_rate_limiter

# ──────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ──────────────────────────────────────────────────────────────────────────────

PROVIDER_ID = str(uuid.uuid4())
TASK_ID = str(uuid.uuid4())
ASSIGNMENT_ID = str(uuid.uuid4())

NOW = datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_provider() -> dict:
    return {
        "id": PROVIDER_ID,
        "email": "test@example.com",
        "full_name": "Test Provider",
        "password_hash": hash_password("password123"),
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
    return {
        "id": TASK_ID,
        "title": "Entrenamiento ML — ResNet-50 CIFAR-100",
        "task_type": "entrenamiento_ml",
        "description": "Entrenamiento completo de ResNet-50.",
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
    return {
        "id": str(uuid.uuid4()),
        "provider_id": PROVIDER_ID,
        "available_balance": 15.00,
        "pending_balance": 0.00,
        "total_earned": 25.00,
        "total_withdrawn": 10.00,
        "created_at": NOW,
        "updated_at": NOW,
    }


# ──────────────────────────────────────────────────────────────────────────────
# TestClient with dependency override for authentication
# ──────────────────────────────────────────────────────────────────────────────


def _bypass_provider_rate_limit(mock_provider: dict):
    """
    Override for the `rate_limit_by_provider(...)` dependencies used by
    /work/claim and /work/submit: returns the mock provider without hitting
    Postgres or counting towards any limit. Existing tests that fire several
    requests in a row must not start failing with 429 just because the new
    dependency was added — see docs/04-arquitectura.md §15.8.
    """

    def _override() -> dict:
        return mock_provider

    return _override


def _bypass_ip_rate_limit() -> None:
    """No-op override for the `rate_limit_by_ip(...)` dependencies used by
    /auth/register and /auth/login (see docs/04-arquitectura.md §15.8)."""
    return None


@pytest.fixture
def client(mock_provider: dict) -> Generator[TestClient, None, None]:
    """
    TestClient with get_current_provider overridden to return mock_provider.
    Rate-limiting dependencies are also bypassed by default so tests that
    make several requests in a row don't hit the real DB or a 429 — tests
    that specifically exercise rate limiting override these back explicitly.
    Use this fixture for authenticated endpoints.
    """

    def override_get_current_provider() -> dict:
        return mock_provider

    app.dependency_overrides[get_current_provider] = override_get_current_provider
    app.dependency_overrides[claim_rate_limiter] = _bypass_provider_rate_limit(mock_provider)
    app.dependency_overrides[submit_rate_limiter] = _bypass_provider_rate_limit(mock_provider)
    app.dependency_overrides[register_rate_limiter] = _bypass_ip_rate_limit
    app.dependency_overrides[login_rate_limiter] = _bypass_ip_rate_limit
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client() -> Generator[TestClient, None, None]:
    """
    TestClient without authentication override. Used for auth endpoint tests.
    Rate-limiting dependencies for the public auth endpoints are bypassed by
    default for the same reason as the `client` fixture above; tests that
    exercise rate limiting itself clear these overrides explicitly.
    """
    app.dependency_overrides.clear()
    app.dependency_overrides[register_rate_limiter] = _bypass_ip_rate_limit
    app.dependency_overrides[login_rate_limiter] = _bypass_ip_rate_limit
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def valid_token(mock_provider: dict) -> str:
    """Return a valid JWT for the mock provider."""
    return create_access_token(subject=mock_provider["id"])
