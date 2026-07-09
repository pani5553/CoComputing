"""
Router for /work — worker-side compute API.
All endpoints require authentication (the worker authenticates as a provider).
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.rate_limit import rate_limit_by_provider
from app.models.compute import ClaimRequest, ClaimResponse, SubmitRequest, SubmitResponse
from app.services import consensus_service
from app.models.compute import ChunkWithPayload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["work"])

# Instancias de dependencia expuestas a nivel de módulo (no inline en el
# decorador) para que los tests puedan sobreescribirlas vía
# app.dependency_overrides — ver tests/conftest.py y docs/04-arquitectura.md §15.8.
# Cada una ya incluye la autenticación (Depends(get_current_provider) por
# dentro) además del rate limit, así que sustituye por completo a la
# dependencia de autenticación que llevaban estos endpoints antes.
claim_rate_limiter = rate_limit_by_provider("work_claim", limit=30, window_seconds=60)
submit_rate_limiter = rate_limit_by_provider("work_submit", limit=60, window_seconds=60)


@router.post("/claim", response_model=ClaimResponse)
def claim_chunks(
    body: ClaimRequest,
    provider: dict = Depends(claim_rate_limiter),
) -> ClaimResponse:
    """
    Claim up to max_chunks pending chunks atomically.
    Returns an empty list when no chunks are available.
    """
    provider_id = str(provider["id"])
    rows = consensus_service.process_chunk_claim(provider_id, body.max_chunks)

    chunks = [
        ChunkWithPayload(
            chunk_id=row["chunk_id"],
            job_id=row["job_id"],
            chunk_index=row["chunk_index"],
            job_type=row.get("job_type", "data-processing"),
            payload=row["payload"] if isinstance(row["payload"], dict) else {},
        )
        for row in rows
    ]
    return ClaimResponse(chunks=chunks)


@router.post("/{chunk_id}/submit", response_model=SubmitResponse)
def submit_chunk(
    chunk_id: UUID,
    body: SubmitRequest,
    provider: dict = Depends(submit_rate_limiter),
) -> SubmitResponse:
    """
    Submit the result of a processed chunk.
    Triggers consensus evaluation and, if chunk is validated, payment + trust update.
    """
    return consensus_service.process_chunk_submission(
        chunk_id=str(chunk_id),
        provider_id=str(provider["id"]),
        result=body.result,
        duration_ms=body.duration_ms,
    )
