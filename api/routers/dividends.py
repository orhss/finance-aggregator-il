"""Dividend calculator endpoints."""

import logging

from typing import List

from fastapi import APIRouter, HTTPException, Query

from api.deps import CurrentUser
from api.schemas.dividends import (
    DividendSummaryResponse,
    DividendPaymentResponse,
    DripCompareItem,
    DripCompareRequest,
    DripCompareResponse,
    DripPointResponse,
    DripProjectionResponse,
    DripRequest,
    HoldingIncomeResponse,
    PortfolioIncomeRequest,
    PortfolioIncomeResponse,
    TickerSearchResultResponse,
)
from services.dividend_service import (
    fetch_dividend_summary,
    project_drip,
    project_portfolio_income,
    search_tickers,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dividends", tags=["dividends"])


@router.get("/search", response_model=List[TickerSearchResultResponse])
def ticker_search(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(8, ge=1, le=20),
    _: str = CurrentUser,
):
    """Search for tickers by name or symbol."""
    results = search_tickers(q, limit=limit)
    return [
        TickerSearchResultResponse(
            symbol=r.symbol,
            name=r.name,
            exchange=r.exchange,
            type=r.type,
        )
        for r in results
    ]


@router.get("/summary/{ticker}", response_model=DividendSummaryResponse)
def dividend_summary(ticker: str, _: str = CurrentUser):
    """Get dividend summary and history for a ticker."""
    try:
        s = fetch_dividend_summary(ticker)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Error fetching dividend data for %s", ticker)
        raise HTTPException(status_code=502, detail=f"Failed to fetch data: {e}")

    return DividendSummaryResponse(
        ticker=s.ticker,
        name=s.name,
        currency=s.currency,
        current_price=s.current_price,
        annual_dividend=s.annual_dividend,
        dividend_yield=s.dividend_yield,
        growth_rate_5y=s.growth_rate_5y,
        growth_rate_all=s.growth_rate_all,
        payment_frequency=s.payment_frequency,
        history=[
            DividendPaymentResponse(ex_date=d.ex_date.isoformat(), amount=d.amount)
            for d in s.history
        ],
    )


def _point_response(pt) -> DripPointResponse:
    return DripPointResponse(
        year=pt.year,
        shares=pt.shares,
        share_price=pt.share_price,
        annual_dividend_income=pt.annual_dividend_income,
        annual_tax=pt.annual_tax,
        annual_dividend_after_tax=pt.annual_dividend_after_tax,
        portfolio_value=pt.portfolio_value,
        total_dividends_received=pt.total_dividends_received,
        total_tax_paid=pt.total_tax_paid,
    )


@router.post("/drip", response_model=DripProjectionResponse)
def drip_projection(req: DripRequest, _: str = CurrentUser):
    """Project DRIP compounding over time."""
    try:
        p = project_drip(
            ticker=req.ticker,
            initial_shares=req.initial_shares,
            years=req.years,
            dividend_growth_rate=req.dividend_growth_rate,
            price_growth_rate=req.price_growth_rate,
            annual_contribution=req.annual_contribution,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Error projecting DRIP for %s", req.ticker)
        raise HTTPException(status_code=502, detail=f"Failed to compute projection: {e}")

    return DripProjectionResponse(
        ticker=p.ticker,
        initial_shares=p.initial_shares,
        initial_investment=p.initial_investment,
        dividend_growth_rate=p.dividend_growth_rate,
        price_growth_rate=p.price_growth_rate,
        years=p.years,
        points=[_point_response(pt) for pt in p.points],
    )


@router.post("/drip-compare", response_model=DripCompareResponse)
def drip_compare(req: DripCompareRequest, _: str = CurrentUser):
    """Compare DRIP projections across multiple tickers with per-ticker growth rates."""
    if len(req.tickers) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 tickers for comparison")

    results: List[DripCompareItem] = []
    for t_input in req.tickers:
        try:
            p = project_drip(
                ticker=t_input.ticker,
                initial_shares=req.initial_shares,
                years=req.years,
                dividend_growth_rate=t_input.dividend_growth_rate,
                price_growth_rate=t_input.price_growth_rate,
                annual_contribution=req.annual_contribution,
                share_price_override=t_input.share_price_override,
                dividend_tax_rate=req.dividend_tax_rate,
            )
            results.append(DripCompareItem(
                ticker=p.ticker,
                name=p.name,
                initial_share_price=p.initial_share_price,
                dividend_yield=round(p.points[0].annual_dividend_income / p.initial_investment * 100, 2) if p.initial_investment > 0 else 0,
                dividend_growth_rate=p.dividend_growth_rate,
                price_growth_rate=p.price_growth_rate,
                initial_investment=p.initial_investment,
                ending_balance=p.ending_balance,
                total_return_pct=p.total_return_pct,
                avg_annual_return_pct=p.avg_annual_return_pct,
                final_annual_income=p.final_annual_income,
                final_annual_income_after_tax=p.final_annual_income_after_tax,
                total_dividends_paid=p.total_dividends_paid,
                total_tax_paid=p.total_tax_paid,
                yield_on_cost=p.yield_on_cost,
                points=[_point_response(pt) for pt in p.points],
            ))
        except Exception as e:
            logger.warning("Failed to compute DRIP for %s: %s", t_input.ticker, e)
            results.append(DripCompareItem(
                ticker=t_input.ticker.upper(),
                name=t_input.ticker.upper(),
                initial_share_price=0,
                dividend_yield=0,
                dividend_growth_rate=0,
                price_growth_rate=t_input.price_growth_rate,
                initial_investment=0,
                ending_balance=0,
                total_return_pct=0,
                avg_annual_return_pct=0,
                final_annual_income=0,
                final_annual_income_after_tax=0,
                total_dividends_paid=0,
                total_tax_paid=0,
                yield_on_cost=0,
                points=[],
                error=str(e),
            ))

    return DripCompareResponse(
        initial_shares=req.initial_shares,
        years=req.years,
        results=results,
    )


@router.post("/portfolio-income", response_model=PortfolioIncomeResponse)
def portfolio_income(req: PortfolioIncomeRequest, _: str = CurrentUser):
    """Calculate projected annual dividend income for a portfolio."""
    try:
        p = project_portfolio_income(
            [{"ticker": h.ticker, "shares": h.shares} for h in req.holdings]
        )
    except Exception as e:
        logger.exception("Error computing portfolio income")
        raise HTTPException(status_code=502, detail=f"Failed to compute: {e}")

    return PortfolioIncomeResponse(
        total_annual_income=p.total_annual_income,
        total_portfolio_value=p.total_portfolio_value,
        weighted_yield=p.weighted_yield,
        holdings=[
            HoldingIncomeResponse(
                ticker=h.get("ticker", ""),
                name=h.get("name", ""),
                shares=h.get("shares", 0),
                price=h.get("price"),
                annual_dividend_per_share=h.get("annual_dividend_per_share"),
                annual_income=h.get("annual_income"),
                value=h.get("value"),
                yield_pct=h.get("yield"),
                currency=h.get("currency"),
                error=h.get("error"),
            )
            for h in p.holdings
        ],
    )
