"""Account endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends

from api.deps import CurrentUser, get_analytics
from api.schemas.accounts import AccountResponse, AccountSummary, BalanceSummary
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _balance_schema(balance) -> Optional[BalanceSummary]:
    if balance is None:
        return None
    return BalanceSummary(
        total_amount=balance.total_amount,
        available=balance.available,
        profit_loss=balance.profit_loss,
        profit_loss_percentage=balance.profit_loss_percentage,
        currency=balance.currency or "ILS",
        balance_date=balance.balance_date,
    )


def _account_schema(account) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        account_type=account.account_type,
        institution=account.institution,
        account_number=account.account_number,
        account_name=account.account_name,
        card_unique_id=account.card_unique_id,
        is_active=account.is_active,
        created_at=account.created_at,
        last_synced_at=account.last_synced_at,
        latest_balance=_balance_schema(account.latest_balance),
    )


@router.get("", response_model=List[AccountResponse])
def list_accounts(
    active_only: bool = True,
    account_type: Optional[str] = None,
    institution: Optional[str] = None,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    if institution:
        accounts = analytics.get_accounts_by_institution(institution, active_only=active_only)
    elif account_type:
        accounts = analytics.get_accounts_by_type(account_type, active_only=active_only)
    else:
        accounts = analytics.get_all_accounts(active_only=active_only)

    return [_account_schema(a) for a in accounts]


@router.get("/summary", response_model=AccountSummary)
def account_summary(
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    raw = analytics.get_account_summary()
    latest_balances = analytics.get_latest_balances()
    total_balance = sum(b.total_amount for _, b in latest_balances)
    return AccountSummary(
        total_accounts=raw["total_accounts"],
        by_type=raw["by_type"],
        by_institution=raw["by_institution"],
        total_balance=total_balance,
    )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: int,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    from fastapi import HTTPException, status
    account = analytics.get_account_by_id(account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return _account_schema(account)
