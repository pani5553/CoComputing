"""
Router for /work — worker-side compute API.
All endpoints require authentication (the worker authenticates as a provider).
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_current_provider
from app.models.compute import ClaimRequest, ClaimResponse, SubmitRequest, SubmitResponse
from app.services import consensus_service
from app.models.compute import ChunkWithPayload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["work"])


@router.post("/claim", response_model=ClaimResponse)
def claim_chunks(
    body: ClaimRequest,
    provider: dict = Depends(get_current_provider),
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
    provider: dict = Depends(get_current_provider),
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
