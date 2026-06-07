"""
Router for /jobs — client-side compute API.
All endpoints require authentication.

POST /jobs accepts two content-types:
  - application/json:       {"job_type": "data-processing", "params": {...}}
  - multipart/form-data:    job_type (str), params (JSON str), file (UploadFile)

FastAPI does not allow mixing a Pydantic body model with Form fields in the same
function, so we use a single function that reads the raw request content-type and
dispatches accordingly.
"""
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.dependencies import get_current_provider
from app.models.compute import (
    JobCreateRequest,
    JobListResponse,
    JobPublic,
)
from app.services import compute_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["compute"])

MAX_CSV_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("", response_model=JobPublic, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: Request,
    provider: dict = Depends(get_current_provider),
) -> JobPublic:
    """
    Create a compute job.

    Variant A — application/json:
        {"job_type": "data-processing", "params": {"operation": "mean", "data": [[...]]}}

    Variant B — multipart/form-data:
        job_type: "data-processing"
        params:   '{"operation":"mean","columns":["col1"]}'
        file:     <csv file, max 10 MB>
    """
    client_id = str(provider["id"])
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        # Multipart path
        form = await request.form()
        job_type = form.get("job_type")
        params_raw = form.get("params")
        upload = form.get("file")

        if not job_type or not params_raw or not upload:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Se requieren job_type, params y file en multipart/form-data",
            )

        try:
            parsed_params: dict[str, Any] = json.loads(str(params_raw))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El campo params debe ser un JSON válido",
            )

        csv_bytes = await upload.read()
        if len(csv_bytes) > MAX_CSV_BYTES:
            raise HTTPException(
                status_code=413,
                detail="El archivo CSV no puede superar 10 MB",
            )
        if len(csv_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo CSV no contiene datos válidos",
            )

        return compute_service.create_job_with_chunks(
            client_id=client_id,
            job_type=str(job_type),
            params=parsed_params,
            csv_bytes=csv_bytes,
        )

    else:
        # JSON path
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El body debe ser JSON válido",
            )

        try:
            validated = JobCreateRequest(**body)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            )

        return compute_service.create_job_with_chunks(
            client_id=client_id,
            job_type=validated.job_type,
            params=validated.params,
            csv_bytes=None,
        )


@router.get("", response_model=JobListResponse)
def list_jobs(
    provider: dict = Depends(get_current_provider),
    status: str | None = None,
) -> JobListResponse:
    """List all jobs submitted by the authenticated provider (as client)."""
    result = compute_service.get_jobs(str(provider["id"]), status_filter=status)
    return JobListResponse(**result)


@router.get("/{job_id}/result")
def get_job_result(
    job_id: UUID,
    provider: dict = Depends(get_current_provider),
) -> dict:
    """Return the consolidated result of a completed job."""
    return compute_service.get_job_result(str(job_id), str(provider["id"]))


@router.get("/{job_id}", response_model=JobPublic)
def get_job(
    job_id: UUID,
    provider: dict = Depends(get_current_provider),
) -> JobPublic:
    """Return job detail with real-time progress."""
    return compute_service.get_job_status(str(job_id), str(provider["id"]))
