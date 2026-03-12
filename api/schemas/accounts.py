"""Account schemas."""

from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class BalanceSummary(BaseModel):
    total_amount: float
    available: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percentage: Optional[float] = None
    currency: str = "ILS"
    balance_date: Optional[date] = None

    class Config:
        from_attributes = True


class AccountResponse(BaseModel):
    id: int
    account_type: str
    institution: str
    account_number: str
    account_name: Optional[str] = None
    card_unique_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_synced_at: Optional[datetime] = None
    latest_balance: Optional[BalanceSummary] = None

    class Config:
        from_attributes = True


class AccountSummary(BaseModel):
    total_accounts: int
    by_type: dict
    by_institution: dict
    total_balance: float
