"""Transaction endpoints."""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import CurrentUser, get_analytics, get_db, get_tag_service
from api.schemas.common import CountResponse, PaginatedResponse
from api.schemas.transactions import TransactionResponse, TransactionUpdate
from services.analytics_service import AnalyticsService
from services.tag_service import TagService

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _txn_schema(txn) -> TransactionResponse:
    return TransactionResponse(
        id=txn.id,
        account_id=txn.account_id,
        transaction_id=txn.transaction_id,
        transaction_date=txn.transaction_date,
        processed_date=txn.processed_date,
        description=txn.description,
        original_amount=txn.original_amount,
        original_currency=txn.original_currency,
        charged_amount=txn.charged_amount,
        charged_currency=txn.charged_currency,
        transaction_type=txn.transaction_type,
        status=txn.status,
        raw_category=txn.raw_category,
        category=txn.category,
        user_category=txn.user_category,
        effective_category=txn.effective_category,
        memo=txn.memo,
        installment_number=txn.installment_number,
        installment_total=txn.installment_total,
        tags=txn.tags,
        created_at=txn.created_at,
    )


@router.get("", response_model=PaginatedResponse[TransactionResponse])
def list_transactions(
    account_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[str] = None,
    institution: Optional[str] = None,
    untagged_only: bool = False,
    page: int = 1,
    page_size: int = 50,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    page_size = min(page_size, 200)
    offset = (page - 1) * page_size

    # Get total count
    total = analytics.get_transaction_count(
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        status=status,
    )

    txns = analytics.get_transactions(
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        status=status,
        institution=institution,
        untagged_only=untagged_only,
        limit=page_size,
        offset=offset,
    )

    return PaginatedResponse(
        items=[_txn_schema(t) for t in txns],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + len(txns)) < total,
    )


@router.get("/count", response_model=CountResponse)
def transaction_count(
    account_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    status: Optional[str] = None,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    count = analytics.get_transaction_count(
        account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        status=status,
    )
    return CountResponse(count=count)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    txn = analytics.get_transaction_by_id(transaction_id)
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return _txn_schema(txn)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    body: TransactionUpdate,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
    tag_service: TagService = Depends(get_tag_service),
):
    txn = analytics.get_transaction_by_id(transaction_id)
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    updated = tag_service.update_transaction(
        transaction_id=transaction_id,
        user_category=body.user_category,
        memo=body.memo,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    # Refresh
    txn = analytics.get_transaction_by_id(transaction_id)
    return _txn_schema(txn)
