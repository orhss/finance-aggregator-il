"""Balance schemas."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel


class BalanceResponse(BaseModel):
    id: int
    account_id: int
    balance_date: date
    total_amount: float
    available: Optional[float] = None
    used: Optional[float] = None
    blocked: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percentage: Optional[float] = None
    currency: str
    created_at: datetime

    class Config:
        from_attributes = True


class LatestBalanceResponse(BaseModel):
    account_id: int
    institution: str
    account_type: str
    account_number: str
    account_name: Optional[str] = None
    balance: BalanceResponse


class PortfolioProgressionPoint(BaseModel):
    date: date
    series: str
    total_amount: float
    profit_loss: Optional[float] = None


class PortfolioProgressionResponse(BaseModel):
    points: List[PortfolioProgressionPoint]
    series_names: List[str]


class PnLSummaryItem(BaseModel):
    account_id: int
    label: str
    institution: str
    account_type: str
    total_amount: float
    profit_loss: Optional[float] = None
    profit_loss_percentage: Optional[float] = None
