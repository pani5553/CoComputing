"""
Consensus service: validates chunk results and triggers payment/trust updates.

Consensus rules (replicas_needed=2 by default):
  1 result   → pending, wait for second replica.
  2 results  → if equal: both valid, chunk=done.
               if different: chunk back to pending for a 3rd worker.
  3 results  → majority (2-of-3) wins; minority is invalid.
               if all 3 different → all invalid, chunk=rejected.

After a chunk reaches 'done', completed_chunks is incremented and, if
completed_chunks == total_chunks (all terminal), finalize_job is called.
"""
import json
import logging
from collections import Counter
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.db.queries import compute_queries
from app.db.queries.auth_queries import get_provider_by_id
from app.db.queries.profile_queries import update_provider
from app.models.compute import SubmitResponse
from app.services import trust_score, wallet_service

logger = logging.getLogger(__name__)

REWARD_PER_CHUNK = 0.10


def _canonical(result: Any) -> str:
    """Canonical JSON serialization for comparison (order-independent)."""
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            return result
    return json.dumps(result, sort_keys=True)


def _pay_and_update_trust(provider_id: str, chunk_id: str, valid: bool) -> None:
    """Pay (if valid) and update accuracy for one provider result."""
    try:
        if valid:
            wallet_service.credit_reward(
                provider_id=str(provider_id),
                amount=REWARD_PER_CHUNK,
                description=f"Recompensa por chunk validado: {chunk_id}",
            )
        provider = get_provider_by_id(str(provider_id))
        if provider is None:
            logger.warning("Provider %s not found for trust update", provider_id)
            return

        current_accuracy = float(provider.get("accuracy", 80.0))
        if valid:
            new_accuracy = trust_score.update_accuracy_on_complete(current_accuracy)
        else:
            new_accuracy = trust_score.update_accuracy_on_fail(current_accuracy)

        new_ts = trust_score.calculate_trust_score(
            completion_rate=float(provider.get("completion_rate", 0.0)),
            accuracy=new_accuracy,
            response_time_score=float(provider.get("response_time_score", 70.0)),
            client_rating=float(provider.get("client_rating", 70.0)),
        )
        new_rank = trust_score.get_rank(new_ts)
        update_provider(
            str(provider_id),
            {
                "accuracy": new_accuracy,
                "trust_score": new_ts,
                "rank": new_rank,
            },
        )
    except Exception as exc:
        logger.error(
            "Error en pago/trust para proveedor %s chunk %s: %s",
            provider_id,
            chunk_id,
            exc,
            exc_info=True,
        )


def _try_close_job(job_id: str) -> None:
    """
    Check if all chunks in the job are in a terminal state (done/rejected).
    If so, call finalize_job.
    """
    try:
        from app.services import compute_service  # local import to avoid circular dep

        counts = compute_queries.count_done_and_rejected_chunks(job_id)
        terminal = counts["done"] + counts["rejected"]
        total = counts["total"]

        if total == 0 or terminal < total:
            return

        job = compute_queries.get_job(job_id)
        if job is None or job["status"] in ("completed", "failed"):
            return

        # If more than half of chunks are rejected, mark job as failed
        if counts["rejected"] > total * 0.5:
            from datetime import datetime, timezone
            compute_queries.update_job_status(
                job_id,
                "failed",
                completed_at=datetime.now(timezone.utc),
            )
            logger.info("Job %s marcado como failed (demasiados chunks rechazados)", job_id)
        else:
            compute_service.finalize_job(job_id)

    except Exception as exc:
        logger.error("Error en _try_close_job %s: %s", job_id, exc, exc_info=True)


def process_chunk_submission(
    chunk_id: str,
    provider_id: str,
    result: dict[str, Any],
    duration_ms: int,
) -> SubmitResponse:
    """
    Main entry point called by POST /work/{chunk_id}/submit.
    Persists result, evaluates consensus, triggers side-effects.
    """
    # Validate chunk existence and assignment
    try:
        chunk = compute_queries.get_chunk(chunk_id)
    except Exception as exc:
        logger.error("Error obteniendo chunk %s: %s", chunk_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )

    if chunk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk no encontrado",
        )

    # Check that this provider has the chunk assigned (assigned_to matches or it
    # was previously assigned — for the 3rd-replica case, assigned_to may be null
    # when the chunk was reset to pending). We verify via chunk_results instead.
    existing_results = compute_queries.get_chunk_results(chunk_id)
    already_submitted = any(
        str(r["provider_id"]) == str(provider_id) for r in existing_results
    )
    if already_submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya has entregado un resultado para este chunk",
        )

    # The chunk must be 'assigned' and the provider must be the assignee
    if chunk["status"] != "assigned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tienes este chunk asignado",
        )
    if str(chunk.get("assigned_to")) != str(provider_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tienes este chunk asignado",
        )

    # Persist the result
    try:
        cr_row = compute_queries.submit_chunk_result(
            chunk_id=chunk_id,
            provider_id=provider_id,
            result=result,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        logger.error("Error guardando chunk_result: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )

    chunk_result_id = cr_row["id"]
    job_id = str(chunk["job_id"])
    replicas_needed = int(chunk.get("replicas_needed") or 2)

    # Reload all results (including the one just inserted)
    all_results = compute_queries.get_chunk_results(chunk_id)
    n_results = len(all_results)

    if n_results < replicas_needed:
        # Reset chunk to pending so a second worker can claim it (R2-A-06)
        compute_queries.update_chunk_status(chunk_id, "pending")
        return SubmitResponse(
            chunk_result_id=chunk_result_id,
            chunk_id=chunk_id,
            status="assigned",
            message="Resultado recibido. Esperando segunda réplica para validar.",
        )

    canonicals = [_canonical(r["result"]) for r in all_results]

    if n_results == 2:
        if canonicals[0] == canonicals[1]:
            # Consensus achieved
            for r in all_results:
                compute_queries.validate_chunk_result(r["id"], True)
            compute_queries.update_chunk_status(chunk_id, "done")
            updated_job = compute_queries.increment_job_completed_chunks(job_id)

            for r in all_results:
                _pay_and_update_trust(str(r["provider_id"]), chunk_id, valid=True)

            _try_close_job(job_id)

            return SubmitResponse(
                chunk_result_id=chunk_result_id,
                chunk_id=chunk_id,
                status="done",
                message="Chunk validado. Recompensa acreditada.",
            )
        else:
            # Disagreement — return to queue for a 3rd worker
            compute_queries.update_chunk_status(chunk_id, "pending")
            return SubmitResponse(
                chunk_result_id=chunk_result_id,
                chunk_id=chunk_id,
                status="assigned",
                message="Desacuerdo entre réplicas. Se asignará un tercer proveedor para desempate.",
            )

    # n_results >= 3 — tiebreaker round
    counter = Counter(canonicals)
    majority_canonical, majority_count = counter.most_common(1)[0]

    if majority_count >= 2:
        for r, canon in zip(all_results, canonicals):
            is_valid = canon == majority_canonical
            compute_queries.validate_chunk_result(r["id"], is_valid)

        compute_queries.update_chunk_status(chunk_id, "done")
        updated_job = compute_queries.increment_job_completed_chunks(job_id)

        for r, canon in zip(all_results, canonicals):
            _pay_and_update_trust(
                str(r["provider_id"]),
                chunk_id,
                valid=(canon == majority_canonical),
            )

        _try_close_job(job_id)

        return SubmitResponse(
            chunk_result_id=chunk_result_id,
            chunk_id=chunk_id,
            status="done",
            message="Chunk validado por mayoría. Recompensa acreditada.",
        )
    else:
        # All 3 different — reject
        for r in all_results:
            compute_queries.validate_chunk_result(r["id"], False)
        compute_queries.update_chunk_status(chunk_id, "rejected")

        for r in all_results:
            _pay_and_update_trust(str(r["provider_id"]), chunk_id, valid=False)

        _try_close_job(job_id)

        return SubmitResponse(
            chunk_result_id=chunk_result_id,
            chunk_id=chunk_id,
            status="rejected",
            message="Chunk rechazado: los tres resultados difieren entre sí.",
        )
