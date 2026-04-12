"""Pydantic schemas for the retirement calculator API."""

import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, field_validator


class SimulationSummary(BaseModel):
    fire_age: float
    fire_date: str
    fire_month_index: int
    years_to_fire: float
    min_nw: float
    min_nw_age: float
    end_nw: float
    end_age: float
    portfolio_depletion_age: Optional[float] = None
    pension_start_ages: List[float]
    old_age_start_ages: List[float]
    withdrawal_rate_at_fire: float


class MonthlyRow(BaseModel):
    month: int
    age: float
    date: str
    # Asset values
    net_worth: float
    portfolio: float
    kh_values: List[float]
    pension_values: List[float]
    kaspit: float
    checking: float
    # Flows
    income: float
    expenses: float
    goals: float
    deposit: float
    withdrawal_portfolio: float
    withdrawal_kh: List[float]
    # Pension income (per person)
    pension_mukeret: List[float]
    pension_mazka: List[float]
    old_age: List[float]
    # Tax (per person)
    income_tax: List[float]
    bituach_leumi: List[float]
    portfolio_tax: float


class Milestone(BaseModel):
    age: float  # The relevant person's actual age
    chart_age: Optional[float] = None  # Primary person's age (for chart X-axis)
    date: str
    type: Literal[
        'fire', 'pension_conversion', 'old_age_start',
        'portfolio_depleted', 'kh_depleted', 'one_time_expense',
    ]
    label: str
    person: Optional[str] = None
    amount: Optional[float] = None


class SimulationResponse(BaseModel):
    status: Literal['success', 'impossible']
    summary: SimulationSummary
    monthly: List[MonthlyRow]
    milestones: List[Milestone]
    persons: List[str]


# ==================== Scenario CRUD ====================

class ScenarioCreate(BaseModel):
    name: str
    config: Dict[str, Any]


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ScenarioResponse(BaseModel):
    id: int
    name: str
    config: Dict[str, Any]
    created_at: str
    updated_at: Optional[str] = None

    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            return json.loads(v)
        return v
