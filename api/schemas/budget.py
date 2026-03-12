"""Budget schemas."""

from typing import Optional
from pydantic import BaseModel, Field


class BudgetResponse(BaseModel):
    id: int
    year: int
    month: int
    amount: float

    class Config:
        from_attributes = True


class BudgetSet(BaseModel):
    amount: float = Field(..., gt=0)


class BudgetProgress(BaseModel):
    year: int
    month: int
    budget: Optional[float] = None
    spent: float
    remaining: Optional[float] = None
    percent: Optional[float] = None
    percent_actual: Optional[float] = None
    is_over_budget: Optional[bool] = None
