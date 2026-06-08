"""
Database queries for the client-side feature:
deposit, publish tasks, escrow management, task detail.
"""
from typing import Any

import psycopg2
import psycopg2.extras

from app.core.config import settings
from app.db.client import get_supabase


# ─── Deposit ──────────────────────────────────────────────────────────────────

def deposit_to_wallet(client_id: str, amount: float) -> dict[str, Any]:
    """
    Atomically add amount to available_balance and total_earned for the client.
    Returns the updated wallet row.
    """
    sql = """
        UPDATE wallets
        SET available_balance = available_balance + %s,
            total_earned      = total_earned      + %s
        WHERE provider_id = %s
        RETURNING *
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (round(amount, 2), round(amount, 2), client_id))
            row = cur.fetchone()
            conn.commit()
    if row is None:
        raise ValueError(f"No wallet found for client {client_id}")
    return dict(row)


# ─── Escrow / task creation ────────────────────────────────────────────────────

def hold_escrow(client_id: str, task_id: str, amount_per_slot: float, total_slots: int) -> dict[str, Any]:
    """
    Atomically deduct escrow from available_balance, add to pending_balance,
    and insert an escrow row. All in a single transaction.
    Returns the created escrow row.
    """
    total = round(amount_per_slot * total_slots, 2)
    sql_wallet = """
        UPDATE wallets
        SET available_balance = available_balance - %s,
            pending_balance   = pending_balance   + %s
        WHERE provider_id = %s
          AND available_balance >= %s
        RETURNING available_balance
    """
    sql_escrow = """
        INSERT INTO escrows
            (task_id, client_id, amount_per_slot, total_slots, amount_held, amount_released, status)
        VALUES (%s, %s, %s, %s, %s, 0.00, 'activo')
        RETURNING *
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_wallet, (total, total, client_id, total))
            if cur.fetchone() is None:
                conn.rollback()
                raise ValueError("insufficient_balance")
            cur.execute(sql_escrow, (task_id, client_id, round(amount_per_slot, 2), total_slots, total))
            escrow_row = cur.fetchone()
            conn.commit()
    return dict(escrow_row)


def get_escrow_by_task(task_id: str) -> dict[str, Any] | None:
    """Fetch the escrow row for a task. Returns None if not found."""
    response = (
        get_supabase().table("escrows")
        .select("*")
        .eq("task_id", task_id)
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def release_escrow_slot(task_id: str, client_id: str, amount: float) -> dict[str, Any]:
    """
    Release one slot from the escrow: increment amount_released, decrement
    client's pending_balance. Called when a provider completes the task.
    Returns the updated escrow row.
    """
    sql_escrow = """
        UPDATE escrows
        SET amount_released = amount_released + %s,
            status = CASE
                WHEN amount_released + %s >= amount_held THEN 'completado'
                ELSE status
            END
        WHERE task_id = %s
          AND status = 'activo'
        RETURNING *
    """
    sql_wallet = """
        UPDATE wallets
        SET pending_balance = pending_balance - %s
        WHERE provider_id = %s
          AND pending_balance >= %s
        RETURNING pending_balance
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_escrow, (round(amount, 2), round(amount, 2), task_id))
            escrow_row = cur.fetchone()
            if escrow_row is None:
                # Escrow not active (task from seed or already cancelled) — skip silently
                conn.rollback()
                return {}
            cur.execute(sql_wallet, (round(amount, 2), client_id, round(amount, 2)))
            conn.commit()
    return dict(escrow_row)


def refund_escrow(task_id: str, client_id: str) -> float:
    """
    Cancel the escrow and refund the unreleased amount back to available_balance.
    Returns the refunded amount.
    """
    sql_escrow = """
        UPDATE escrows
        SET status = 'cancelado'
        WHERE task_id = %s
          AND client_id = %s
          AND status = 'activo'
        RETURNING amount_held, amount_released
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_escrow, (task_id, client_id))
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                raise ValueError("escrow_not_active")
            refund = round(float(row["amount_held"]) - float(row["amount_released"]), 2)
            if refund > 0:
                sql_wallet = """
                    UPDATE wallets
                    SET available_balance = available_balance + %s,
                        pending_balance   = pending_balance   - %s
                    WHERE provider_id = %s
                """
                cur.execute(sql_wallet, (refund, refund, client_id))
            conn.commit()
    return refund


# ─── Task creation ────────────────────────────────────────────────────────────

def create_client_task(
    client_id: str,
    title: str,
    task_type: str,
    description: str,
    reward: float,
    difficulty: str,
    hardware_required: str,
    total_slots: int,
    duration_min: int,
    duration_max: int,
    stages: list[str],
    requester_name: str,
) -> dict[str, Any]:
    """Insert a new task row linked to the client. Returns the created task."""
    response = (
        get_supabase().table("tasks")
        .insert({
            "client_id": client_id,
            "title": title,
            "task_type": task_type,
            "description": description,
            "reward": round(reward, 2),
            "difficulty": difficulty,
            "hardware_required": hardware_required,
            "total_slots": total_slots,
            "slots_left": total_slots,
            "duration_min": duration_min,
            "duration_max": duration_max,
            "stages": stages,
            "requester_name": requester_name,
            "status": "disponible",
        })
        .execute()
    )
    return response.data[0]


# ─── Client task queries ──────────────────────────────────────────────────────

def get_client_tasks(client_id: str) -> list[dict[str, Any]]:
    """
    Fetch all tasks published by the client with escrow info and completed slot count.
    """
    sql = """
        SELECT
            t.id,
            t.title,
            t.task_type,
            t.reward,
            t.total_slots,
            t.slots_left,
            t.status,
            t.created_at,
            COALESCE(e.amount_held, 0)     AS escrow_held,
            COALESCE(e.amount_released, 0) AS escrow_released,
            COALESCE(
                (SELECT COUNT(*) FROM task_assignments ta
                 WHERE ta.task_id = t.id AND ta.status = 'completada'),
                0
            )::int AS slots_completed
        FROM tasks t
        LEFT JOIN escrows e ON e.task_id = t.id
        WHERE t.client_id = %s
        ORDER BY t.created_at DESC
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (client_id,))
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def get_client_task_detail(task_id: str, client_id: str) -> dict[str, Any] | None:
    """
    Fetch full task detail with assignments for the client owner.
    Returns None if task doesn't exist or doesn't belong to the client.
    """
    sql_task = """
        SELECT
            t.id,
            t.title,
            t.task_type,
            t.description,
            t.reward,
            t.difficulty,
            t.hardware_required,
            t.total_slots,
            t.slots_left,
            t.status,
            t.created_at,
            COALESCE(e.amount_held, 0)     AS escrow_held,
            COALESCE(e.amount_released, 0) AS escrow_released
        FROM tasks t
        LEFT JOIN escrows e ON e.task_id = t.id
        WHERE t.id = %s
          AND t.client_id = %s
        LIMIT 1
    """
    sql_assignments = """
        SELECT
            ta.id,
            ta.provider_id,
            p.full_name AS provider_name,
            ta.status,
            ta.reward_paid,
            ta.accepted_at,
            ta.completed_at
        FROM task_assignments ta
        JOIN providers p ON p.id = ta.provider_id
        WHERE ta.task_id = %s
        ORDER BY ta.accepted_at DESC
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_task, (task_id, client_id))
            task_row = cur.fetchone()
            if task_row is None:
                return None
            cur.execute(sql_assignments, (task_id,))
            assignments = cur.fetchall()

    result = dict(task_row)
    result["assignments"] = [dict(a) for a in assignments]
    return result


def cancel_task_db(task_id: str, client_id: str) -> dict[str, Any] | None:
    """
    Set task status to 'cancelada' if it belongs to client and is cancellable.
    Returns the updated task row, or None if not found/not allowed.
    """
    sql = """
        UPDATE tasks
        SET status = 'cancelada'
        WHERE id = %s
          AND client_id = %s
          AND status IN ('disponible', 'en_progreso')
        RETURNING *
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (task_id, client_id))
            row = cur.fetchone()
            conn.commit()
    if row is None:
        return None
    return dict(row)
