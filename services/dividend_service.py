"""
Dividend calculator service.

Fetches dividend data via yfinance and computes yield, growth rate (CAGR),
DRIP compounding projections, and projected annual income.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

import requests
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class DividendPayment:
    """Single historical dividend payment."""
    ex_date: date
    amount: float  # per share, in local currency


@dataclass
class DividendSummary:
    """Summary stats for a single ticker."""
    ticker: str
    name: str
    currency: str
    current_price: float
    annual_dividend: float  # trailing 12m sum
    dividend_yield: float  # percentage
    growth_rate_5y: Optional[float]  # 5-year CAGR percentage
    growth_rate_all: Optional[float]  # all-time CAGR percentage
    payment_frequency: int  # payments per year
    history: List[DividendPayment]


@dataclass
class DripProjectionPoint:
    """Single year in a DRIP projection."""
    year: int
    shares: float
    share_price: float
    annual_dividend_income: float  # gross (pre-tax)
    annual_tax: float
    annual_dividend_after_tax: float
    portfolio_value: float
    total_dividends_received: float  # cumulative gross
    total_tax_paid: float  # cumulative


@dataclass
class DripProjection:
    """Full DRIP projection result."""
    ticker: str
    name: str
    initial_shares: float
    initial_share_price: float
    initial_investment: float
    dividend_growth_rate: float  # annual %
    price_growth_rate: float  # annual %
    annual_contribution: float
    years: int
    dividend_tax_rate: float  # percentage
    # Summary stats
    ending_balance: float
    total_return_pct: float  # percentage
    avg_annual_return_pct: float  # percentage
    final_annual_income: float  # gross
    final_annual_income_after_tax: float
    total_dividends_paid: float  # gross
    total_tax_paid: float
    yield_on_cost: float  # percentage
    points: List[DripProjectionPoint]


@dataclass
class PortfolioIncomeProjection:
    """Projected dividend income for a portfolio of holdings."""
    total_annual_income: float
    total_portfolio_value: float
    weighted_yield: float  # percentage
    holdings: List[dict]  # per-holding breakdown


def fetch_dividend_summary(ticker: str) -> DividendSummary:
    """
    Fetch dividend data for a ticker and compute summary stats.

    Raises ValueError if ticker not found or has no dividend history.
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    if not info or info.get("regularMarketPrice") is None:
        raise ValueError(f"Ticker '{ticker}' not found or has no price data")

    dividends = stock.dividends
    if dividends is None or dividends.empty:
        raise ValueError(f"Ticker '{ticker}' has no dividend history")

    current_price = info.get("regularMarketPrice") or info.get("previousClose", 0)
    name = info.get("shortName") or info.get("longName") or ticker
    currency = info.get("currency", "USD")

    # Build history
    history = []
    for dt, amount in dividends.items():
        ex_date = dt.date() if hasattr(dt, "date") else dt
        history.append(DividendPayment(ex_date=ex_date, amount=round(float(amount), 6)))

    # Trailing 12-month annual dividend
    one_year_ago = date.today().replace(year=date.today().year - 1)
    recent = [d for d in history if d.ex_date >= one_year_ago]
    annual_dividend = sum(d.amount for d in recent) if recent else 0.0

    # Dividend yield
    dividend_yield = (annual_dividend / current_price * 100) if current_price > 0 else 0.0

    # Payment frequency (from trailing 12m)
    payment_frequency = len(recent)

    # Growth rate CAGRs
    growth_5y = _compute_dividend_cagr(history, max_years=5)
    growth_all = _compute_dividend_cagr(history)

    return DividendSummary(
        ticker=ticker.upper(),
        name=name,
        currency=currency,
        current_price=round(current_price, 2),
        annual_dividend=round(annual_dividend, 4),
        dividend_yield=round(dividend_yield, 2),
        growth_rate_5y=round(growth_5y, 2) if growth_5y is not None else None,
        growth_rate_all=round(growth_all, 2) if growth_all is not None else None,
        payment_frequency=payment_frequency,
        history=history,
    )


def project_drip(
    ticker: str,
    initial_shares: float,
    years: int = 20,
    dividend_growth_rate: Optional[float] = None,
    price_growth_rate: float = 7.0,
    annual_contribution: float = 0.0,
    share_price_override: Optional[float] = None,
    dividend_tax_rate: float = 0.0,
) -> DripProjection:
    """
    Project DRIP (dividend reinvestment) compounding over time.

    Compounds quarterly: each quarter, dividends are taxed at the given rate,
    then the after-tax amount is reinvested at the current quarter-end price.
    Annual contributions are added at year start.

    Args:
        ticker: Stock ticker symbol
        initial_shares: Number of shares to start with
        years: Projection horizon
        dividend_growth_rate: Annual dividend growth % (None = use 5-year CAGR)
        price_growth_rate: Annual price appreciation % (default 7%)
        annual_contribution: Additional $ invested per year (default 0)
        share_price_override: Override the starting share price (None = use current)
        dividend_tax_rate: Tax rate on dividends as % (default 0). Tax is deducted
            from each dividend payment before reinvestment.

    Returns:
        DripProjection with yearly breakdown and summary stats.
    """
    summary = fetch_dividend_summary(ticker)

    if dividend_growth_rate is None:
        dividend_growth_rate = summary.growth_rate_5y or summary.growth_rate_all or 0.0

    shares = initial_shares
    price = share_price_override if share_price_override is not None else summary.current_price
    initial_price = price

    annual_div_per_share = summary.annual_dividend
    quarterly_div = annual_div_per_share / 4
    initial_investment = shares * price
    total_contributions = initial_investment
    cumulative_divs = 0.0
    cumulative_tax = 0.0
    tax_multiplier = dividend_tax_rate / 100

    # Quarterly price/dividend growth factors
    q_price_growth = (1 + price_growth_rate / 100) ** 0.25
    q_div_growth = (1 + dividend_growth_rate / 100) ** 0.25

    points = []
    # Track per-year tax for the point record
    year_tax = 0.0
    year_divs_gross = 0.0

    for yr in range(years + 1):
        # Record year-start state
        annual_income_gross = shares * annual_div_per_share
        annual_tax_est = annual_income_gross * tax_multiplier
        portfolio_value = shares * price

        points.append(DripProjectionPoint(
            year=yr,
            shares=round(shares, 4),
            share_price=round(price, 2),
            annual_dividend_income=round(annual_income_gross, 2),
            annual_tax=round(year_tax, 2) if yr > 0 else round(annual_tax_est, 2),
            annual_dividend_after_tax=round(
                (year_divs_gross - year_tax) if yr > 0 else (annual_income_gross - annual_tax_est), 2
            ),
            portfolio_value=round(portfolio_value, 2),
            total_dividends_received=round(cumulative_divs, 2),
            total_tax_paid=round(cumulative_tax, 2),
        ))

        if yr < years:
            # Reset per-year accumulators
            year_tax = 0.0
            year_divs_gross = 0.0

            # Annual contribution at start of year
            if annual_contribution > 0 and price > 0:
                shares += annual_contribution / price
                total_contributions += annual_contribution

            # Simulate 4 quarters
            for _q in range(4):
                # Gross dividend payment
                gross_div = shares * quarterly_div
                tax = gross_div * tax_multiplier
                net_div = gross_div - tax

                cumulative_divs += gross_div
                cumulative_tax += tax
                year_tax += tax
                year_divs_gross += gross_div

                # Price appreciates this quarter
                price *= q_price_growth

                # DRIP: reinvest after-tax dividends at new price
                if price > 0:
                    shares += net_div / price

                # Dividend per share grows this quarter
                quarterly_div *= q_div_growth

            # Recalc annual div per share
            annual_div_per_share = quarterly_div * 4

    # Summary stats
    last = points[-1]
    ending_balance = last.portfolio_value
    total_return_pct = ((ending_balance - total_contributions) / total_contributions * 100) if total_contributions > 0 else 0.0
    avg_annual_return_pct = (((ending_balance / total_contributions) ** (1 / years) - 1) * 100) if total_contributions > 0 and years > 0 else 0.0
    yield_on_cost = (last.annual_dividend_income / total_contributions * 100) if total_contributions > 0 else 0.0

    return DripProjection(
        ticker=ticker.upper(),
        name=summary.name,
        initial_shares=initial_shares,
        initial_share_price=round(initial_price, 2),
        initial_investment=round(initial_investment, 2),
        dividend_growth_rate=dividend_growth_rate,
        price_growth_rate=price_growth_rate,
        annual_contribution=annual_contribution,
        dividend_tax_rate=dividend_tax_rate,
        years=years,
        ending_balance=round(ending_balance, 2),
        total_return_pct=round(total_return_pct, 2),
        avg_annual_return_pct=round(avg_annual_return_pct, 2),
        final_annual_income=round(last.annual_dividend_income, 2),
        final_annual_income_after_tax=round(last.annual_dividend_after_tax, 2),
        total_dividends_paid=round(cumulative_divs, 2),
        total_tax_paid=round(cumulative_tax, 2),
        yield_on_cost=round(yield_on_cost, 2),
        points=points,
    )


def project_portfolio_income(
    holdings: List[dict],
) -> PortfolioIncomeProjection:
    """
    Calculate projected annual dividend income for a portfolio.

    Args:
        holdings: List of {"ticker": str, "shares": float}

    Returns:
        PortfolioIncomeProjection with per-holding and total income.
    """
    result_holdings = []
    total_income = 0.0
    total_value = 0.0

    for h in holdings:
        ticker = h["ticker"]
        shares = h["shares"]
        try:
            summary = fetch_dividend_summary(ticker)
            annual_income = shares * summary.annual_dividend
            value = shares * summary.current_price
            result_holdings.append({
                "ticker": summary.ticker,
                "name": summary.name,
                "shares": shares,
                "price": summary.current_price,
                "annual_dividend_per_share": summary.annual_dividend,
                "annual_income": round(annual_income, 2),
                "value": round(value, 2),
                "yield": summary.dividend_yield,
                "currency": summary.currency,
            })
            total_income += annual_income
            total_value += value
        except ValueError as e:
            logger.warning("Skipping %s: %s", ticker, e)
            result_holdings.append({
                "ticker": ticker.upper(),
                "name": ticker.upper(),
                "shares": shares,
                "error": str(e),
            })

    weighted_yield = (total_income / total_value * 100) if total_value > 0 else 0.0

    return PortfolioIncomeProjection(
        total_annual_income=round(total_income, 2),
        total_portfolio_value=round(total_value, 2),
        weighted_yield=round(weighted_yield, 2),
        holdings=result_holdings,
    )


def _compute_dividend_cagr(
    history: List[DividendPayment],
    max_years: Optional[int] = None,
) -> Optional[float]:
    """
    Compute compound annual growth rate of dividends.

    Groups dividends by calendar year, filters out partial/startup years
    (years with fewer payments than the mode), then calculates CAGR.

    Args:
        history: List of dividend payments.
        max_years: If set, only use the most recent N full years.

    Returns None if fewer than 2 qualifying years of data.
    """
    if not history:
        return None

    # Group by calendar year: total amount and payment count
    by_year: dict[int, dict] = {}
    for d in history:
        yr = d.ex_date.year
        if yr not in by_year:
            by_year[yr] = {"total": 0.0, "count": 0}
        by_year[yr]["total"] += d.amount
        by_year[yr]["count"] += 1

    current_year = date.today().year

    # Determine expected payment frequency (mode of counts, excluding current year)
    counts = [v["count"] for yr, v in by_year.items() if yr < current_year]
    if not counts:
        return None
    expected_freq = max(set(counts), key=counts.count)

    # Keep only years with the expected number of payments (filters startup/partial years)
    # Also exclude current year (incomplete)
    qualifying = sorted(
        yr for yr, v in by_year.items()
        if yr < current_year and v["count"] >= expected_freq
    )

    if max_years and len(qualifying) > max_years:
        qualifying = qualifying[-max_years:]

    if len(qualifying) < 2:
        return None

    earliest = by_year[qualifying[0]]["total"]
    latest = by_year[qualifying[-1]]["total"]
    n_years = qualifying[-1] - qualifying[0]

    if earliest <= 0 or n_years == 0:
        return None

    cagr = ((latest / earliest) ** (1 / n_years) - 1) * 100
    return cagr


@dataclass
class TickerSearchResult:
    """Single autocomplete result."""
    symbol: str
    name: str
    exchange: str
    type: str  # EQUITY, ETF, etc.


_YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"


def search_tickers(query: str, limit: int = 8) -> List[TickerSearchResult]:
    """
    Search for tickers using Yahoo Finance autocomplete.

    Returns up to `limit` results matching the query.
    """
    if not query or len(query.strip()) < 1:
        return []

    try:
        resp = requests.get(
            _YAHOO_SEARCH_URL,
            params={
                "q": query,
                "quotesCount": limit,
                "newsCount": 0,
                "listsCount": 0,
                "enableFuzzyQuery": False,
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("Ticker search failed for '%s': %s", query, e)
        return []

    results = []
    for q in data.get("quotes", []):
        qtype = q.get("quoteType", "")
        if qtype not in ("EQUITY", "ETF", "MUTUALFUND"):
            continue
        results.append(TickerSearchResult(
            symbol=q.get("symbol", ""),
            name=q.get("shortname") or q.get("longname") or "",
            exchange=q.get("exchange", ""),
            type=qtype,
        ))

    return results[:limit]
