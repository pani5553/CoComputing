"""
Tests for profile endpoints.

Coverage:
- GET /profile/stats: ok
- PUT /profile/hardware: ok, validation failure
- PATCH /profile/online: ok
- PATCH /profile/name: ok
"""
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.conftest import NOW, PROVIDER_ID


# ──────────────────────────────────────────────────────────────────────────────
# GET /profile/stats
# ──────────────────────────────────────────────────────────────────────────────


def test_get_stats_ok(client: TestClient, mock_provider: dict) -> None:
    """Returns the full profile with trust score detail and rank info."""
    with patch("app.routers.profile.get_provider_by_id", return_value=mock_provider):
        response = client.get("/profile/stats")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "trust_score_detail" in data
    assert "rank_info" in data
    assert "hardware" in data

    trust_detail = data["trust_score_detail"]
    assert trust_detail["completion_rate_weight"] == 0.40
    assert trust_detail["accuracy_weight"] == 0.30
    assert trust_detail["response_time_weight"] == 0.20
    assert trust_detail["client_rating_weight"] == 0.10

    rank_info = data["rank_info"]
    assert rank_info["current_rank"] == "confiable"
    assert rank_info["next_rank"] == "experto"
    assert rank_info["points_to_next_rank"] is not None


def test_get_stats_elite_provider(client: TestClient, mock_provider: dict) -> None:
    """Elite provider has no next_rank in rank_info."""
    elite_provider = {
        **mock_provider,
        "trust_score": 95.00,
        "rank": "elite",
    }
    with patch("app.routers.profile.get_provider_by_id", return_value=elite_provider):
        response = client.get("/profile/stats")

    assert response.status_code == 200
    rank_info = response.json()["rank_info"]
    assert rank_info["current_rank"] == "elite"
    assert rank_info["next_rank"] is None
    assert rank_info["points_to_next_rank"] is None


# ──────────────────────────────────────────────────────────────────────────────
# PUT /profile/hardware
# ──────────────────────────────────────────────────────────────────────────────


def test_update_hardware_ok(client: TestClient, mock_provider: dict) -> None:
    """Successfully updates hardware specifications."""
    updated = {
        **mock_provider,
        "cpu_model": "AMD Ryzen 9 7950X",
        "gpu_model": "NVIDIA RTX 4090",
        "ram_gb": 64,
        "storage_gb": 2000,
    }
    with patch("app.routers.profile.update_hardware", return_value=updated):
        response = client.put(
            "/profile/hardware",
            json={
                "cpu_model": "AMD Ryzen 9 7950X",
                "gpu_model": "NVIDIA RTX 4090",
                "ram_gb": 64,
                "storage_gb": 2000,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["cpu_model"] == "AMD Ryzen 9 7950X"
    assert data["ram_gb"] == 64


def test_update_hardware_invalid_ram(client: TestClient) -> None:
    """Returns 422 when ram_gb is 0 (must be >= 1)."""
    response = client.put(
        "/profile/hardware",
        json={
            "cpu_model": "Intel Core i9",
            "gpu_model": None,
            "ram_gb": 0,
            "storage_gb": 500,
        },
    )
    assert response.status_code == 422


def test_update_hardware_missing_cpu(client: TestClient) -> None:
    """Returns 422 when cpu_model is missing."""
    response = client.put(
        "/profile/hardware",
        json={
            "ram_gb": 16,
            "storage_gb": 500,
        },
    )
    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /profile/online
# ──────────────────────────────────────────────────────────────────────────────


def test_toggle_online_ok(client: TestClient, mock_provider: dict) -> None:
    """Successfully toggles online status."""
    updated = {**mock_provider, "is_online": False}
    with patch("app.routers.profile.toggle_online", return_value=updated):
        response = client.patch("/profile/online", json={"is_online": False})

    assert response.status_code == 200
    data = response.json()
    assert data["is_online"] is False
    assert "updated_at" in data


def test_toggle_online_missing_field(client: TestClient) -> None:
    """Returns 422 when is_online field is missing."""
    response = client.patch("/profile/online", json={})
    assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /profile/name
# ──────────────────────────────────────────────────────────────────────────────


def test_update_name_ok(client: TestClient, mock_provider: dict) -> None:
    """Successfully updates provider full name."""
    updated = {**mock_provider, "full_name": "Ana García López"}
    with patch("app.routers.profile.update_name", return_value=updated):
        response = client.patch("/profile/name", json={"full_name": "Ana García López"})

    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana García López"


def test_update_name_empty_string(client: TestClient) -> None:
    """Returns 422 when full_name is empty."""
    response = client.patch("/profile/name", json={"full_name": ""})
    assert response.status_code == 422
