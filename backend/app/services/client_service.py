"""
Client-side service: deposit, publish tasks, escrow management, cancellation.
"""
import logging
from typing import Any

from fastapi import HTTPException, status

from app.db.queries import client_queries, wallet_queries

logger = logging.getLogger(__name__)

MIN_DEPOSIT = 1.0


def deposit(client_id: str, amount: float) -> dict[str, Any]:
    """
    Simulate a CC deposit: add amount to available_balance and record a transaction.
    """
    if amount < MIN_DEPOSIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El depósito mínimo es {MIN_DEPOSIT:.2f} CC",
        )

    wallet = client_queries.deposit_to_wallet(client_id, amount)
    tx = wallet_queries.create_transaction(
        provider_id=client_id,
        amount=amount,
        tx_type="deposito",
        description=f"Depósito simulado de {amount:.2f} CC",
        status="completada",
    )
    return {
        "transaction_id": tx["id"],
        "amount": amount,
        "new_available_balance": float(wallet["available_balance"]),
        "message": f"Depósito de {amount:.2f} CC realizado correctamente.",
    }


def create_task(
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
    """
    Publish a new task. Validates balance, creates the task, locks escrow.
    Escrow = reward × total_slots deducted from available_balance atomically.
    """
    escrow_total = round(reward * total_slots, 2)

    # Check wallet exists and has enough balance
    wallet = wallet_queries.get_wallet_by_provider_id(client_id)
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cartera no encontrada",
        )
    available = float(wallet["available_balance"])
    if available < escrow_total:
        formatted = f"{available:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saldo insuficiente. Necesitas {escrow_total:.2f} CC (tienes {formatted} CC disponibles).",
        )

    # Create task row first (we need the task_id for the escrow)
    task = client_queries.create_client_task(
        client_id=client_id,
        title=title,
        task_type=task_type,
        description=description,
        reward=reward,
        difficulty=difficulty,
        hardware_required=hardware_required,
        total_slots=total_slots,
        duration_min=duration_min,
        duration_max=duration_max,
        stages=stages,
        requester_name=requester_name,
    )

    # Lock escrow (atomic: deduct available_balance, increment pending_balance)
    try:
        client_queries.hold_escrow(client_id, task["id"], reward, total_slots)
    except ValueError as exc:
        if "insufficient_balance" in str(exc):
            # Race condition: another request drained the balance between check and hold
            # Roll back the task row
            _delete_task_unsafe(task["id"])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Saldo insuficiente al intentar retener el escrow.",
            ) from exc
        raise

    # Record escrow transaction
    wallet_queries.create_transaction(
        provider_id=client_id,
        amount=escrow_total,
        tx_type="escrow",
        description=f"Escrow retenido para tarea: {title} ({total_slots} plazas × {reward:.2f} CC)",
        status="completada",
        task_id=task["id"],
    )

    # Refresh wallet to return updated balance
    updated_wallet = wallet_queries.get_wallet_by_provider_id(client_id)

    return {
        "task_id": task["id"],
        "title": title,
        "reward": reward,
        "total_slots": total_slots,
        "escrow_total": escrow_total,
        "new_available_balance": float(updated_wallet["available_balance"]),
        "message": f"Tarea publicada. Se han retenido {escrow_total:.2f} CC en escrow.",
    }


def get_my_tasks(client_id: str) -> dict[str, Any]:
    """Return all tasks published by the client with escrow and completion info."""
    tasks = client_queries.get_client_tasks(client_id)
    return {"count": len(tasks), "tasks": tasks}


def get_task_detail(client_id: str, task_id: str) -> dict[str, Any]:
    """Return full task detail (assignments, escrow) for the client owner."""
    task = client_queries.get_client_task_detail(task_id, client_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada o no tienes permiso para verla",
        )
    return task


def cancel_task(client_id: str, task_id: str) -> dict[str, Any]:
    """
    Cancel a task and refund unreleased escrow to the client's available_balance.
    """
    # Mark task as cancelled (validates ownership and current status)
    updated_task = client_queries.cancel_task_db(task_id, client_id)
    if updated_task is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tarea no encontrada, no te pertenece, o ya está completada/cancelada",
        )

    # Refund unreleased escrow
    try:
        refund = client_queries.refund_escrow(task_id, client_id)
    except ValueError as exc:
        if "escrow_not_active" in str(exc):
            # Task from seed (no escrow) — no refund needed
            refund = 0.0
        else:
            raise

    # Record refund transaction if there's something to refund
    if refund > 0:
        wallet_queries.create_transaction(
            provider_id=client_id,
            amount=refund,
            tx_type="reembolso",
            description=f"Reembolso de escrow por cancelación de tarea: {updated_task['title']}",
            status="completada",
            task_id=task_id,
        )

    wallet = wallet_queries.get_wallet_by_provider_id(client_id)

    return {
        "task_id": task_id,
        "refund_amount": refund,
        "new_available_balance": float(wallet["available_balance"]),
        "message": (
            f"Tarea cancelada. Se han reembolsado {refund:.2f} CC a tu saldo disponible."
            if refund > 0
            else "Tarea cancelada. No había escrow pendiente de reembolso."
        ),
    }


def _delete_task_unsafe(task_id: str) -> None:
    """Delete a task row (cleanup on failed escrow). Best-effort — logs errors."""
    try:
        from app.db.client import get_supabase
        get_supabase().table("tasks").delete().eq("id", task_id).execute()
    except Exception as exc:
        logger.error("Failed to rollback task %s after escrow failure: %s", task_id, exc)
