"""Analytics endpoints."""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends

from api.deps import CurrentUser, get_analytics
from api.schemas.analytics import (
    CategoryBreakdownItem,
    CategoryTrendsResponse,
    CardSpendingItem,
    MonthlySummary,
    StatsResponse,
    TagBreakdownItem,
    TrendPoint,
)
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stats", response_model=StatsResponse)
def overall_stats(
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    raw = analytics.get_overall_stats()
    return StatsResponse(**raw)


@router.get("/monthly", response_model=MonthlySummary)
def monthly_summary(
    year: int,
    month: int,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    raw = analytics.get_monthly_summary(year, month)
    return MonthlySummary(**raw)


@router.get("/trends", response_model=List[TrendPoint])
def monthly_trends(
    months: int = 6,
    tag: Optional[str] = None,
    card_last4: Optional[str] = None,
    include_current: bool = False,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    data = analytics.get_monthly_spending_trends(
        months=months, tag=tag, card_last4=card_last4, include_current=include_current
    )
    return [TrendPoint(**d) for d in data]


@router.get("/categories", response_model=List[CategoryBreakdownItem])
def category_breakdown(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    raw = analytics.get_category_breakdown(from_date=from_date, to_date=to_date)
    return [
        CategoryBreakdownItem(
            category=cat,
            count=v["count"],
            total_amount=v["total_amount"],
            avg_amount=v["avg_amount"],
        )
        for cat, v in raw.items()
    ]


@router.get("/category-trends", response_model=CategoryTrendsResponse)
def category_trends(
    months: int = 6,
    top_n: int = 5,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    raw = analytics.get_category_trends(months=months, top_n=top_n)
    return CategoryTrendsResponse(**raw)


@router.get("/tags", response_model=List[TagBreakdownItem])
def tag_breakdown(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    raw = analytics.get_tag_breakdown(from_date=from_date, to_date=to_date)
    return [
        TagBreakdownItem(
            tag=tag,
            count=v["count"],
            total_amount=v["total_amount"],
            percentage=v["percentage"],
        )
        for tag, v in raw.items()
    ]


@router.get("/cards", response_model=List[CardSpendingItem])
def spending_by_card(
    months: int = 6,
    _: str = CurrentUser,
    analytics: AnalyticsService = Depends(get_analytics),
):
    raw = analytics.get_spending_by_card_holder(months=months)
    return [
        CardSpendingItem(
            last4=last4,
            total_amount=v["total_amount"],
            transaction_count=v["transaction_count"],
            percentage=v["percentage"],
        )
        for last4, v in raw.items()
    ]
