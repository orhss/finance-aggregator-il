"""Analytics schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class StatsResponse(BaseModel):
    total_accounts: int
    total_transactions: int
    pending_transactions: int
    total_balance: float
    last_sync: Optional[datetime] = None


class MonthlySummary(BaseModel):
    year: int
    month: int
    transaction_count: int
    total_amount: float
    total_charged: float
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    by_account: Dict[str, int]


class TrendPoint(BaseModel):
    year: int
    month: int
    total_amount: float
    transaction_count: int


class CategoryBreakdownItem(BaseModel):
    category: str
    count: int
    total_amount: float
    avg_amount: float


class TagBreakdownItem(BaseModel):
    tag: str
    count: int
    total_amount: float
    percentage: float


class CardSpendingItem(BaseModel):
    last4: str
    total_amount: float
    transaction_count: int
    percentage: float


class CategoryTrendsResponse(BaseModel):
    categories: Dict[str, List[Dict[str, Any]]]
    totals: Dict[str, float]
