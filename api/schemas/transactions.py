"""Transaction schemas."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel


class TransactionResponse(BaseModel):
    id: int
    account_id: int
    transaction_id: Optional[str] = None
    transaction_date: date
    processed_date: Optional[date] = None
    description: str
    original_amount: float
    original_currency: str
    charged_amount: Optional[float] = None
    charged_currency: Optional[str] = None
    transaction_type: Optional[str] = None
    status: Optional[str] = None
    raw_category: Optional[str] = None
    category: Optional[str] = None
    user_category: Optional[str] = None
    effective_category: Optional[str] = None
    memo: Optional[str] = None
    installment_number: Optional[int] = None
    installment_total: Optional[int] = None
    tags: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionUpdate(BaseModel):
    user_category: Optional[str] = None
    memo: Optional[str] = None


class TransactionFilters(BaseModel):
    account_id: Optional[int] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = None
    institution: Optional[str] = None
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    untagged_only: bool = False
    page: int = 1
    page_size: int = 50
