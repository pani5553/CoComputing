"""
Compute service: job creation, splitting, status retrieval, and finalization.

Business rules:
- chunk_size = 500 rows
- reward = 0.10 CC per chunk
- progress = completed_chunks / total_chunks * 100
"""
import csv
import io
import json
import logging
from datetime import datetime, timezone
from math import ceil
from typing import Any

from fastapi import HTTPException, status

from app.db.queries import compute_queries
from app.models.compute import JobPublic

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
REWARD_PER_CHUNK = 0.10


def _job_to_public(job: dict[str, Any]) -> JobPublic:
    total = int(job.get("total_chunks") or 0)
    completed = int(job.get("completed_chunks") or 0)
    progress = round((completed / total) * 100.0, 1) if total > 0 else 0.0
    return JobPublic(
        id=job["id"],
        client_id=job["client_id"],
        job_type=job["job_type"],
        status=job["status"],
        params=job["params"] if isinstance(job["params"], dict) else {},
        total_chunks=total,
        completed_chunks=completed,
        reward_total=float(job.get("reward_total") or 0),
        result=job.get("result"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        progress=progress,
    )


def split_csv(csv_bytes: bytes, params: dict[str, Any], chunk_size: int = CHUNK_SIZE) -> list[dict[str, Any]]:
    """
    Pure function. Parse CSV bytes and return a list of chunk payloads.
    Each payload: {"rows": [[...]], "columns": [...], "operation": str, "target_columns": [...]}
    Raises ValueError if the CSV has no valid data.
    """
    text = csv_bytes.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    try:
        headers = next(reader)
    except StopIteration:
        raise ValueError("El archivo CSV no contiene datos válidos")

    headers = [h.strip() for h in headers]
    if not headers:
        raise ValueError("El archivo CSV no contiene datos válidos")

    all_rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not all_rows:
        raise ValueError("El archivo CSV no contiene datos válidos")

    operation = params.get("operation", "mean")
    target_columns = params.get("columns", headers)

    chunks = []
    for i in range(0, len(all_rows), chunk_size):
        batch = all_rows[i : i + chunk_size]
        chunks.append(
            {
                "rows": batch,
                "columns": headers,
                "operation": operation,
                "target_columns": target_columns,
            }
        )
    return chunks


def split_inline_data(
    data: list[list[Any]],
    columns: list[str],
    params: dict[str, Any],
    chunk_size: int = CHUNK_SIZE,
) -> list[dict[str, Any]]:
    """
    Pure function. Split inline row data (from params["data"]) into chunk payloads.
    """
    if not data or not columns:
        raise ValueError("El archivo CSV no contiene datos válidos")

    operation = params.get("operation", "mean")
    target_columns = params.get("columns", columns)

    chunks = []
    for i in range(0, len(data), chunk_size):
        batch = data[i : i + chunk_size]
        chunks.append(
            {
                "rows": batch,
                "columns": columns,
                "operation": operation,
                "target_columns": target_columns,
            }
        )
    return chunks


def create_job_with_chunks(
    client_id: str,
    job_type: str,
    params: dict[str, Any],
    csv_bytes: bytes | None = None,
) -> JobPublic:
    """
    Create a job, split into chunks, persist everything, and return the job.
    Accepts either a CSV file (csv_bytes) or inline data in params["data"].
    """
    if job_type != "data-processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de job no soportado: {job_type}",
        )

    try:
        if csv_bytes is not None:
            chunk_payloads = split_csv(csv_bytes, params)
        elif "data" in params:
            raw_data = params["data"]
            columns = params.get("columns")
            if not columns and raw_data:
                columns = [f"col{i}" for i in range(len(raw_data[0]))]
            chunk_payloads = split_inline_data(raw_data, columns or [], params)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo CSV no contiene datos válidos",
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    n_chunks = len(chunk_payloads)
    if n_chunks == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo CSV no contiene datos válidos",
        )

    reward_total = round(REWARD_PER_CHUNK * n_chunks, 2)

    # Strip "data" from params stored in the job (it can be large)
    stored_params = {k: v for k, v in params.items() if k != "data"}

    job_id: str | None = None
    try:
        job = compute_queries.create_job(
            client_id=client_id,
            job_type=job_type,
            params=stored_params,
            total_chunks=n_chunks,
            reward_total=reward_total,
        )
        job_id = str(job["id"])

        # Move to splitting immediately (synchronous — chunks created in same request)
        compute_queries.update_job_status(job_id, "splitting")

        compute_queries.create_chunks(job_id, chunk_payloads)

        updated_job = compute_queries.update_job_chunks_count(job_id, n_chunks)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error creando job: %s", exc, exc_info=True)
        # Cleanup: mark job as failed so it doesn't stay stuck in 'splitting' (R2-A-05)
        if job_id is not None:
            try:
                from datetime import datetime, timezone
                compute_queries.update_job_status(
                    job_id, "failed", completed_at=datetime.now(timezone.utc)
                )
            except Exception:
                pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )

    return _job_to_public(updated_job)


def get_jobs(client_id: str, status_filter: str | None = None) -> dict[str, Any]:
    """List all jobs for a client."""
    try:
        jobs = compute_queries.get_jobs_by_client(client_id, status_filter)
    except Exception as exc:
        logger.error("Error listando jobs: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )
    public_jobs = [_job_to_public(j) for j in jobs]
    return {"count": len(public_jobs), "jobs": public_jobs}


def get_job_status(job_id: str, client_id: str) -> JobPublic:
    """Fetch a job verifying ownership."""
    try:
        job = compute_queries.get_job(job_id)
    except Exception as exc:
        logger.error("Error obteniendo job %s: %s", job_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job no encontrado",
        )
    if str(job["client_id"]) != str(client_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para realizar esta acción",
        )
    return _job_to_public(job)


def get_job_result(job_id: str, client_id: str) -> dict[str, Any]:
    """Return the consolidated result. Only available when status=completed."""
    job_public = get_job_status(job_id, client_id)
    if job_public.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El job aún no ha sido completado (estado actual: {job_public.status})",
        )
    return {
        "id": str(job_public.id),
        "status": job_public.status,
        "result": job_public.result,
        "total_chunks": job_public.total_chunks,
        "completed_chunks": job_public.completed_chunks,
        "completed_at": job_public.completed_at,
    }


def finalize_job(job_id: str) -> None:
    """
    Consolidate valid chunk results into job.result, then mark job completed.
    Called by consensus_service when all chunks reach terminal status.
    """
    try:
        job = compute_queries.get_job(job_id)
        if job is None:
            logger.error("finalize_job: job %s not found", job_id)
            return

        valid_results = compute_queries.get_valid_results_for_job(job_id)

        # Reduce partial results: aggregate per column-operation key
        consolidated: dict[str, Any] = {}
        counts: dict[str, int] = {}
        for row in valid_results:
            r = row.get("result") or {}
            if isinstance(r, str):
                try:
                    r = json.loads(r)
                except Exception:
                    r = {}
            for key, val in r.items():
                if val is None:
                    continue
                try:
                    fval = float(val)
                except (TypeError, ValueError):
                    consolidated[key] = val
                    continue
                # Detect operation from key suffix
                key_lower = key.lower()
                if key_lower.endswith("_count"):
                    consolidated[key] = consolidated.get(key, 0) + fval
                elif key_lower.endswith("_sum"):
                    consolidated[key] = consolidated.get(key, 0) + fval
                elif key_lower.endswith("_min"):
                    existing = consolidated.get(key)
                    consolidated[key] = fval if existing is None else min(existing, fval)
                elif key_lower.endswith("_max"):
                    existing = consolidated.get(key)
                    consolidated[key] = existing if existing is not None and existing >= fval else fval
                else:
                    # mean: accumulate sum + count for final division
                    sum_key = f"__sum__{key}"
                    cnt_key = f"__cnt__{key}"
                    consolidated[sum_key] = consolidated.get(sum_key, 0.0) + fval
                    consolidated[cnt_key] = consolidated.get(cnt_key, 0) + 1

        # Finalize means
        final_result: dict[str, Any] = {}
        processed_mean_keys: set[str] = set()
        for key, val in consolidated.items():
            if key.startswith("__sum__"):
                original_key = key[len("__sum__"):]
                cnt = consolidated.get(f"__cnt__{original_key}", 1)
                final_result[original_key] = round(val / cnt, 6) if cnt else 0.0
                processed_mean_keys.add(original_key)
            elif key.startswith("__cnt__"):
                continue
            elif not key.startswith("__"):
                final_result[key] = val

        # Wrap in envelope for frontend consumption: {operation, columns: {col: val}}
        job_params = job.get("params") or {}
        operation_name = job_params.get("operation", "mean") if isinstance(job_params, dict) else "mean"
        result_envelope = {"operation": operation_name, "columns": final_result}

        compute_queries.update_job_status(
            job_id,
            "completed",
            result=result_envelope,
            completed_at=datetime.now(timezone.utc),
        )
        logger.info("Job %s finalizado con resultado: %s", job_id, final_result)

    except Exception as exc:
        logger.error("Error finalizando job %s: %s", job_id, exc, exc_info=True)
