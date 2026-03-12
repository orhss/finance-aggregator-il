"""Balance endpoints."""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends

from api.deps import CurrentUser, get_analytics
from api.schemas.balances import (
    BalanceResponse,
    LatestBalanceResponse,
    PnLSummaryItem,
    PortfolioProgressionPoint,
    PortfolioProgressionResponse,
)
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/balances", tags=["balances"])


def _balance_schema(balance) -> BalanceResponse:
    return BalanceResponse(
        id=balance.id,
        account_id=balance.account_id,
        balance_date=balance.balance_date,
        total_amount=balance.total_amount,
        available=balance.available,
        used=balance.used,
        blocked=balance.blocked,
        profit_loss=balance.profit_loss,
        profit_loss_percentage=balance.profit_loss_percentage,
        currency=balance.currency or "ILS",
        created_at=balance.created_at,
    )


@router.get("/latest", response_model=List[LatestBalanceResponse])
def latest_balances(
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    pairs = analytics.get_latest_balances()
    result = []
    for account, balance in pairs:
        result.append(LatestBalanceResponse(
            account_id=account.id,
            institution=account.institution,
            account_type=account.account_type,
            account_number=account.account_number,
            account_name=account.account_name,
            balance=_balance_schema(balance),
        ))
    return result


@router.get("/progression/by-type", response_model=PortfolioProgressionResponse)
def portfolio_by_type(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    points, series_names = analytics.get_portfolio_by_type(from_date=from_date, to_date=to_date)
    return PortfolioProgressionResponse(
        points=[PortfolioProgressionPoint(**p) for p in points],
        series_names=series_names,
    )


@router.get("/progression/by-account", response_model=PortfolioProgressionResponse)
def portfolio_by_account(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    points, series_names = analytics.get_portfolio_by_account(from_date=from_date, to_date=to_date)
    return PortfolioProgressionResponse(
        points=[PortfolioProgressionPoint(**p) for p in points],
        series_names=series_names,
    )


@router.get("/pnl-summary", response_model=List[PnLSummaryItem])
def pnl_summary(
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    pairs = analytics.get_latest_balances()
    return [
        PnLSummaryItem(
            account_id=account.id,
            label=account.account_name or f"{account.institution} ({account.account_type})",
            institution=account.institution,
            account_type=account.account_type,
            total_amount=balance.total_amount,
            profit_loss=balance.profit_loss,
            profit_loss_percentage=balance.profit_loss_percentage,
        )
        for account, balance in pairs
        if account.account_type != 'credit_card' and balance.profit_loss is not None
    ]


@router.get("/history/{account_id}", response_model=List[BalanceResponse])
def balance_history(
    account_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    balances = analytics.get_balance_history(account_id, from_date=from_date, to_date=to_date)
    return [_balance_schema(b) for b in balances]
