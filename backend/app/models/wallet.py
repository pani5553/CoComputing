from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class WalletResponse(BaseModel):
    id: str
    provider_id: str
    available_balance: float
    pending_balance: float
    total_earned: float
    total_withdrawn: float
    updated_at: datetime


class TransactionResponse(BaseModel):
    id: str
    provider_id: str
    task_id: str | None = None
    amount: float
    tx_type: str
    status: str
    description: str
    withdraw_method: str | None = None
    withdraw_destination: str | None = None
    created_at: datetime


class TransactionListResponse(BaseModel):
    count: int
    total: int
    transactions: list[TransactionResponse]


class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    method: Literal["transferencia", "paypal", "cripto"]
    destination: str = Field(..., min_length=1, max_length=200)

    @field_validator("amount")
    @classmethod
    def validate_amount_decimals(cls, v: float) -> float:
        # Ensure at most 2 decimal places
        rounded = round(v, 2)
        return rounded


class WithdrawResponse(BaseModel):
    transaction_id: str
    amount: float
    method: str
    destination: str
    status: str
    new_available_balance: float
    message: str
