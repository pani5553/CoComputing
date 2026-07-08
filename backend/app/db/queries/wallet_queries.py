"""
Database queries for wallets and transactions.
"""
from typing import Any

import psycopg2
import psycopg2.extras

from app.core.config import settings
from app.db.client import get_supabase

# NOTA — excepción de capas deliberada (docs/04-arquitectura.md §14.3.1):
# esta es la única función de app/db/queries/*.py que importa de
# app/services/*. Se justifica porque trust_score es lógica pura (sin I/O,
# sin dependencias de framework, no importa de app.db.queries — cero riesgo
# de import circular) y necesita ejecutarse MIENTRAS el provider sigue
# bloqueado (FOR UPDATE) en la misma transacción; calcularlo fuera reabriría
# la ventana de carrera que credit_reward_and_update_trust existe para
# cerrar. No generalizar este patrón sin el mismo análisis.
from app.services import trust_score


def get_wallet_by_provider_id(provider_id: str) -> dict[str, Any] | None:
    """Fetch the wallet for a provider. Returns None if not found."""
    response = (
        get_supabase().table("wallets")
        .select("*")
        .eq("provider_id", provider_id)
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def get_transactions(
    provider_id: str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """
    Fetch paginated transactions for a provider ordered by created_at DESC.
    Returns (rows, total_count).
    """
    # Get total count
    count_response = (
        get_supabase().table("transactions")
        .select("id", count="exact")
        .eq("provider_id", provider_id)
        .execute()
    )
    total: int = count_response.count or 0

    # Get paginated rows
    rows_response = (
        get_supabase().table("transactions")
        .select("*")
        .eq("provider_id", provider_id)
        .order("created_at", desc=True)
        .limit(limit)
        .offset(offset)
        .execute()
    )
    return rows_response.data or [], total


def create_transaction(
    provider_id: str,
    amount: float,
    tx_type: str,
    description: str,
    status: str = "completada",
    task_id: str | None = None,
    withdraw_method: str | None = None,
    withdraw_destination: str | None = None,
) -> dict[str, Any]:
    """Insert a new transaction row."""
    payload: dict[str, Any] = {
        "provider_id": provider_id,
        "amount": amount,
        "tx_type": tx_type,
        "description": description,
        "status": status,
    }
    if task_id is not None:
        payload["task_id"] = task_id
    if withdraw_method is not None:
        payload["withdraw_method"] = withdraw_method
    if withdraw_destination is not None:
        payload["withdraw_destination"] = withdraw_destination

    response = get_supabase().table("transactions").insert(payload).execute()
    return response.data[0]


def update_wallet_on_task_complete(
    provider_id: str,
    reward: float,
) -> dict[str, Any]:
    """
    Atomically increment available_balance and total_earned by reward using psycopg2.
    Avoids the read-modify-write race condition present in the SDK-based approach.
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
            cur.execute(sql, (round(reward, 2), round(reward, 2), provider_id))
            row = cur.fetchone()
            conn.commit()
    if row is None:
        raise ValueError(f"No wallet found for provider {provider_id}")
    return dict(row)


def update_wallet_on_withdraw(
    provider_id: str,
    amount: float,
) -> dict[str, Any]:
    """
    Decrement available_balance and increment total_withdrawn by amount.
    Returns the updated wallet row.
    """
    wallet = get_wallet_by_provider_id(provider_id)
    if wallet is None:
        raise ValueError(f"No wallet found for provider {provider_id}")

    new_available = float(wallet["available_balance"]) - amount
    new_total_withdrawn = float(wallet["total_withdrawn"]) + amount

    response = (
        get_supabase().table("wallets")
        .update(
            {
                "available_balance": round(new_available, 2),
                "total_withdrawn": round(new_total_withdrawn, 2),
            }
        )
        .eq("provider_id", provider_id)
        .execute()
    )
    return response.data[0]


def credit_reward_and_update_trust(
    provider_id: str,
    valid: bool,
    reward_amount: float,
    description: str,
) -> dict[str, Any]:
    """
    Apply, in a single psycopg2 transaction (docs/04-arquitectura.md §14.3.2):
      - if valid: atomic wallet credit + transactions row
      - always: recompute accuracy/trust_score/rank for the provider, with
        the provider row locked (FOR UPDATE) for the whole calculation to
        avoid a lost update if two chunks of the same provider settle almost
        simultaneously.
    All or nothing: if any step raises, nothing is applied (automatic
    rollback on exiting the `with conn:` block via exception).
    """
    with psycopg2.connect(
        settings.supabase_db_url,
        cursor_factory=psycopg2.extras.RealDictCursor,
    ) as conn:
        with conn.cursor() as cur:
            # 1. Lock + read the provider's trust components
            cur.execute(
                """
                SELECT accuracy, completion_rate, response_time_score, client_rating
                FROM providers
                WHERE id = %s
                FOR UPDATE
                """,
                (provider_id,),
            )
            provider = cur.fetchone()
            if provider is None:
                raise ValueError(f"Provider {provider_id} no encontrado")

            # 2. Calculation in Python — same pure functions used elsewhere
            if valid:
                new_accuracy = trust_score.update_accuracy_on_complete(float(provider["accuracy"]))
            else:
                new_accuracy = trust_score.update_accuracy_on_fail(float(provider["accuracy"]))
            new_trust_score = trust_score.calculate_trust_score(
                completion_rate=float(provider["completion_rate"]),
                accuracy=new_accuracy,
                response_time_score=float(provider["response_time_score"]),
                client_rating=float(provider["client_rating"]),
            )
            new_rank = trust_score.get_rank(new_trust_score)

            # 3. Wallet credit + transaction (only if valid) — same arithmetic
            #    as update_wallet_on_task_complete, on the SAME connection/transaction
            if valid:
                cur.execute(
                    """
                    UPDATE wallets
                    SET available_balance = available_balance + %s,
                        total_earned      = total_earned + %s
                    WHERE provider_id = %s
                    RETURNING available_balance, total_earned
                    """,
                    (round(reward_amount, 2), round(reward_amount, 2), provider_id),
                )
                wallet_row = cur.fetchone()
                if wallet_row is None:
                    raise ValueError(f"No wallet found for provider {provider_id}")

                cur.execute(
                    """
                    INSERT INTO transactions (provider_id, amount, tx_type, description, status)
                    VALUES (%s, %s, 'pago_tarea', %s, 'completada')
                    """,
                    (provider_id, round(reward_amount, 2), description),
                )

            # 4. Write the new trust values
            cur.execute(
                """
                UPDATE providers
                SET accuracy = %s, trust_score = %s, rank = %s
                WHERE id = %s
                RETURNING accuracy, trust_score, rank
                """,
                (new_accuracy, new_trust_score, new_rank, provider_id),
            )
            updated_provider = cur.fetchone()

            conn.commit()

    return dict(updated_provider)
