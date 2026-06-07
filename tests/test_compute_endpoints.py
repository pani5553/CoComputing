"""
Tests para los endpoints del pipeline de cómputo distribuido.

Criterios de aceptación validados (US-31 a US-36, US-40):
- POST /jobs: JSON success, CSV success, CSV too large, unauthenticated
- GET /jobs: lista vacía, con datos
- GET /jobs/{id}: job propio (200+progress), otro proveedor (403), no encontrado (404)
- GET /jobs/{id}/result: completado (200), en procesamiento (400)
- POST /work/claim: devuelve lista, validación max_chunks
- POST /work/{id}/submit: success, duration_ms=0 (422), chunk no encontrado (404)

Todas las llamadas a Supabase/psycopg2 están mockeadas.
No se realizan conexiones reales a la base de datos.
"""
import io
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import NOW, PROVIDER_ID

# ── IDs compartidos ────────────────────────────────────────────────────────────

JOB_ID = str(uuid.uuid4())
CHUNK_ID = str(uuid.uuid4())
CHUNK_RESULT_ID = str(uuid.uuid4())
OTHER_PROVIDER_ID = str(uuid.uuid4())


# ── Helpers de datos ──────────────────────────────────────────────────────────

def _make_job(
    *,
    status: str = "processing",
    completed_chunks: int = 0,
    total_chunks: int = 2,
    result: dict | None = None,
    client_id: str = PROVIDER_ID,
) -> dict:
    """Genera un dict que simula la fila de un job en Supabase."""
    return {
        "id": JOB_ID,
        "client_id": client_id,
        "job_type": "data-processing",
        "status": status,
        "params": {"operation": "mean", "columns": ["col1"]},
        "total_chunks": total_chunks,
        "completed_chunks": completed_chunks,
        "reward_total": round(total_chunks * 0.10, 2),
        "result": result,
        "created_at": NOW,
        "completed_at": (
            datetime(2026, 6, 5, 15, 0, 0, tzinfo=timezone.utc)
            if status == "completed"
            else None
        ),
    }


def _small_csv() -> bytes:
    """CSV mínimo válido (10 filas de datos)."""
    lines = ["col1,col2"]
    for i in range(10):
        lines.append(f"{i},{i * 2}")
    return "\n".join(lines).encode("utf-8")


def _large_csv() -> bytes:
    """CSV que supera los 10 MB."""
    header = "col1,col2\n"
    row = "1234567890," * 10 + "1234567890\n"
    repetitions = (11 * 1024 * 1024) // len(row) + 1
    return (header + row * repetitions).encode("utf-8")


def _mock_job_creation(job: dict):
    """Context manager helper: mockea las 4 llamadas de compute_queries para crear un job."""
    return (
        patch("app.services.compute_service.compute_queries.create_job", return_value=job),
        patch("app.services.compute_service.compute_queries.update_job_status", return_value=job),
        patch("app.services.compute_service.compute_queries.create_chunks", return_value=[{}]),
        patch("app.services.compute_service.compute_queries.update_job_chunks_count", return_value=job),
    )


# ══════════════════════════════════════════════════════════════════════════════
# POST /jobs — Crear un job
# ══════════════════════════════════════════════════════════════════════════════


def test_create_job_json_success(client: TestClient) -> None:
    """
    US-31 CA-6/7: POST /jobs con datos embebidos en JSON devuelve 201
    con id, status=processing y total_chunks >= 1.
    """
    job = _make_job(total_chunks=1, completed_chunks=0)
    p1, p2, p3, p4 = _mock_job_creation(job)
    with p1, p2, p3, p4:
        response = client.post(
            "/jobs",
            json={
                "job_type": "data-processing",
                "params": {
                    "operation": "mean",
                    "columns": ["col1"],
                    "data": [[1], [2], [3]],
                },
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "processing"
    assert data["total_chunks"] >= 1


def test_create_job_csv_success(client: TestClient) -> None:
    """
    US-31 CA-2/6: POST /jobs con multipart CSV válido devuelve 201.
    """
    job = _make_job(total_chunks=1, completed_chunks=0)
    p1, p2, p3, p4 = _mock_job_creation(job)
    with p1, p2, p3, p4:
        response = client.post(
            "/jobs",
            data={
                "job_type": "data-processing",
                "params": '{"operation":"mean","columns":["col1"]}',
            },
            files={"file": ("data.csv", io.BytesIO(_small_csv()), "text/csv")},
        )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "processing"


def test_create_job_csv_too_large(client: TestClient) -> None:
    """
    US-31 CA-2: CSV mayor de 10 MB devuelve 413.
    """
    response = client.post(
        "/jobs",
        data={
            "job_type": "data-processing",
            "params": '{"operation":"mean","columns":["col1"]}',
        },
        files={"file": ("big.csv", io.BytesIO(_large_csv()), "text/csv")},
    )

    assert response.status_code == 413


def test_create_job_unauthenticated(unauthenticated_client: TestClient) -> None:
    """
    US-31 CA-10: POST /jobs sin JWT devuelve 401.
    """
    response = unauthenticated_client.post(
        "/jobs",
        json={
            "job_type": "data-processing",
            "params": {"operation": "mean", "data": [[1], [2]]},
        },
    )
    assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# GET /jobs — Listar jobs del cliente
# ══════════════════════════════════════════════════════════════════════════════


def test_get_jobs_empty(client: TestClient) -> None:
    """
    US-32 CA-4: GET /jobs sin jobs devuelve 200 con lista vacía.
    """
    with patch("app.services.compute_service.compute_queries.get_jobs_by_client", return_value=[]):
        response = client.get("/jobs")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["jobs"] == []


def test_get_jobs_with_data(client: TestClient, mock_provider: dict) -> None:
    """
    US-32 CA-1/2: GET /jobs con jobs existentes devuelve la lista correcta
    con estado y porcentaje de progreso por job.
    """
    jobs = [_make_job(total_chunks=2, completed_chunks=1, client_id=str(mock_provider["id"]))]
    with patch("app.services.compute_service.compute_queries.get_jobs_by_client", return_value=jobs):
        response = client.get("/jobs")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["jobs"][0]["id"] == JOB_ID
    assert data["jobs"][0]["status"] == "processing"
    # progress = 1/2 * 100 = 50.0
    assert data["jobs"][0]["progress"] == 50.0


# ══════════════════════════════════════════════════════════════════════════════
# GET /jobs/{id} — Detalle de un job
# ══════════════════════════════════════════════════════════════════════════════


def test_get_job_own(client: TestClient, mock_provider: dict) -> None:
    """
    US-33 CA-1/2: GET /jobs/{id} del propio cliente devuelve 200
    con campo progress calculado correctamente (1/3 * 100 ≈ 33.3).
    Usa el mock_provider fixture para asegurar que client_id coincide con
    el proveedor autenticado en el override de dependencias.
    """
    job = _make_job(total_chunks=3, completed_chunks=1, client_id=str(mock_provider["id"]))
    with patch("app.services.compute_service.compute_queries.get_job", return_value=job):
        response = client.get(f"/jobs/{JOB_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == JOB_ID
    assert "progress" in data
    assert abs(data["progress"] - 33.3) < 0.1


def test_get_job_other_provider(client: TestClient) -> None:
    """
    US-33 CA-6: GET /jobs/{id} de job que pertenece a otro cliente devuelve 403.
    """
    job = _make_job(client_id=OTHER_PROVIDER_ID)
    with patch("app.services.compute_service.compute_queries.get_job", return_value=job):
        response = client.get(f"/jobs/{JOB_ID}")

    assert response.status_code == 403


def test_get_job_not_found(client: TestClient) -> None:
    """
    US-33 CA-7: GET /jobs/{id} con UUID inexistente devuelve 404.
    """
    with patch("app.services.compute_service.compute_queries.get_job", return_value=None):
        response = client.get(f"/jobs/{uuid.uuid4()}")

    assert response.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# GET /jobs/{id}/result — Resultado consolidado
# ══════════════════════════════════════════════════════════════════════════════


def test_get_job_result_completed(client: TestClient, mock_provider: dict) -> None:
    """
    US-34 CA-1/2: GET /jobs/{id}/result con job en estado 'completed'
    devuelve 200 con el campo result poblado.
    """
    job = _make_job(
        status="completed",
        total_chunks=2,
        completed_chunks=2,
        result={"col1_mean": 5.0},
        client_id=str(mock_provider["id"]),
    )
    with patch("app.services.compute_service.compute_queries.get_job", return_value=job):
        response = client.get(f"/jobs/{JOB_ID}/result")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "result" in data
    assert data["result"]["col1_mean"] == 5.0


def test_get_job_result_not_completed(client: TestClient, mock_provider: dict) -> None:
    """
    US-34 CA-1: GET /jobs/{id}/result con job en estado 'processing' devuelve 400.
    El resultado no está disponible mientras el job sigue en curso.
    """
    job = _make_job(status="processing", total_chunks=2, completed_chunks=0,
                    client_id=str(mock_provider["id"]))
    with patch("app.services.compute_service.compute_queries.get_job", return_value=job):
        response = client.get(f"/jobs/{JOB_ID}/result")

    assert response.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# POST /work/claim — Worker reclama chunks
# ══════════════════════════════════════════════════════════════════════════════


def test_claim_chunks_returns_list(client: TestClient) -> None:
    """
    US-36 CA-6: POST /work/claim sin chunks disponibles devuelve 200
    con lista vacía (no 404).
    """
    with patch("app.routers.work.compute_queries.claim_chunks_atomic", return_value=[]):
        response = client.post("/work/claim", json={"max_chunks": 3})

    assert response.status_code == 200
    data = response.json()
    assert "chunks" in data
    assert isinstance(data["chunks"], list)
    assert data["chunks"] == []


def test_claim_chunks_with_available_chunks(client: TestClient) -> None:
    """
    US-36 CA-1: POST /work/claim con chunks disponibles devuelve la lista
    con los campos requeridos: chunk_id, job_id, chunk_index, job_type, payload.
    """
    raw_chunks = [
        {
            "chunk_id": CHUNK_ID,
            "job_id": JOB_ID,
            "chunk_index": 0,
            "payload": {
                "rows": [["1"], ["2"]],
                "columns": ["col1"],
                "operation": "mean",
                "target_columns": ["col1"],
            },
            "job_type": "data-processing",
            "replicas_needed": 2,
        }
    ]
    with patch("app.routers.work.compute_queries.claim_chunks_atomic", return_value=raw_chunks):
        response = client.post("/work/claim", json={"max_chunks": 3})

    assert response.status_code == 200
    data = response.json()
    assert len(data["chunks"]) == 1
    chunk = data["chunks"][0]
    assert chunk["chunk_id"] == CHUNK_ID
    assert chunk["job_id"] == JOB_ID
    assert chunk["chunk_index"] == 0
    assert chunk["job_type"] == "data-processing"


def test_claim_chunks_max_validation(client: TestClient) -> None:
    """
    US-36 CA-1: max_chunks mayor que 10 falla validación Pydantic y devuelve 422.
    El campo tiene le=10 en ClaimRequest.
    """
    response = client.post("/work/claim", json={"max_chunks": 99})
    assert response.status_code == 422


def test_claim_chunks_unauthenticated(unauthenticated_client: TestClient) -> None:
    """
    US-36 CA-5: POST /work/claim sin JWT devuelve 401.
    """
    response = unauthenticated_client.post("/work/claim", json={"max_chunks": 3})
    assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# POST /work/{id}/submit — Worker entrega resultado
# ══════════════════════════════════════════════════════════════════════════════


def test_submit_chunk_success(client: TestClient, mock_provider: dict) -> None:
    """
    US-36 CA-3: POST /work/{id}/submit con result válido y duration_ms > 0
    devuelve 200 con chunk_result_id y status del chunk.
    El chunk.assigned_to debe coincidir con el proveedor autenticado.
    """
    provider_id = str(mock_provider["id"])
    chunk = {
        "id": CHUNK_ID,
        "job_id": JOB_ID,
        "status": "assigned",
        "assigned_to": provider_id,
        "replicas_needed": 2,
    }
    cr_row = {
        "id": CHUNK_RESULT_ID,
        "chunk_id": CHUNK_ID,
        "provider_id": provider_id,
        "result": {"col1_mean": 3.0},
        "duration_ms": 150,
        "is_valid": None,
    }

    with patch("app.services.consensus_service.compute_queries.get_chunk", return_value=chunk), \
         patch("app.services.consensus_service.compute_queries.get_chunk_results", return_value=[]), \
         patch("app.services.consensus_service.compute_queries.submit_chunk_result", return_value=cr_row):

        response = client.post(
            f"/work/{CHUNK_ID}/submit",
            json={"result": {"col1_mean": 3.0}, "duration_ms": 150},
        )

    assert response.status_code == 200
    data = response.json()
    assert "chunk_result_id" in data
    assert "status" in data
    assert "message" in data


def test_submit_chunk_duration_zero(client: TestClient) -> None:
    """
    US-36 CA-3: duration_ms = 0 debe fallar validación Pydantic (Field gt=0)
    y devolver 422. Un submit con duración cero es inválido.
    """
    response = client.post(
        f"/work/{CHUNK_ID}/submit",
        json={"result": {"col1_mean": 3.0}, "duration_ms": 0},
    )
    assert response.status_code == 422


def test_submit_chunk_not_found(client: TestClient) -> None:
    """
    US-36 CA-3: POST /work/{id}/submit para un chunk inexistente devuelve 404.
    """
    with patch("app.services.consensus_service.compute_queries.get_chunk", return_value=None):
        response = client.post(
            f"/work/{uuid.uuid4()}/submit",
            json={"result": {"col1_mean": 3.0}, "duration_ms": 100},
        )
    assert response.status_code == 404


def test_submit_chunk_unauthenticated(unauthenticated_client: TestClient) -> None:
    """
    US-36 CA-5: POST /work/{id}/submit sin JWT devuelve 401.
    """
    response = unauthenticated_client.post(
        f"/work/{CHUNK_ID}/submit",
        json={"result": {"col1_mean": 3.0}, "duration_ms": 100},
    )
    assert response.status_code == 401
