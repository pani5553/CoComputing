"""
Tests unitarios del servicio de consenso (consensus_service.py).

Criterios de aceptación validados (US-38, US-39, US-40):
- CA-2: 2 resultados iguales → ambos is_valid=True, chunk=done
- CA-2: 2 resultados distintos → chunk vuelve a pending (espera 3º proveedor)
- CA-4: 3 resultados con mayoría de 2 → los 2 iguales valid=True, el distinto valid=False
- CA-4: 3 resultados todos distintos → todos valid=False, chunk=rejected
- CA-5: cuando todos los chunks están done → job pasa a completed y
         wallet_service es invocado por cada result válido

Estrategia: se mockea compute_queries y las dependencias de side-effects
(wallet_service, trust_score, auth_queries, profile_queries) para que los tests
sean unitarios puros sin conexión a Supabase.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from tests.conftest import PROVIDER_ID

# ── IDs compartidos ────────────────────────────────────────────────────────────

JOB_ID = str(uuid.uuid4())
CHUNK_ID = str(uuid.uuid4())
PROVIDER_A = str(uuid.uuid4())
PROVIDER_B = str(uuid.uuid4())
PROVIDER_C = str(uuid.uuid4())

RESULT_A = {"col1_mean": 5.0}
RESULT_B = {"col1_mean": 5.0}   # igual a A
RESULT_C = {"col1_mean": 9.9}   # diferente


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_chunk(status: str = "assigned", provider_id: str = PROVIDER_A) -> dict:
    return {
        "id": CHUNK_ID,
        "job_id": JOB_ID,
        "status": status,
        "assigned_to": provider_id,
        "replicas_needed": 2,
        "chunk_index": 0,
        "attempts": 1,
    }


def _make_cr(cr_id: str, provider_id: str, result: dict, is_valid=None) -> dict:
    return {
        "id": cr_id,
        "chunk_id": CHUNK_ID,
        "provider_id": provider_id,
        "result": result,
        "duration_ms": 100,
        "is_valid": is_valid,
        "created_at": datetime(2026, 6, 5, 14, 0, 0, tzinfo=timezone.utc),
    }


def _make_provider(provider_id: str, accuracy: float = 80.0) -> dict:
    return {
        "id": provider_id,
        "accuracy": accuracy,
        "completion_rate": 80.0,
        "response_time_score": 70.0,
        "client_rating": 70.0,
        "trust_score": 75.0,
        "rank": "experto",
    }


def _run_consensus(chunk, existing_results, new_cr_row):
    """
    Ejecuta process_chunk_submission con los mocks apropiados.
    new_cr_row es lo que submit_chunk_result devuelve (el resultado recién insertado).
    all_results es la lista completa INCLUYENDO el recién insertado.
    """
    from app.services.consensus_service import process_chunk_submission

    with patch("app.services.consensus_service.compute_queries.get_chunk", return_value=chunk), \
         patch("app.services.consensus_service.compute_queries.get_chunk_results",
               side_effect=[existing_results, existing_results + [new_cr_row]]), \
         patch("app.services.consensus_service.compute_queries.submit_chunk_result",
               return_value=new_cr_row), \
         patch("app.services.consensus_service.compute_queries.validate_chunk_result") as mock_validate, \
         patch("app.services.consensus_service.compute_queries.update_chunk_status") as mock_update_chunk, \
         patch("app.services.consensus_service.compute_queries.increment_job_completed_chunks",
               return_value={"id": JOB_ID, "completed_chunks": 1, "total_chunks": 1, "status": "processing"}), \
         patch("app.services.consensus_service.compute_queries.count_done_and_rejected_chunks",
               return_value={"done": 1, "rejected": 0, "total": 1}), \
         patch("app.services.consensus_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing", "total_chunks": 1, "completed_chunks": 1}), \
         patch("app.services.consensus_service.get_provider_by_id",
               return_value=_make_provider(chunk["assigned_to"])), \
         patch("app.services.consensus_service.update_provider"), \
         patch("app.services.consensus_service.wallet_service.credit_reward") as mock_pay, \
         patch("app.services.compute_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing"}), \
         patch("app.services.compute_service.compute_queries.get_valid_results_for_job",
               return_value=[new_cr_row]), \
         patch("app.services.compute_service.compute_queries.update_job_status"):

        result = process_chunk_submission(
            chunk_id=CHUNK_ID,
            provider_id=chunk["assigned_to"],
            result=new_cr_row["result"],
            duration_ms=new_cr_row["duration_ms"],
        )

    return result, mock_validate, mock_update_chunk, mock_pay


# ══════════════════════════════════════════════════════════════════════════════
# Escenario 1: 2 resultados iguales — consenso logrado
# ══════════════════════════════════════════════════════════════════════════════

def test_consensus_two_equal_results_both_valid() -> None:
    """
    US-38 CA-2: Con 2 resultados idénticos ambos se marcan is_valid=True
    y el chunk pasa a estado 'done'.
    """
    from app.services.consensus_service import process_chunk_submission

    cr_id_a = str(uuid.uuid4())
    cr_id_b = str(uuid.uuid4())

    chunk = _make_chunk(status="assigned", provider_id=PROVIDER_B)
    existing_results = [_make_cr(cr_id_a, PROVIDER_A, RESULT_A)]
    new_cr = _make_cr(cr_id_b, PROVIDER_B, RESULT_B)
    all_results = existing_results + [new_cr]

    with patch("app.services.consensus_service.compute_queries.get_chunk", return_value=chunk), \
         patch("app.services.consensus_service.compute_queries.get_chunk_results",
               side_effect=[existing_results, all_results]), \
         patch("app.services.consensus_service.compute_queries.submit_chunk_result", return_value=new_cr), \
         patch("app.services.consensus_service.compute_queries.validate_chunk_result") as mock_validate, \
         patch("app.services.consensus_service.compute_queries.update_chunk_status") as mock_update_chunk, \
         patch("app.services.consensus_service.compute_queries.increment_job_completed_chunks",
               return_value={"id": JOB_ID, "completed_chunks": 1, "total_chunks": 1}), \
         patch("app.services.consensus_service.compute_queries.count_done_and_rejected_chunks",
               return_value={"done": 1, "rejected": 0, "total": 1}), \
         patch("app.services.consensus_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing", "total_chunks": 1}), \
         patch("app.services.consensus_service.get_provider_by_id",
               return_value=_make_provider(PROVIDER_B)), \
         patch("app.services.consensus_service.update_provider"), \
         patch("app.services.consensus_service.wallet_service.credit_reward"), \
         patch("app.services.compute_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing"}), \
         patch("app.services.compute_service.compute_queries.get_valid_results_for_job",
               return_value=[new_cr]), \
         patch("app.services.compute_service.compute_queries.update_job_status"):

        response = process_chunk_submission(
            chunk_id=CHUNK_ID,
            provider_id=PROVIDER_B,
            result=RESULT_B,
            duration_ms=100,
        )

    # El chunk debe pasar a 'done'
    mock_update_chunk.assert_called_with(CHUNK_ID, "done")
    # Ambos resultados (cr_id_a y cr_id_b) deben marcarse como válidos
    validate_calls = [c.args for c in mock_validate.call_args_list]
    assert len(validate_calls) == 2
    assert all(is_valid is True for _, is_valid in validate_calls)
    # El response indica chunk done
    assert response.status is not None


# ══════════════════════════════════════════════════════════════════════════════
# Escenario 2: 2 resultados distintos — vuelve a pending
# ══════════════════════════════════════════════════════════════════════════════

def test_consensus_two_different_results_pending() -> None:
    """
    US-38 CA-2 (discrepancia): Con 2 resultados distintos el chunk
    vuelve a estado 'pending' para asignar un 3er proveedor.
    No se marcan resultados como válidos ni inválidos todavía.
    """
    from app.services.consensus_service import process_chunk_submission

    cr_id_a = str(uuid.uuid4())
    cr_id_c = str(uuid.uuid4())

    chunk = _make_chunk(status="assigned", provider_id=PROVIDER_C)
    existing_results = [_make_cr(cr_id_a, PROVIDER_A, RESULT_A)]
    new_cr = _make_cr(cr_id_c, PROVIDER_C, RESULT_C)
    all_results = existing_results + [new_cr]

    with patch("app.services.consensus_service.compute_queries.get_chunk", return_value=chunk), \
         patch("app.services.consensus_service.compute_queries.get_chunk_results",
               side_effect=[existing_results, all_results]), \
         patch("app.services.consensus_service.compute_queries.submit_chunk_result", return_value=new_cr), \
         patch("app.services.consensus_service.compute_queries.validate_chunk_result") as mock_validate, \
         patch("app.services.consensus_service.compute_queries.update_chunk_status") as mock_update_chunk:

        response = process_chunk_submission(
            chunk_id=CHUNK_ID,
            provider_id=PROVIDER_C,
            result=RESULT_C,
            duration_ms=100,
        )

    # El chunk debe volver a pending
    mock_update_chunk.assert_called_with(CHUNK_ID, "pending")
    # No se llama a validate_chunk_result
    mock_validate.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════════
# Escenario 3: 3 resultados con mayoría (2 de 3)
# ══════════════════════════════════════════════════════════════════════════════

def test_consensus_three_results_majority() -> None:
    """
    US-38 CA-4 (mayoría): Con 3 resultados donde 2 coinciden,
    los 2 iguales se marcan is_valid=True y el discordante is_valid=False.
    El chunk pasa a 'done'.
    """
    from app.services.consensus_service import process_chunk_submission

    cr_id_a = str(uuid.uuid4())
    cr_id_b = str(uuid.uuid4())
    cr_id_c = str(uuid.uuid4())

    chunk = _make_chunk(status="assigned", provider_id=PROVIDER_C)
    existing_results = [
        _make_cr(cr_id_a, PROVIDER_A, RESULT_A),  # {"col1_mean": 5.0}
        _make_cr(cr_id_b, PROVIDER_B, RESULT_B),  # {"col1_mean": 5.0} igual a A
    ]
    # El 3er resultado es diferente
    result_c_different = {"col1_mean": 99.0}
    new_cr = _make_cr(cr_id_c, PROVIDER_C, result_c_different)
    all_results = existing_results + [new_cr]

    with patch("app.services.consensus_service.compute_queries.get_chunk", return_value=chunk), \
         patch("app.services.consensus_service.compute_queries.get_chunk_results",
               side_effect=[existing_results, all_results]), \
         patch("app.services.consensus_service.compute_queries.submit_chunk_result", return_value=new_cr), \
         patch("app.services.consensus_service.compute_queries.validate_chunk_result") as mock_validate, \
         patch("app.services.consensus_service.compute_queries.update_chunk_status") as mock_update_chunk, \
         patch("app.services.consensus_service.compute_queries.increment_job_completed_chunks",
               return_value={"id": JOB_ID, "completed_chunks": 1, "total_chunks": 1}), \
         patch("app.services.consensus_service.compute_queries.count_done_and_rejected_chunks",
               return_value={"done": 1, "rejected": 0, "total": 1}), \
         patch("app.services.consensus_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing", "total_chunks": 1}), \
         patch("app.services.consensus_service.get_provider_by_id",
               return_value=_make_provider(PROVIDER_C)), \
         patch("app.services.consensus_service.update_provider"), \
         patch("app.services.consensus_service.wallet_service.credit_reward"), \
         patch("app.services.compute_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing"}), \
         patch("app.services.compute_service.compute_queries.get_valid_results_for_job",
               return_value=existing_results), \
         patch("app.services.compute_service.compute_queries.update_job_status"):

        response = process_chunk_submission(
            chunk_id=CHUNK_ID,
            provider_id=PROVIDER_C,
            result=result_c_different,
            duration_ms=100,
        )

    # Chunk debe pasar a 'done'
    mock_update_chunk.assert_called_with(CHUNK_ID, "done")

    # Debe haber 3 llamadas a validate_chunk_result
    assert mock_validate.call_count == 3

    # Extraer qué se validó como qué: (result_id, is_valid)
    validation_calls = {c.args[0]: c.args[1] for c in mock_validate.call_args_list}
    # Los 2 iguales (cr_id_a, cr_id_b) → True; el diferente (cr_id_c) → False
    assert validation_calls.get(cr_id_a) is True
    assert validation_calls.get(cr_id_b) is True
    assert validation_calls.get(cr_id_c) is False


# ══════════════════════════════════════════════════════════════════════════════
# Escenario 4: 3 resultados todos distintos — chunk rejected
# ══════════════════════════════════════════════════════════════════════════════

def test_consensus_three_results_no_majority() -> None:
    """
    US-38 CA-4 (sin mayoría): Con 3 resultados todos distintos,
    todos se marcan is_valid=False y el chunk pasa a estado 'rejected'.
    """
    from app.services.consensus_service import process_chunk_submission

    cr_id_a = str(uuid.uuid4())
    cr_id_b = str(uuid.uuid4())
    cr_id_c = str(uuid.uuid4())

    chunk = _make_chunk(status="assigned", provider_id=PROVIDER_C)
    result_x = {"col1_mean": 1.0}
    result_y = {"col1_mean": 2.0}
    result_z = {"col1_mean": 3.0}

    existing_results = [
        _make_cr(cr_id_a, PROVIDER_A, result_x),
        _make_cr(cr_id_b, PROVIDER_B, result_y),
    ]
    new_cr = _make_cr(cr_id_c, PROVIDER_C, result_z)
    all_results = existing_results + [new_cr]

    with patch("app.services.consensus_service.compute_queries.get_chunk", return_value=chunk), \
         patch("app.services.consensus_service.compute_queries.get_chunk_results",
               side_effect=[existing_results, all_results]), \
         patch("app.services.consensus_service.compute_queries.submit_chunk_result", return_value=new_cr), \
         patch("app.services.consensus_service.compute_queries.validate_chunk_result") as mock_validate, \
         patch("app.services.consensus_service.compute_queries.update_chunk_status") as mock_update_chunk, \
         patch("app.services.consensus_service.compute_queries.count_done_and_rejected_chunks",
               return_value={"done": 0, "rejected": 1, "total": 1}), \
         patch("app.services.consensus_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing", "total_chunks": 1}), \
         patch("app.services.consensus_service.compute_queries.update_job_status"), \
         patch("app.services.consensus_service.get_provider_by_id",
               return_value=_make_provider(PROVIDER_C)), \
         patch("app.services.consensus_service.update_provider"), \
         patch("app.services.consensus_service.wallet_service.credit_reward"):

        response = process_chunk_submission(
            chunk_id=CHUNK_ID,
            provider_id=PROVIDER_C,
            result=result_z,
            duration_ms=100,
        )

    # Chunk debe pasar a 'rejected'
    mock_update_chunk.assert_called_with(CHUNK_ID, "rejected")

    # Todos los resultados deben marcarse como inválidos
    assert mock_validate.call_count == 3
    validation_calls = {c.args[0]: c.args[1] for c in mock_validate.call_args_list}
    assert all(v is False for v in validation_calls.values())

    # El response indica rejected
    assert response.status == "rejected"


# ══════════════════════════════════════════════════════════════════════════════
# Escenario 5: todos los chunks done → job pasa a completed
# ══════════════════════════════════════════════════════════════════════════════

def test_job_closes_when_all_chunks_done() -> None:
    """
    US-38 CA-5/7 / US-39 CA-1/3: Cuando el último chunk de un job pasa a 'done',
    el servicio llama a finalize_job (que marca el job como 'completed')
    y credit_reward se invoca por cada chunk_result válido.
    """
    from app.services.consensus_service import process_chunk_submission

    cr_id_a = str(uuid.uuid4())
    cr_id_b = str(uuid.uuid4())

    chunk = _make_chunk(status="assigned", provider_id=PROVIDER_B)
    existing_results = [_make_cr(cr_id_a, PROVIDER_A, RESULT_A)]
    new_cr = _make_cr(cr_id_b, PROVIDER_B, RESULT_B)
    all_results = existing_results + [new_cr]

    # Simulamos que este es el último chunk (total=1, done=1 tras el submit)
    with patch("app.services.consensus_service.compute_queries.get_chunk", return_value=chunk), \
         patch("app.services.consensus_service.compute_queries.get_chunk_results",
               side_effect=[existing_results, all_results]), \
         patch("app.services.consensus_service.compute_queries.submit_chunk_result", return_value=new_cr), \
         patch("app.services.consensus_service.compute_queries.validate_chunk_result"), \
         patch("app.services.consensus_service.compute_queries.update_chunk_status"), \
         patch("app.services.consensus_service.compute_queries.increment_job_completed_chunks",
               return_value={"id": JOB_ID, "completed_chunks": 1, "total_chunks": 1}), \
         patch("app.services.consensus_service.compute_queries.count_done_and_rejected_chunks",
               return_value={"done": 1, "rejected": 0, "total": 1}), \
         patch("app.services.consensus_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing", "total_chunks": 1}), \
         patch("app.services.consensus_service.get_provider_by_id",
               return_value=_make_provider(PROVIDER_B)), \
         patch("app.services.consensus_service.update_provider"), \
         patch("app.services.consensus_service.wallet_service.credit_reward") as mock_pay, \
         patch("app.services.compute_service.compute_queries.get_job",
               return_value={"id": JOB_ID, "status": "processing", "total_chunks": 1}) as mock_finalize_get_job, \
         patch("app.services.compute_service.compute_queries.get_valid_results_for_job",
               return_value=all_results), \
         patch("app.services.compute_service.compute_queries.update_job_status") as mock_update_job_status:

        process_chunk_submission(
            chunk_id=CHUNK_ID,
            provider_id=PROVIDER_B,
            result=RESULT_B,
            duration_ms=100,
        )

    # wallet_service.credit_reward debe haberse invocado por los 2 resultados válidos
    assert mock_pay.call_count == 2

    # El job debe haber sido marcado como 'completed'
    completed_statuses = [c.args[1] for c in mock_update_job_status.call_args_list]
    assert "completed" in completed_statuses
