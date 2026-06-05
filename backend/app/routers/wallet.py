"""
Wallet router: balance, transactions, and withdrawal.
"""
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_provider
from app.models.wallet import (
    TransactionListResponse,
    WalletResponse,
    WithdrawRequest,
    WithdrawResponse,
)
from app.services import wallet_service

router = APIRouter()


@router.get("/", response_model=WalletResponse)
def get_wallet(
    current_provider: dict = Depends(get_current_provider),
) -> WalletResponse:
    """Return the current balances of the authenticated provider's wallet."""
    provider_id: str = current_provider["id"]
    wallet = wallet_service.get_wallet(provider_id)
    return WalletResponse(**wallet)


@router.get("/transactions", response_model=TransactionListResponse)
def get_transactions(
    limit: int = Query(default=50, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    current_provider: dict = Depends(get_current_provider),
) -> TransactionListResponse:
    """Return a paginated list of transactions for the authenticated provider."""
    provider_id: str = current_provider["id"]
    result = wallet_service.get_transactions(provider_id, limit=limit, offset=offset)
    return TransactionListResponse(**result)


@router.post("/withdraw", response_model=WithdrawResponse)
def withdraw(
    payload: WithdrawRequest,
    current_provider: dict = Depends(get_current_provider),
) -> WithdrawResponse:
    """Register a withdrawal request for the authenticated provider."""
    provider_id: str = current_provider["id"]
    result = wallet_service.process_withdrawal(
        provider_id=provider_id,
        amount=payload.amount,
        method=payload.method,
        destination=payload.destination,
    )
    return WithdrawResponse(**result)
