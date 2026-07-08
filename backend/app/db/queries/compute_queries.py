"""
Database queries for the compute pipeline: jobs, chunks, chunk_results.

Rules:
- Supabase SDK for standard CRUD.
- psycopg2 with FOR UPDATE SKIP LOCKED for claim_chunks_atomic.
- No string interpolation with user data.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras

from app.core.config import settings
from app.db.client import get_supabase

logger = logging.getLogger(__name__)

REWARD_PER_CHUNK = 0.10


# ── Jobs ──────────────────────────────────────────────────────────────────────

def create_job(
    client_id: str,
    job_type: str,
    params: dict[str, Any],
    total_chunks: int,
    reward_total: float,
) -> dict[str, Any]:
    """Insert a new job row and return the created record."""
    response = (
        get_supabase().table("jobs")
        .insert(
            {
                "client_id": client_id,
                "job_type": job_type,
                "status": "pending",
                "params": params,
                "total_chunks": total_chunks,
                "completed_chunks": 0,
                "reward_total": reward_total,
            }
        )
        .execute()
    )
    return response.data[0]


def get_jobs_by_client(
    client_id: str,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all jobs for a client, optionally filtered by status, newest first."""
    query = (
        get_supabase().table("jobs")
        .select("*")
        .eq("client_id", client_id)
        .order("created_at", desc=True)
    )
    if status_filter:
        query = query.eq("status", status_filter)
    response = query.execute()
    return response.data or []


def get_job(job_id: str) -> dict[str, Any] | None:
    """Fetch a job by UUID. Returns None if not found."""
    response = (
        get_supabase().table("jobs")
        .select("*")
        .eq("id", job_id)
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def update_job_status(
    job_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    completed_at: datetime | None = None,
) -> dict[str, Any]:
    """Update job status (and optionally result + completed_at). Returns updated row."""
    payload: dict[str, Any] = {"status": status}
    if result is not None:
        payload["result"] = result
    if completed_at is not None:
        payload["completed_at"] = completed_at.isoformat()
    response = (
        get_supabase().table("jobs")
        .update(payload)
        .eq("id", job_id)
        .execute()
    )
    return response.data[0]


def update_job_chunks_count(job_id: str, total_chunks: int) -> dict[str, Any]:
    """Set total_chunks and move status to 'processing'. Returns updated row."""
    response = (
        get_supabase().table("jobs")
        .update({"total_chunks": total_chunks, "status": "processing"})
        .eq("id", job_id)
        .execute()
    )
    return response.data[0]


def increment_job_completed_chunks(job_id: str) -> dict[str, Any]:
    """
    Atomically increment completed_chunks by 1 using psycopg2.
    The CHECK constraint (completed_chunks <= total_chunks) is enforced by the DB.
    Returns the updated job row.
    """
    sql = """
        UPDATE jobs
        SET completed_chunks = completed_chunks + 1
        WHERE id = %s
        RETURNING *
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (job_id,))
            row = cur.fetchone()
            conn.commit()
    if row is None:
        raise ValueError(f"Job {job_id} not found for increment")
    return dict(row)


# ── Chunks ────────────────────────────────────────────────────────────────────

def create_chunks(job_id: str, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Bulk-insert chunks for a job.
    payloads is an ordered list; chunk_index is derived from position.
    Returns the list of created chunk rows.
    """
    rows = [
        {
            "job_id": job_id,
            "chunk_index": idx,
            "payload": payload,
            "status": "pending",
            "attempts": 0,
            "replicas_needed": 2,
        }
        for idx, payload in enumerate(payloads)
    ]
    response = get_supabase().table("chunks").insert(rows).execute()
    return response.data or []


MAX_CHUNK_ATTEMPTS = 5
CHUNK_ASSIGNMENT_TTL_MINUTES = 10  # ver docs/04-arquitectura.md §14.2.1


def claim_chunks_atomic(provider_id: str, max_chunks: int) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Claim up to max_chunks pending chunks for provider_id in a single atomic
    transaction (one psycopg2 connection, one commit), running three
    sequential statements in order — see docs/04-arquitectura.md §14.2.4 for
    the full rationale (why these can't be fused into a single WITH):

      1. TTL reclaim: 'assigned' chunks whose assigned_at exceeded
         CHUNK_ASSIGNMENT_TTL_MINUTES go back to 'pending' (assigned_to and
         assigned_at cleared; attempts untouched — it was already counted
         when assigned). The provider that was assigned (assigned_to, before
         it is cleared) is appended to abandoned_by, unless already present
         (SEC-36 mitigation — see migrations/007_chunk_abandon_tracking.sql).
         Uses FOR UPDATE SKIP LOCKED (via a CTE) so this statement never
         blocks a concurrent worker on a row already being reclaimed by
         another connection.
      2. Attempts rejection (pre-existing logic, now reachable in practice
         once TTL reclaim is active): 'pending' chunks with
         attempts >= MAX_CHUNK_ATTEMPTS move to 'rejected'.
      3. The claim itself, excluding chunks with attempts >= MAX_CHUNK_ATTEMPTS
         and chunks the requesting provider previously abandoned (SEC-36),
         using FOR UPDATE SKIP LOCKED so concurrent workers never claim the
         same chunk, setting assigned_at = now().

    A chunk is eligible for claim only when the provider has not yet
    delivered a result for it AND has not previously abandoned it (left it
    to expire via TTL without submitting) — see SEC-36 in docs/06-security.md.
    The provider can still claim any other pending chunk normally.

    Returns (claimed_chunks, rejected_job_ids):
      - claimed_chunks: list of dicts with keys chunk_id, job_id, chunk_index,
        payload, replicas_needed, job_type.
      - rejected_job_ids: job_ids that had at least one chunk rejected for
        exceeding MAX_CHUNK_ATTEMPTS during this call, so the service layer
        can attempt to close them (see consensus_service.process_chunk_claim).
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            # 1. TTL RECLAIM — return expired 'assigned' chunks to 'pending',
            #    recording the abandoning provider in abandoned_by (SEC-36).
            cur.execute(
                """
                WITH expired AS (
                    SELECT id FROM chunks
                    WHERE status = 'assigned'
                      AND assigned_at < now() - make_interval(mins => %(ttl_minutes)s)
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE chunks
                SET status = 'pending',
                    assigned_to = NULL,
                    assigned_at = NULL,
                    abandoned_by = CASE
                        WHEN chunks.assigned_to = ANY(chunks.abandoned_by) THEN chunks.abandoned_by
                        ELSE chunks.abandoned_by || chunks.assigned_to
                    END
                FROM expired
                WHERE chunks.id = expired.id
                RETURNING chunks.id AS chunk_id, chunks.job_id AS job_id, chunks.attempts AS attempts
                """,
                {"ttl_minutes": CHUNK_ASSIGNMENT_TTL_MINUTES},
            )
            reclaimed = cur.fetchall()
            if reclaimed:
                logger.warning(
                    "TTL de asignación superado (%d min): %d chunk(s) devueltos a pending: %s",
                    CHUNK_ASSIGNMENT_TTL_MINUTES,
                    len(reclaimed),
                    [str(r["chunk_id"]) for r in reclaimed],
                )

            # 2. ATTEMPTS REJECTION — pre-existing logic, now reachable via TTL reclaim.
            cur.execute(
                """
                WITH overdue AS (
                    SELECT id FROM chunks
                    WHERE status = 'pending' AND attempts >= %(max_attempts)s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE chunks SET status = 'rejected'
                FROM overdue
                WHERE chunks.id = overdue.id
                RETURNING chunks.id AS chunk_id, chunks.job_id AS job_id
                """,
                {"max_attempts": MAX_CHUNK_ATTEMPTS},
            )
            rejected = cur.fetchall()

            # 3. CLAIM — existing logic, plus assigned_at = now().
            cur.execute(
                """
                WITH candidates AS (
                    SELECT c.id
                    FROM chunks c
                    WHERE c.status = 'pending'
                      AND c.attempts < %(max_attempts)s
                      AND NOT (%(provider_id)s = ANY(c.abandoned_by))
                      AND NOT EXISTS (
                          SELECT 1 FROM chunk_results cr
                          WHERE cr.chunk_id = c.id
                            AND cr.provider_id = %(provider_id)s
                      )
                    ORDER BY c.created_at ASC
                    LIMIT %(max_chunks)s
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE chunks
                SET status      = 'assigned',
                    assigned_to = %(provider_id)s,
                    assigned_at = now(),
                    attempts    = attempts + 1
                FROM candidates
                WHERE chunks.id = candidates.id
                RETURNING
                    chunks.id          AS chunk_id,
                    chunks.job_id,
                    chunks.chunk_index,
                    chunks.payload,
                    chunks.replicas_needed
                """,
                {
                    "provider_id": provider_id,
                    "max_chunks": max_chunks,
                    "max_attempts": MAX_CHUNK_ATTEMPTS,
                },
            )
            claimed = cur.fetchall()

            conn.commit()

    rejected_job_ids = list({str(r["job_id"]) for r in rejected})

    # Enrich each claimed chunk row with job_type from the jobs table via a
    # single query.
    if not claimed:
        return [], rejected_job_ids

    chunk_rows = [dict(r) for r in claimed]
    job_ids = list({r["job_id"] for r in chunk_rows})

    # Fetch job_types for all referenced jobs
    job_response = (
        get_supabase().table("jobs")
        .select("id, job_type")
        .in_("id", [str(j) for j in job_ids])
        .execute()
    )
    job_type_map = {row["id"]: row["job_type"] for row in (job_response.data or [])}

    for row in chunk_rows:
        row["job_type"] = job_type_map.get(str(row["job_id"]), "data-processing")

    return chunk_rows, rejected_job_ids


def get_chunk(chunk_id: str) -> dict[str, Any] | None:
    """Fetch a chunk by UUID. Returns None if not found."""
    response = (
        get_supabase().table("chunks")
        .select("*")
        .eq("id", chunk_id)
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def update_chunk_status(
    chunk_id: str,
    status: str,
    assigned_to: str | None = None,
) -> dict[str, Any]:
    """
    Update chunk status (and optionally assigned_to). Returns updated row.

    Invariant (docs/04-arquitectura.md §14.2.2): assigned_at is NOT NULL iff
    status == 'assigned'. assigned_at is only ever set to now() by
    claim_chunks_atomic's own claim statement — any transition made here to a
    status other than 'assigned' must clear it.
    """
    payload: dict[str, Any] = {"status": status}
    if assigned_to is not None:
        payload["assigned_to"] = assigned_to
    elif status == "pending":
        # Reset assigned_to to null when returning to queue
        payload["assigned_to"] = None
    if status != "assigned":
        payload["assigned_at"] = None
    response = (
        get_supabase().table("chunks")
        .update(payload)
        .eq("id", chunk_id)
        .execute()
    )
    return response.data[0]


def get_chunks_for_job(job_id: str) -> list[dict[str, Any]]:
    """Fetch all chunks for a job ordered by chunk_index."""
    response = (
        get_supabase().table("chunks")
        .select("*")
        .eq("job_id", job_id)
        .order("chunk_index")
        .execute()
    )
    return response.data or []


# ── Chunk Results ─────────────────────────────────────────────────────────────

def submit_chunk_result(
    chunk_id: str,
    provider_id: str,
    result: dict[str, Any],
    duration_ms: int,
) -> dict[str, Any]:
    """Insert a new chunk_result row (is_valid=null). Returns the created record."""
    response = (
        get_supabase().table("chunk_results")
        .insert(
            {
                "chunk_id": chunk_id,
                "provider_id": provider_id,
                "result": result,
                "duration_ms": duration_ms,
                "is_valid": None,
            }
        )
        .execute()
    )
    return response.data[0]


def get_chunk_results(chunk_id: str) -> list[dict[str, Any]]:
    """Fetch all results for a chunk ordered by created_at."""
    response = (
        get_supabase().table("chunk_results")
        .select("*")
        .eq("chunk_id", chunk_id)
        .order("created_at")
        .execute()
    )
    return response.data or []


def validate_chunk_result(result_id: str, is_valid: bool) -> dict[str, Any]:
    """Set is_valid on a chunk_result row. Returns the updated record."""
    response = (
        get_supabase().table("chunk_results")
        .update({"is_valid": is_valid})
        .eq("id", result_id)
        .execute()
    )
    return response.data[0]


def get_valid_results_for_job(job_id: str) -> list[dict[str, Any]]:
    """
    Fetch all chunk_results with is_valid=True for all chunks of a job.
    Uses psycopg2 for a JOIN query in one round-trip.
    """
    sql = """
        SELECT cr.id, cr.chunk_id, cr.provider_id, cr.result, cr.duration_ms,
               cr.is_valid, cr.created_at, c.chunk_index
        FROM chunk_results cr
        JOIN chunks c ON c.id = cr.chunk_id
        WHERE c.job_id = %s
          AND cr.is_valid = true
        ORDER BY c.chunk_index, cr.created_at
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (job_id,))
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def count_done_and_rejected_chunks(job_id: str) -> dict[str, int]:
    """
    Count chunks by terminal status for a job.
    Returns {"done": N, "rejected": M, "total": T}.
    """
    sql = """
        SELECT
            COUNT(*) FILTER (WHERE status = 'done')     AS done,
            COUNT(*) FILTER (WHERE status = 'rejected') AS rejected,
            COUNT(*)                                    AS total
        FROM chunks
        WHERE job_id = %s
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (job_id,))
            row = cur.fetchone()
    if row is None:
        return {"done": 0, "rejected": 0, "total": 0}
    return dict(row)
