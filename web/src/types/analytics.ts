export interface Stats {
  total_accounts: number
  total_transactions: number
  pending_transactions: number
  total_balance: number
  last_sync: string | null
}

export interface MonthlySummary {
  year: number
  month: number
  transaction_count: number
  total_amount: number
  total_charged: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  by_account: Record<string, number>
}

export interface TrendPoint {
  year: number
  month: number
  total_amount: number
  transaction_count: number
}

export interface CategoryBreakdownItem {
  category: string
  count: number
  total_amount: number
  avg_amount: number
}

export interface TagBreakdownItem {
  tag: string
  count: number
  total_amount: number
  percentage: number
}

export interface CardSpendingItem {
  last4: string
  total_amount: number
  transaction_count: number
  percentage: number
}

export interface CategoryTrends {
  categories: Record<string, Array<{ year: number; month: number; amount: number }>>
  totals: Record<string, number>
}
