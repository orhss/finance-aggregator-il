export interface PortfolioProgressionPoint {
  date: string
  series: string
  total_amount: number
  profit_loss: number | null
}

export interface PortfolioProgression {
  points: PortfolioProgressionPoint[]
  series_names: string[]
}

export interface PnLSummaryItem {
  account_id: number
  label: string
  institution: string
  account_type: string
  total_amount: number
  profit_loss: number | null
  profit_loss_percentage: number | null
}
