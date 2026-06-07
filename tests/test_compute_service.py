"""
Tests unitarios de compute_service.py y del plugin DataProcessingPlugin.

Criterios de aceptación validados (US-31, US-33, US-35, US-38, US-40):
- Troceado correcto: 1100 filas → 3 chunks (500+500+100)
- Cálculo de recompensa: 3 chunks → 0.30 CC
- Cálculo de progreso: 3 total / 1 completado → 33.3%
- Autorización: proveedor B no puede acceder al job del proveedor A (HTTPException 403)
- Plugin DataProcessingPlugin.process: operaciones mean, sum, count, min, max

Estos tests son UNITARIOS PUROS: no usan TestClient ni conexión HTTP.
Las llamadas a compute_queries están mockeadas via patch.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException

from tests.conftest import PROVIDER_ID, NOW

# ── IDs compartidos ────────────────────────────────────────────────────────────

JOB_ID = str(uuid.uuid4())
OTHER_PROVIDER_ID = str(uuid.uuid4())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_job_row(
    *,
    status: str = "processing",
    total_chunks: int = 3,
    completed_chunks: int = 0,
    client_id: str = PROVIDER_ID,
    result: dict | None = None,
) -> dict:
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
        "completed_at": None,
    }


def _make_csv_bytes(n_rows: int) -> bytes:
    """Genera un CSV con n_rows filas de datos más la cabecera."""
    lines = ["col1,col2"]
    for i in range(n_rows):
        lines.append(f"{i},{i * 2}")
    return "\n".join(lines).encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# Troceado del CSV — split_csv
# ══════════════════════════════════════════════════════════════════════════════

def test_create_job_splits_correctly() -> None:
    """
    US-31 CA-7 / US-40 CA-1:
    Un CSV de 1100 filas con chunk_size=500 genera 3 chunks (500+500+100).
    Verifica la lógica pura de split_csv, sin llamadas a BD.
    """
    from app.services.compute_service import split_csv

    csv_bytes = _make_csv_bytes(1100)
    params = {"operation": "mean", "columns": ["col1"]}
    chunks = split_csv(csv_bytes, params)

    assert len(chunks) == 3
    assert len(chunks[0]["rows"]) == 500
    assert len(chunks[1]["rows"]) == 500
    assert len(chunks[2]["rows"]) == 100


def test_split_csv_single_chunk() -> None:
    """
    Un CSV de 300 filas (< 500) genera exactamente 1 chunk con las 300 filas.
    """
    from app.services.compute_service import split_csv

    csv_bytes = _make_csv_bytes(300)
    params = {"operation": "sum", "columns": ["col1"]}
    chunks = split_csv(csv_bytes, params)

    assert len(chunks) == 1
    assert len(chunks[0]["rows"]) == 300


def test_split_csv_exact_multiple() -> None:
    """
    Un CSV de exactamente 1000 filas genera 2 chunks de 500 cada uno.
    """
    from app.services.compute_service import split_csv

    csv_bytes = _make_csv_bytes(1000)
    params = {"operation": "mean", "columns": ["col1"]}
    chunks = split_csv(csv_bytes, params)

    assert len(chunks) == 2
    assert len(chunks[0]["rows"]) == 500
    assert len(chunks[1]["rows"]) == 500


def test_split_csv_preserves_operation_in_payload() -> None:
    """
    El payload de cada chunk contiene la operación y los target_columns del params.
    """
    from app.services.compute_service import split_csv

    csv_bytes = _make_csv_bytes(10)
    params = {"operation": "sum", "columns": ["col1"]}
    chunks = split_csv(csv_bytes, params)

    for chunk in chunks:
        assert chunk["operation"] == "sum"
        assert "col1" in chunk["target_columns"]


def test_split_csv_empty_raises_value_error() -> None:
    """
    Un CSV vacío o sin filas de datos lanza ValueError.
    """
    from app.services.compute_service import split_csv

    empty_csv = b"col1,col2\n"  # solo cabecera, sin filas
    params = {"operation": "mean"}
    with pytest.raises(ValueError):
        split_csv(empty_csv, params)


# ══════════════════════════════════════════════════════════════════════════════
# Cálculo de recompensa
# ══════════════════════════════════════════════════════════════════════════════

def test_create_job_calculates_reward() -> None:
    """
    US-31 CA-8: Con 3 chunks y REWARD_PER_CHUNK=0.10, reward_total debe ser 0.30 CC.
    Verifica que compute_queries.create_job se invoca con reward_total correcto.
    """
    from app.services.compute_service import create_job_with_chunks

    n_rows = 1100  # → 3 chunks (500+500+100)
    csv_bytes = _make_csv_bytes(n_rows)
    params = {"operation": "mean", "columns": ["col1"]}

    job_row = _make_job_row(total_chunks=3, completed_chunks=0)

    with patch("app.services.compute_service.compute_queries.create_job",
               return_value=job_row) as mock_create, \
         patch("app.services.compute_service.compute_queries.update_job_status",
               return_value=job_row), \
         patch("app.services.compute_service.compute_queries.create_chunks",
               return_value=[{}, {}, {}]), \
         patch("app.services.compute_service.compute_queries.update_job_chunks_count",
               return_value=job_row):

        result = create_job_with_chunks(
            client_id=PROVIDER_ID,
            job_type="data-processing",
            params=params,
            csv_bytes=csv_bytes,
        )

    # Verificar que create_job fue llamado con reward_total=0.30
    call_kwargs = mock_create.call_args
    reward = call_kwargs.kwargs.get("reward_total") or call_kwargs.args[4]
    assert abs(reward - 0.30) < 0.001


# ══════════════════════════════════════════════════════════════════════════════
# Cálculo de progreso — get_job_status
# ══════════════════════════════════════════════════════════════════════════════

def test_get_job_calculates_progress() -> None:
    """
    US-33 CA-2: Job con 3 total_chunks y 1 completed_chunks
    → progress = 33.3% (redondeado a 1 decimal).
    """
    from app.services.compute_service import get_job_status

    job_row = _make_job_row(total_chunks=3, completed_chunks=1)
    with patch("app.services.compute_service.compute_queries.get_job", return_value=job_row):
        job_public = get_job_status(JOB_ID, PROVIDER_ID)

    assert abs(job_public.progress - 33.3) < 0.1


def test_get_job_progress_zero_when_no_completed() -> None:
    """
    Job con 0 chunks completados tiene progress = 0.0.
    """
    from app.services.compute_service import get_job_status

    job_row = _make_job_row(total_chunks=5, completed_chunks=0)
    with patch("app.services.compute_service.compute_queries.get_job", return_value=job_row):
        job_public = get_job_status(JOB_ID, PROVIDER_ID)

    assert job_public.progress == 0.0


def test_get_job_progress_100_when_all_completed() -> None:
    """
    Job con todos los chunks completados tiene progress = 100.0.
    """
    from app.services.compute_service import get_job_status

    job_row = _make_job_row(total_chunks=4, completed_chunks=4)
    with patch("app.services.compute_service.compute_queries.get_job", return_value=job_row):
        job_public = get_job_status(JOB_ID, PROVIDER_ID)

    assert job_public.progress == 100.0


# ══════════════════════════════════════════════════════════════════════════════
# Autorización — get_job_status
# ══════════════════════════════════════════════════════════════════════════════

def test_get_job_unauthorized() -> None:
    """
    US-33 CA-6: Un proveedor B que intenta acceder al job del proveedor A
    recibe HTTPException con status_code 403.
    """
    from app.services.compute_service import get_job_status

    job_row = _make_job_row(client_id=PROVIDER_ID)  # job es del PROVIDER_ID

    with patch("app.services.compute_service.compute_queries.get_job", return_value=job_row):
        with pytest.raises(HTTPException) as exc_info:
            get_job_status(JOB_ID, OTHER_PROVIDER_ID)  # intenta acceder con otro ID

    assert exc_info.value.status_code == 403


def test_get_job_not_found_raises_404() -> None:
    """
    US-33 CA-7: Job inexistente lanza HTTPException 404.
    """
    from app.services.compute_service import get_job_status

    with patch("app.services.compute_service.compute_queries.get_job", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            get_job_status(str(uuid.uuid4()), PROVIDER_ID)

    assert exc_info.value.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Plugin DataProcessingPlugin — cómputo real
# ══════════════════════════════════════════════════════════════════════════════

def _make_payload(operation: str, rows: list | None = None) -> dict:
    """Genera un payload de chunk con los datos de prueba."""
    if rows is None:
        rows = [["1", "10"], ["2", "20"], ["3", "30"]]
    return {
        "rows": rows,
        "columns": ["col1", "col2"],
        "operation": operation,
        "target_columns": ["col1", "col2"],
    }


def test_data_processing_plugin_mean() -> None:
    """
    US-35 CA-4 / US-40 CA-6:
    DataProcessingPlugin.process con operation=mean calcula la media correcta.
    col1: [1, 2, 3] → mean = 2.0
    col2: [10, 20, 30] → mean = 20.0
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = _make_payload("mean")
    result = plugin.process(payload)

    assert "col1_mean" in result
    assert "col2_mean" in result
    assert abs(result["col1_mean"] - 2.0) < 0.001
    assert abs(result["col2_mean"] - 20.0) < 0.001


def test_data_processing_plugin_sum() -> None:
    """
    US-35 CA-4: operation=sum calcula la suma correcta.
    col1: [1, 2, 3] → sum = 6.0
    col2: [10, 20, 30] → sum = 60.0
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = _make_payload("sum")
    result = plugin.process(payload)

    assert "col1_sum" in result
    assert "col2_sum" in result
    assert abs(result["col1_sum"] - 6.0) < 0.001
    assert abs(result["col2_sum"] - 60.0) < 0.001


def test_data_processing_plugin_count() -> None:
    """
    US-35 CA-4: operation=count devuelve el número de filas válidas.
    3 filas → count = 3.0
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = _make_payload("count")
    result = plugin.process(payload)

    assert "col1_count" in result
    assert "col2_count" in result
    assert result["col1_count"] == 3.0
    assert result["col2_count"] == 3.0


def test_data_processing_plugin_min() -> None:
    """
    US-35 CA-4: operation=min devuelve el valor mínimo.
    col1: [1, 2, 3] → min = 1.0
    col2: [10, 20, 30] → min = 10.0
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = _make_payload("min")
    result = plugin.process(payload)

    assert "col1_min" in result
    assert "col2_min" in result
    assert abs(result["col1_min"] - 1.0) < 0.001
    assert abs(result["col2_min"] - 10.0) < 0.001


def test_data_processing_plugin_max() -> None:
    """
    US-35 CA-4: operation=max devuelve el valor máximo.
    col1: [1, 2, 3] → max = 3.0
    col2: [10, 20, 30] → max = 30.0
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = _make_payload("max")
    result = plugin.process(payload)

    assert "col1_max" in result
    assert "col2_max" in result
    assert abs(result["col1_max"] - 3.0) < 0.001
    assert abs(result["col2_max"] - 30.0) < 0.001


def test_data_processing_plugin_single_target_column() -> None:
    """
    Cuando target_columns contiene solo una columna, solo aparece esa en el resultado.
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = {
        "rows": [["1", "10"], ["2", "20"], ["3", "30"]],
        "columns": ["col1", "col2"],
        "operation": "sum",
        "target_columns": ["col1"],  # solo col1
    }
    result = plugin.process(payload)

    assert "col1_sum" in result
    assert "col2_sum" not in result


def test_data_processing_plugin_empty_rows_returns_empty() -> None:
    """
    Un payload con rows vacías devuelve un dict vacío (sin lanzar excepción).
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = {
        "rows": [],
        "columns": ["col1"],
        "operation": "mean",
        "target_columns": ["col1"],
    }
    result = plugin.process(payload)

    assert result == {}


def test_data_processing_plugin_result_key_format() -> None:
    """
    Las claves del resultado siguen el formato '{col}_{operation}'.
    No hay claves con prefijos internos como '__sum__' o '__cnt__'.
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = _make_payload("mean")
    result = plugin.process(payload)

    for key in result.keys():
        assert not key.startswith("__"), f"Clave interna expuesta: {key}"


def test_data_processing_plugin_mean_with_floats() -> None:
    """
    El plugin maneja valores float como strings (formato CSV típico).
    col1: [1.5, 2.5, 3.0] → mean = 2.333...
    """
    from app.worker.plugins.data_processing import DataProcessingPlugin

    plugin = DataProcessingPlugin()
    payload = {
        "rows": [["1.5"], ["2.5"], ["3.0"]],
        "columns": ["col1"],
        "operation": "mean",
        "target_columns": ["col1"],
    }
    result = plugin.process(payload)

    assert "col1_mean" in result
    expected_mean = (1.5 + 2.5 + 3.0) / 3
    assert abs(result["col1_mean"] - expected_mean) < 0.001
