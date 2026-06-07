"""
Tests for consensus_service — chunk validation, payment and trust update logic.

All external calls (DB queries, wallet_service, trust_score updates) are mocked.
Test IDs: K-01 to K-07 (from docs/04-arquitectura.md §12.9)
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from tests.conftest import PROVIDER_ID

CHUNK_ID = str(uuid.uuid4())
JOB_ID = str(uuid.uuid4())
PROVIDER_A = str(uuid.uuid4())
PROVIDER_B = str(uuid.uuid4())
PROVIDER_C = str(uuid.uuid4())
NOW = datetime(2026, 6, 7, 10, 0, 0, tzinfo=timezone.utc)

RESULT_SAME = {"col1_mean": 1.5, "col2_mean": 3.0}
RESULT_DIFF_A = {"col1_mean": 1.5}
RESULT_DIFF_B = {"col1_mean": 2.0}
RESULT_DIFF_C = {"col1_mean": 3.0}


def _make_chunk(status="assigned", assigned_to=PROVIDER_A, replicas_needed=2):
    return {
        "id": CHUNK_ID,
        "job_id": JOB_ID,
        "chunk_index": 0,
        "status": status,
        "assigned_to": assigned_to,
        "replicas_needed": replicas_needed,
        "attempts": 1,
        "created_at": NOW,
        "payload": {"rows": [], "columns": []},
    }


def _make_chunk_result(result_id, provider_id, result, is_valid=None):
    return {
        "id": result_id,
        "chunk_id": CHUNK_ID,
        "provider_id": provider_id,
        "result": result,
        "duration_ms": 100,
        "is_valid": is_valid,
        "created_at": NOW,
    }


def _make_job(completed_chunks=0, total_chunks=1):
    return {
        "id": JOB_ID,
        "client_id": PROVIDER_ID,
        "job_type": "data-processing",
        "status": "processing",
        "params": {},
        "total_chunks": total_chunks,
        "completed_chunks": completed_chunks,
        "reward_total": 0.10,
        "result": None,
        "created_at": NOW,
        "completed_at": None,
    }


def _provider_dict(provider_id):
    return {
        "id": provider_id,
        "accuracy": 80.0,
        "completion_rate": 70.0,
        "response_time_score": 70.0,
        "client_rating": 70.0,
        "trust_score": 73.0,
        "rank": "confiable",
    }


# ── K-01: Two workers send same result → both valid, chunk=done ──────────────

@patch("app.services.consensus_service._try_close_job")
@patch("app.db.queries.profile_queries.update_provider")
@patch("app.db.queries.auth_queries.get_provider_by_id")
@patch("app.services.wallet_service.credit_reward")
@patch("app.db.queries.compute_queries.increment_job_completed_chunks")
@patch("app.db.queries.compute_queries.update_chunk_status")
@patch("app.db.queries.compute_queries.validate_chunk_result")
@patch("app.db.queries.compute_queries.get_chunk_results")
@patch("app.db.queries.compute_queries.submit_chunk_result")
@patch("app.db.queries.compute_queries.get_chunk")
def test_k01_two_same_results_both_valid_chunk_done(
    mock_get_chunk,
    mock_submit,
    mock_get_results,
    mock_validate,
    mock_update_chunk,
    mock_increment,
    mock_credit,
    mock_get_provider,
    mock_update_provider,
    mock_try_close,
):
    """K-01: Two workers send identical results → both is_valid=True, chunk=done."""
    cr_id = str(uuid.uuid4())
    mock_get_chunk.return_value = _make_chunk(assigned_to=PROVIDER_B)
    mock_submit.return_value = {"id": cr_id}
    cr_a = _make_chunk_result(str(uuid.uuid4()), PROVIDER_A, RESULT_SAME)
    cr_b = _make_chunk_result(cr_id, PROVIDER_B, RESULT_SAME)
    # First call: check already_submitted for PROVIDER_B → only A submitted so far
    # Second call: evaluate consensus → both A and B submitted
    mock_get_results.side_effect = [
        [cr_a],        # already_submitted check: B not yet in list
        [cr_a, cr_b],  # consensus evaluation after B's result is inserted
    ]

    mock_increment.return_value = _make_job(completed_chunks=1)
    mock_get_provider.return_value = _provider_dict(PROVIDER_B)

    from app.services.consensus_service import process_chunk_submission

    response = process_chunk_submission(
        chunk_id=CHUNK_ID,
        provider_id=PROVIDER_B,
        result=RESULT_SAME,
        duration_ms=100,
    )

    assert response.status == "done"
    mock_update_chunk.assert_called_once_with(CHUNK_ID, "done")
    assert mock_validate.call_count == 2
    # Both results marked valid
    for c in mock_validate.call_args_list:
        assert c.args[1] is True
    mock_credit.assert_called()
    mock_try_close.assert_called_once_with(JOB_ID)


# ── K-02: Two workers send different results → chunk back to pending ──────────

@patch("app.db.queries.compute_queries.update_chunk_status")
@patch("app.db.queries.compute_queries.get_chunk_results")
@patch("app.db.queries.compute_queries.submit_chunk_result")
@patch("app.db.queries.compute_queries.get_chunk")
def test_k02_two_different_results_chunk_back_to_pending(
    mock_get_chunk,
    mock_submit,
    mock_get_results,
    mock_update_chunk,
):
    """K-02: Two workers disagree → chunk status set back to pending."""
    cr_id = str(uuid.uuid4())
    mock_get_chunk.return_value = _make_chunk(assigned_to=PROVIDER_B)
    mock_submit.return_value = {"id": cr_id}
    cr_a = _make_chunk_result(str(uuid.uuid4()), PROVIDER_A, RESULT_DIFF_A)
    cr_b = _make_chunk_result(cr_id, PROVIDER_B, RESULT_DIFF_B)
    mock_get_results.side_effect = [
        [cr_a],        # already_submitted check: B not yet in list
        [cr_a, cr_b],  # consensus evaluation
    ]

    from app.services.consensus_service import process_chunk_submission

    response = process_chunk_submission(
        chunk_id=CHUNK_ID,
        provider_id=PROVIDER_B,
        result=RESULT_DIFF_B,
        duration_ms=100,
    )

    assert response.status == "assigned"
    assert "desacuerdo" in response.message.lower() or "Desacuerdo" in response.message
    mock_update_chunk.assert_called_once_with(CHUNK_ID, "pending")


# ── K-03: 3rd worker breaks tie with majority ────────────────────────────────

@patch("app.services.consensus_service._try_close_job")
@patch("app.db.queries.profile_queries.update_provider")
@patch("app.db.queries.auth_queries.get_provider_by_id")
@patch("app.services.wallet_service.credit_reward")
@patch("app.db.queries.compute_queries.increment_job_completed_chunks")
@patch("app.db.queries.compute_queries.update_chunk_status")
@patch("app.db.queries.compute_queries.validate_chunk_result")
@patch("app.db.queries.compute_queries.get_chunk_results")
@patch("app.db.queries.compute_queries.submit_chunk_result")
@patch("app.db.queries.compute_queries.get_chunk")
def test_k03_tiebreaker_majority_wins(
    mock_get_chunk,
    mock_submit,
    mock_get_results,
    mock_validate,
    mock_update_chunk,
    mock_increment,
    mock_credit,
    mock_get_provider,
    mock_update_provider,
    mock_try_close,
):
    """K-03: A and C agree, B disagrees → A and C valid, B invalid, chunk=done."""
    cr_id_c = str(uuid.uuid4())
    # Chunk assigned to C (3rd worker)
    mock_get_chunk.return_value = _make_chunk(assigned_to=PROVIDER_C)
    mock_submit.return_value = {"id": cr_id_c}

    # 3 results: A and C same, B different
    cr_a = _make_chunk_result(str(uuid.uuid4()), PROVIDER_A, RESULT_SAME)
    cr_b = _make_chunk_result(str(uuid.uuid4()), PROVIDER_B, RESULT_DIFF_B)
    cr_c = _make_chunk_result(cr_id_c, PROVIDER_C, RESULT_SAME)
    mock_get_results.side_effect = [
        [cr_a, cr_b],           # already_submitted check: C not yet in list
        [cr_a, cr_b, cr_c],     # consensus evaluation
    ]
    mock_increment.return_value = _make_job(completed_chunks=1)
    mock_get_provider.return_value = _provider_dict(PROVIDER_C)

    from app.services.consensus_service import process_chunk_submission

    response = process_chunk_submission(
        chunk_id=CHUNK_ID,
        provider_id=PROVIDER_C,
        result=RESULT_SAME,
        duration_ms=100,
    )

    assert response.status == "done"
    mock_update_chunk.assert_called_once_with(CHUNK_ID, "done")

    # A and C should be valid, B invalid
    validate_calls = {c.args[0]: c.args[1] for c in mock_validate.call_args_list}
    assert validate_calls[cr_a["id"]] is True
    assert validate_calls[cr_b["id"]] is False
    assert validate_calls[cr_c["id"]] is True


# ── K-04: All 3 results different → all invalid, chunk=rejected ──────────────

@patch("app.services.consensus_service._try_close_job")
@patch("app.db.queries.profile_queries.update_provider")
@patch("app.db.queries.auth_queries.get_provider_by_id")
@patch("app.services.wallet_service.credit_reward")
@patch("app.db.queries.compute_queries.update_chunk_status")
@patch("app.db.queries.compute_queries.validate_chunk_result")
@patch("app.db.queries.compute_queries.get_chunk_results")
@patch("app.db.queries.compute_queries.submit_chunk_result")
@patch("app.db.queries.compute_queries.get_chunk")
def test_k04_all_three_different_chunk_rejected(
    mock_get_chunk,
    mock_submit,
    mock_get_results,
    mock_validate,
    mock_update_chunk,
    mock_credit,
    mock_get_provider,
    mock_update_provider,
    mock_try_close,
):
    """K-04: All 3 results differ → all is_valid=False, chunk=rejected."""
    cr_id_c = str(uuid.uuid4())
    mock_get_chunk.return_value = _make_chunk(assigned_to=PROVIDER_C)
    mock_submit.return_value = {"id": cr_id_c}

    cr_a = _make_chunk_result(str(uuid.uuid4()), PROVIDER_A, RESULT_DIFF_A)
    cr_b = _make_chunk_result(str(uuid.uuid4()), PROVIDER_B, RESULT_DIFF_B)
    cr_c = _make_chunk_result(cr_id_c, PROVIDER_C, RESULT_DIFF_C)
    mock_get_results.side_effect = [
        [cr_a, cr_b],           # already_submitted check: C not yet in list
        [cr_a, cr_b, cr_c],     # consensus evaluation
    ]
    mock_get_provider.return_value = _provider_dict(PROVIDER_C)

    from app.services.consensus_service import process_chunk_submission

    response = process_chunk_submission(
        chunk_id=CHUNK_ID,
        provider_id=PROVIDER_C,
        result=RESULT_DIFF_C,
        duration_ms=100,
    )

    assert response.status == "rejected"
    mock_update_chunk.assert_called_once_with(CHUNK_ID, "rejected")
    # All 3 marked invalid
    for c in mock_validate.call_args_list:
        assert c.args[1] is False
    # No payment for invalid results
    mock_credit.assert_not_called()
    mock_try_close.assert_called_once_with(JOB_ID)


# ── K-05: Last chunk validated → finalize_job called ─────────────────────────

@patch("app.services.compute_service.finalize_job")
@patch("app.db.queries.compute_queries.count_done_and_rejected_chunks")
@patch("app.db.queries.compute_queries.get_job")
def test_k05_last_chunk_triggers_finalize_job(
    mock_get_job,
    mock_count,
    mock_finalize,
):
    """K-05: When all chunks terminal, _try_close_job calls finalize_job."""
    mock_get_job.return_value = _make_job(total_chunks=2, completed_chunks=2)
    mock_count.return_value = {"done": 2, "rejected": 0, "total": 2}

    from app.services.consensus_service import _try_close_job

    _try_close_job(JOB_ID)

    mock_finalize.assert_called_once_with(JOB_ID)


# ── K-06: Worker submits result for chunk not assigned to them → 400 ──────────

@patch("app.db.queries.compute_queries.get_chunk_results")
@patch("app.db.queries.compute_queries.get_chunk")
def test_k06_submit_not_assigned_chunk_returns_400(mock_get_chunk, mock_get_results):
    """K-06: chunk.assigned_to != provider_id → 400."""
    from fastapi import HTTPException

    mock_get_chunk.return_value = _make_chunk(assigned_to=PROVIDER_A)  # assigned to A, not B
    mock_get_results.return_value = []  # B has not submitted yet

    from app.services.consensus_service import process_chunk_submission

    with pytest.raises(HTTPException) as exc_info:
        process_chunk_submission(
            chunk_id=CHUNK_ID,
            provider_id=PROVIDER_B,  # B is not assignee
            result=RESULT_SAME,
            duration_ms=100,
        )
    assert exc_info.value.status_code == 400
    assert "chunk asignado" in exc_info.value.detail


# ── K-07: Worker submits duplicate result → 409 ───────────────────────────────

@patch("app.db.queries.compute_queries.get_chunk_results")
@patch("app.db.queries.compute_queries.get_chunk")
def test_k07_duplicate_submit_returns_409(mock_get_chunk, mock_get_results):
    """K-07: Provider already has a result for this chunk → 409 Conflict."""
    from fastapi import HTTPException

    mock_get_chunk.return_value = _make_chunk(assigned_to=PROVIDER_A)
    # Simulate that provider A already submitted
    mock_get_results.return_value = [
        _make_chunk_result(str(uuid.uuid4()), PROVIDER_A, RESULT_SAME)
    ]

    from app.services.consensus_service import process_chunk_submission

    with pytest.raises(HTTPException) as exc_info:
        process_chunk_submission(
            chunk_id=CHUNK_ID,
            provider_id=PROVIDER_A,
            result=RESULT_SAME,
            duration_ms=100,
        )
    assert exc_info.value.status_code == 409
    assert "Ya has entregado" in exc_info.value.detail


# ── Extra: Only 1 result delivered (< replicas_needed) → chunk reset to pending ──

@patch("app.db.queries.compute_queries.update_chunk_status")
@patch("app.db.queries.compute_queries.get_chunk_results")
@patch("app.db.queries.compute_queries.submit_chunk_result")
@patch("app.db.queries.compute_queries.get_chunk")
def test_first_result_resets_chunk_to_pending(
    mock_get_chunk, mock_submit, mock_get_results, mock_update_chunk
):
    """Single result for a chunk needing 2 replicas → chunk reset to pending for 2nd worker."""
    cr_id = str(uuid.uuid4())
    mock_get_chunk.return_value = _make_chunk(assigned_to=PROVIDER_A)
    mock_submit.return_value = {"id": cr_id}
    cr_a = _make_chunk_result(cr_id, PROVIDER_A, RESULT_SAME)
    mock_get_results.side_effect = [
        [],      # already_submitted check: A hasn't submitted yet
        [cr_a],  # after insert: 1 result, < replicas_needed (2)
    ]

    from app.services.consensus_service import process_chunk_submission

    response = process_chunk_submission(
        chunk_id=CHUNK_ID,
        provider_id=PROVIDER_A,
        result=RESULT_SAME,
        duration_ms=100,
    )

    assert response.status == "assigned"
    assert "réplica" in response.message or "Esperando" in response.message
    # Chunk must be reset to pending so a second worker can claim it (R2-A-06)
    mock_update_chunk.assert_called_once_with(CHUNK_ID, "pending")


# ── Extra: chunk not found → 404 ─────────────────────────────────────────────

@patch("app.db.queries.compute_queries.get_chunk")
def test_submit_chunk_not_found_returns_404(mock_get_chunk):
    from fastapi import HTTPException

    mock_get_chunk.return_value = None

    from app.services.consensus_service import process_chunk_submission

    with pytest.raises(HTTPException) as exc_info:
        process_chunk_submission(
            chunk_id=str(uuid.uuid4()),
            provider_id=PROVIDER_A,
            result={},
            duration_ms=100,
        )
    assert exc_info.value.status_code == 404
