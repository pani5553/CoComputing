"""
Wallet service: balance retrieval, transactions, and withdrawal logic.
"""
import logging
from typing import Any

from fastapi import HTTPException, status

from app.db.queries import wallet_queries

logger = logging.getLogger(__name__)


MIN_WITHDRAW_AMOUNT = 10.0


def get_wallet(provider_id: str) -> dict[str, Any]:
    """Return the wallet for the given provider, raising 404 if absent."""
    wallet = wallet_queries.get_wallet_by_provider_id(provider_id)
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cartera no encontrada",
        )
    return wallet


def get_transactions(
    provider_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Return paginated transactions for the provider."""
    rows, total = wallet_queries.get_transactions(provider_id, limit=limit, offset=offset)
    return {
        "count": len(rows),
        "total": total,
        "transactions": rows,
    }


def process_withdrawal(
    provider_id: str,
    amount: float,
    method: str,
    destination: str,
) -> dict[str, Any]:
    """
    Register a withdrawal request.

    Validates:
    - amount >= MIN_WITHDRAW_AMOUNT
    - amount <= available_balance

    Side effects:
    - Deducts available_balance
    - Creates a transaction row (type=retiro, status=pendiente)
    """
    if amount < MIN_WITHDRAW_AMOUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto mínimo de retiro es {MIN_WITHDRAW_AMOUNT:,.2f} CC".replace(",", "X").replace(".", ",").replace("X", "."),
        )

    wallet = wallet_queries.get_wallet_by_provider_id(provider_id)
    if wallet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cartera no encontrada",
        )

    available = float(wallet["available_balance"])
    if amount > available:
        formatted_balance = f"{available:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El monto supera tu saldo disponible ({formatted_balance} CC)",
        )

    # Deduct balance
    updated_wallet = wallet_queries.update_wallet_on_withdraw(provider_id, amount)

    # Create transaction
    method_label = {"transferencia": "transferencia bancaria", "paypal": "PayPal", "cripto": "criptomoneda"}
    tx = wallet_queries.create_transaction(
        provider_id=provider_id,
        amount=amount,
        tx_type="retiro",
        description=f"Solicitud de retiro via {method_label.get(method, method)}",
        status="pendiente",
        withdraw_method=method,
        withdraw_destination=destination,
    )

    return {
        "transaction_id": tx["id"],
        "amount": amount,
        "method": method,
        "destination": destination,
        "status": "pendiente",
        "new_available_balance": float(updated_wallet["available_balance"]),
        "message": "Solicitud de retiro registrada. Te contactaremos cuando se procese.",
    }


def credit_reward(provider_id: str, amount: float, description: str) -> None:
    """
    Credit amount to wallets.available_balance and total_earned for the provider.
    Creates a transaction row (tx_type='pago_tarea', status='completada').
    Used by consensus_service to pay providers for valid chunk results.
    """
    try:
        wallet_queries.update_wallet_on_task_complete(provider_id, amount)
        wallet_queries.create_transaction(
            provider_id=provider_id,
            amount=amount,
            tx_type="pago_tarea",
            description=description,
            status="completada",
        )
    except Exception as exc:
        logger.error(
            "Error acreditando recompensa al proveedor %s: %s", provider_id, exc, exc_info=True
        )
        raise
