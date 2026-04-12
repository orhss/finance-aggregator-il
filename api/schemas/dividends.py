"""Pydantic schemas for the dividend calculator API."""

from typing import List, Optional

from pydantic import BaseModel


class DividendPaymentResponse(BaseModel):
    ex_date: str
    amount: float


class DividendSummaryResponse(BaseModel):
    ticker: str
    name: str
    currency: str
    current_price: float
    annual_dividend: float
    dividend_yield: float
    growth_rate_5y: Optional[float] = None
    growth_rate_all: Optional[float] = None
    payment_frequency: int
    history: List[DividendPaymentResponse]


class DripRequest(BaseModel):
    ticker: str
    initial_shares: float
    years: int = 20
    dividend_growth_rate: Optional[float] = None
    price_growth_rate: float = 7.0
    annual_contribution: float = 0.0


class DripPointResponse(BaseModel):
    year: int
    shares: float
    share_price: float
    annual_dividend_income: float
    annual_tax: float
    annual_dividend_after_tax: float
    portfolio_value: float
    total_dividends_received: float
    total_tax_paid: float


class DripProjectionResponse(BaseModel):
    ticker: str
    initial_shares: float
    initial_investment: float
    dividend_growth_rate: float
    price_growth_rate: float
    years: int
    points: List[DripPointResponse]


class DripCompareTickerInput(BaseModel):
    ticker: str
    dividend_growth_rate: Optional[float] = None  # None = use historical CAGR
    price_growth_rate: float = 7.0
    share_price_override: Optional[float] = None  # None = use current market price


class DripCompareRequest(BaseModel):
    tickers: List[DripCompareTickerInput]
    initial_shares: float
    years: int = 20
    annual_contribution: float = 0.0
    dividend_tax_rate: float = 0.0


class DripCompareItem(BaseModel):
    ticker: str
    name: str
    initial_share_price: float
    dividend_yield: float
    dividend_growth_rate: float
    price_growth_rate: float
    initial_investment: float
    # Summary stats
    ending_balance: float
    total_return_pct: float
    avg_annual_return_pct: float
    final_annual_income: float
    final_annual_income_after_tax: float
    total_dividends_paid: float
    total_tax_paid: float
    yield_on_cost: float
    points: List[DripPointResponse]
    error: Optional[str] = None


class DripCompareResponse(BaseModel):
    initial_shares: float
    years: int
    results: List[DripCompareItem]


class TickerSearchResultResponse(BaseModel):
    symbol: str
    name: str
    exchange: str
    type: str


class HoldingRequest(BaseModel):
    ticker: str
    shares: float


class PortfolioIncomeRequest(BaseModel):
    holdings: List[HoldingRequest]


class HoldingIncomeResponse(BaseModel):
    ticker: str
    name: str
    shares: float
    price: Optional[float] = None
    annual_dividend_per_share: Optional[float] = None
    annual_income: Optional[float] = None
    value: Optional[float] = None
    yield_pct: Optional[float] = None
    currency: Optional[str] = None
    error: Optional[str] = None


class PortfolioIncomeResponse(BaseModel):
    total_annual_income: float
    total_portfolio_value: float
    weighted_yield: float
    holdings: List[HoldingIncomeResponse]
