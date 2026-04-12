export interface DividendPayment {
  ex_date: string
  amount: number
}

export interface DividendSummary {
  ticker: string
  name: string
  currency: string
  current_price: number
  annual_dividend: number
  dividend_yield: number
  growth_rate_5y: number | null
  growth_rate_all: number | null
  payment_frequency: number
  history: DividendPayment[]
}

export interface DripRequest {
  ticker: string
  initial_shares: number
  years?: number
  dividend_growth_rate?: number | null
  price_growth_rate?: number
}

export interface DripPoint {
  year: number
  shares: number
  share_price: number
  annual_dividend_income: number
  annual_tax: number
  annual_dividend_after_tax: number
  portfolio_value: number
  total_dividends_received: number
  total_tax_paid: number
}

export interface DripProjection {
  ticker: string
  initial_shares: number
  initial_investment: number
  dividend_growth_rate: number
  price_growth_rate: number
  years: number
  points: DripPoint[]
}

export interface DripCompareTickerInput {
  ticker: string
  dividend_growth_rate?: number | null
  price_growth_rate: number
  share_price_override?: number | null
}

export interface DripCompareRequest {
  tickers: DripCompareTickerInput[]
  initial_shares: number
  years?: number
  annual_contribution?: number
  dividend_tax_rate?: number
}

export interface DripCompareItem {
  ticker: string
  name: string
  initial_share_price: number
  dividend_yield: number
  dividend_growth_rate: number
  price_growth_rate: number
  initial_investment: number
  ending_balance: number
  total_return_pct: number
  avg_annual_return_pct: number
  final_annual_income: number
  final_annual_income_after_tax: number
  total_dividends_paid: number
  total_tax_paid: number
  yield_on_cost: number
  points: DripPoint[]
  error?: string
}

export interface DripCompareResponse {
  initial_shares: number
  years: number
  results: DripCompareItem[]
}

export interface TickerSearchResult {
  symbol: string
  name: string
  exchange: string
  type: string
}

export interface HoldingRequest {
  ticker: string
  shares: number
}

export interface HoldingIncome {
  ticker: string
  name: string
  shares: number
  price?: number
  annual_dividend_per_share?: number
  annual_income?: number
  value?: number
  yield_pct?: number
  currency?: string
  error?: string
}

export interface PortfolioIncome {
  total_annual_income: number
  total_portfolio_value: number
  weighted_yield: number
  holdings: HoldingIncome[]
}
