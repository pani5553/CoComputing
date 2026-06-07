"""
Tests for compute pipeline — job creation, listing, status and result endpoints.

All database calls are mocked. No real DB connection is made.
Test IDs: C-01 to C-05 (from docs/04-arquitectura.md §12.9)
"""
import io
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import PROVIDER_ID

JOB_ID = str(uuid.uuid4())
CHUNK_ID = str(uuid.uuid4())
NOW = datetime(2026, 6, 7, 10, 0, 0, tzinfo=timezone.utc)


def _make_job(status="processing", total_chunks=3, completed_chunks=0):
    return {
        "id": JOB_ID,
        "client_id": PROVIDER_ID,
        "job_type": "data-processing",
        "status": status,
        "params": {"operation": "mean", "columns": ["col1", "col2"]},
        "total_chunks": total_chunks,
        "completed_chunks": completed_chunks,
        "reward_total": round(0.10 * total_chunks, 2),
        "result": None,
        "created_at": NOW,
        "completed_at": None,
    }


def _csv_with_rows(n_rows: int) -> bytes:
    """Generate a simple CSV with n_rows data rows."""
    lines = ["col1,col2"]
    for i in range(n_rows):
        lines.append(f"{i},{i * 2}")
    return "\n".join(lines).encode()


# ── C-01: POST /jobs with CSV of 1200 rows → 3 chunks, status=processing ────

@patch("app.db.queries.compute_queries.update_job_chunks_count")
@patch("app.db.queries.compute_queries.create_chunks")
@patch("app.db.queries.compute_queries.update_job_status")
@patch("app.db.queries.compute_queries.create_job")
def test_c01_post_jobs_csv_1200_rows_creates_3_chunks(
    mock_create_job,
    mock_update_status,
    mock_create_chunks,
    mock_update_count,
    client,
):
    """C-01: 1200-row CSV → job with 3 chunks (ceil(1200/500)), status=processing."""
    job_row = _make_job(total_chunks=3)
    mock_create_job.return_value = {**job_row, "status": "pending", "total_chunks": 0}
    mock_update_status.return_value = {**job_row, "status": "splitting"}
    mock_create_chunks.return_value = [{"id": str(uuid.uuid4())} for _ in range(3)]
    mock_update_count.return_value = job_row

    csv_bytes = _csv_with_rows(1200)
    response = client.post(
        "/jobs",
        data={"job_type": "data-processing", "params": '{"operation":"mean"}'},
        files={"file": ("data.csv", io.BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["total_chunks"] == 3
    assert body["status"] == "processing"
    assert body["job_type"] == "data-processing"
    # Verify 3 chunk payloads were inserted
    args, _ = mock_create_chunks.call_args
    assert len(args[1]) == 3  # args[1] = payloads list


# ── C-02: GET /jobs lists only the authenticated provider's jobs ──────────────

@patch("app.db.queries.compute_queries.get_jobs_by_client")
def test_c02_get_jobs_returns_own_jobs_only(mock_get_jobs, client):
    """C-02: GET /jobs returns only jobs belonging to the authenticated provider."""
    mock_get_jobs.return_value = [_make_job()]

    response = client.get("/jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["jobs"][0]["client_id"] == PROVIDER_ID
    mock_get_jobs.assert_called_once_with(PROVIDER_ID, None)


# ── C-03: GET /jobs/{id} progress = completed_chunks / total_chunks * 100 ────

@patch("app.db.queries.compute_queries.get_job")
def test_c03_get_job_progress_calculation(mock_get_job, client):
    """C-03: progress field = completed_chunks / total_chunks * 100."""
    mock_get_job.return_value = _make_job(total_chunks=4, completed_chunks=2)

    response = client.get(f"/jobs/{JOB_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["progress"] == 50.0
    assert body["completed_chunks"] == 2
    assert body["total_chunks"] == 4


# ── C-04: GET /jobs/{id}/result returns 400 if job not completed ─────────────

@patch("app.db.queries.compute_queries.get_job")
def test_c04_get_job_result_returns_400_if_not_completed(mock_get_job, client):
    """C-04: /result endpoint returns 400 when status != completed."""
    mock_get_job.return_value = _make_job(status="processing")

    response = client.get(f"/jobs/{JOB_ID}/result")

    assert response.status_code == 400
    assert "processing" in response.json()["detail"]


# ── C-05: POST /jobs with empty CSV → 400 ────────────────────────────────────

def test_c05_post_jobs_empty_csv_returns_400(client):
    """C-05: Empty CSV file → 400 Bad Request."""
    response = client.post(
        "/jobs",
        data={"job_type": "data-processing", "params": '{"operation":"mean"}'},
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 400


# ── Extra: GET /jobs/{id}/result returns result when completed ────────────────

@patch("app.db.queries.compute_queries.get_job")
def test_get_job_result_returns_data_when_completed(mock_get_job, client):
    """Completed job with result → /result returns the consolidated result dict."""
    job = _make_job(status="completed", total_chunks=2, completed_chunks=2)
    job["result"] = {"col1_mean": 1.5, "col2_mean": 3.0}
    job["completed_at"] = NOW
    mock_get_job.return_value = job

    response = client.get(f"/jobs/{JOB_ID}/result")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"]["col1_mean"] == 1.5


# ── Extra: GET /jobs/{id} returns 403 when job belongs to another provider ───

@patch("app.db.queries.compute_queries.get_job")
def test_get_job_forbidden_when_not_owner(mock_get_job, client):
    """GET /jobs/{id} returns 403 when client_id != authenticated provider."""
    other_job = _make_job()
    other_job["client_id"] = str(uuid.uuid4())  # different owner
    mock_get_job.return_value = other_job

    response = client.get(f"/jobs/{JOB_ID}")

    assert response.status_code == 403


# ── Extra: GET /jobs/{id} returns 404 for unknown job ────────────────────────

@patch("app.db.queries.compute_queries.get_job")
def test_get_job_not_found(mock_get_job, client):
    """GET /jobs/{id} returns 404 when job does not exist."""
    mock_get_job.return_value = None

    response = client.get(f"/jobs/{uuid.uuid4()}")

    assert response.status_code == 404


# ── Extra: CSV > 10 MB returns 413 ───────────────────────────────────────────

def test_post_jobs_csv_too_large_returns_413(client):
    """File larger than 10 MB returns 413."""
    big_content = b"a" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/jobs",
        data={"job_type": "data-processing", "params": '{"operation":"mean"}'},
        files={"file": ("big.csv", io.BytesIO(big_content), "text/csv")},
    )
    assert response.status_code == 413


# ── Extra: GET /jobs with status filter ──────────────────────────────────────

@patch("app.db.queries.compute_queries.get_jobs_by_client")
def test_get_jobs_with_status_filter(mock_get_jobs, client):
    """GET /jobs?status=completed passes status filter to the query."""
    mock_get_jobs.return_value = []

    response = client.get("/jobs?status=completed")

    assert response.status_code == 200
    mock_get_jobs.assert_called_once_with(PROVIDER_ID, "completed")


# ── Extra: DataProcessingPlugin stdlib fallback ───────────────────────────────

def test_data_processing_plugin_stdlib():
    """DataProcessingPlugin._process_stdlib correctly computes mean."""
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = {
        "rows": [["1", "10"], ["2", "20"], ["3", "30"]],
        "columns": ["x", "y"],
        "operation": "mean",
        "target_columns": ["x", "y"],
    }
    result = plugin._process_stdlib(
        payload["rows"], payload["columns"], payload["operation"], payload["target_columns"]
    )
    assert result["x_mean"] == pytest.approx(2.0, rel=1e-5)
    assert result["y_mean"] == pytest.approx(20.0, rel=1e-5)


def test_data_processing_plugin_sum():
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = {
        "rows": [["1"], ["2"], ["3"]],
        "columns": ["v"],
        "operation": "sum",
        "target_columns": ["v"],
    }
    result = plugin._process_stdlib(
        payload["rows"], payload["columns"], payload["operation"], payload["target_columns"]
    )
    assert result["v_sum"] == pytest.approx(6.0)


# ── Extra: split_csv helper ───────────────────────────────────────────────────

def test_split_csv_creates_correct_number_of_chunks():
    from app.services.compute_service import split_csv

    csv_bytes = _csv_with_rows(1001)
    params = {"operation": "mean"}
    chunks = split_csv(csv_bytes, params, chunk_size=500)
    assert len(chunks) == 3  # ceil(1001/500)
    assert len(chunks[0]["rows"]) == 500
    assert len(chunks[2]["rows"]) == 1


def test_split_csv_empty_raises():
    from app.services.compute_service import split_csv

    with pytest.raises(ValueError, match="no contiene datos"):
        split_csv(b"", {})
