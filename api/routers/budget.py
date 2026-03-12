"""Budget endpoints."""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import CurrentUser, get_budget_service
from api.schemas.budget import BudgetProgress, BudgetResponse, BudgetSet
from services.budget_service import BudgetService

router = APIRouter(prefix="/budget", tags=["budget"])


@router.get("/progress", response_model=BudgetProgress)
def budget_progress(
    year: Optional[int] = None,
    month: Optional[int] = None,
    _: str = CurrentUser,
    svc: BudgetService = Depends(get_budget_service),
):
    today = date.today()
    return BudgetProgress(**svc.get_budget_progress(
        year=year or today.year,
        month=month or today.month,
    ))


@router.get("", response_model=Optional[BudgetResponse])
def get_budget(
    year: Optional[int] = None,
    month: Optional[int] = None,
    _: str = CurrentUser,
    svc: BudgetService = Depends(get_budget_service),
):
    today = date.today()
    budget = svc.get_budget(year or today.year, month or today.month)
    if not budget:
        return None
    return BudgetResponse.model_validate(budget)


@router.put("", response_model=BudgetResponse)
def set_budget(
    body: BudgetSet,
    year: Optional[int] = None,
    month: Optional[int] = None,
    _: str = CurrentUser,
    svc: BudgetService = Depends(get_budget_service),
):
    today = date.today()
    budget = svc.set_budget(year or today.year, month or today.month, body.amount)
    return BudgetResponse.model_validate(budget)


@router.delete("", status_code=204)
def delete_budget(
    year: Optional[int] = None,
    month: Optional[int] = None,
    _: str = CurrentUser,
    svc: BudgetService = Depends(get_budget_service),
):
    today = date.today()
    deleted = svc.delete_budget(year or today.year, month or today.month)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
