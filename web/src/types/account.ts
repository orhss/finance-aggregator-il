export interface BalanceSummary {
  total_amount: number
  available: number | null
  profit_loss: number | null
  profit_loss_percentage: number | null
  currency: string
  balance_date: string | null
}

export interface Account {
  id: number
  account_type: string
  institution: string
  account_number: string
  account_name: string | null
  card_unique_id: string | null
  is_active: boolean
  created_at: string
  last_synced_at: string | null
  latest_balance: BalanceSummary | null
}

export interface AccountSummary {
  total_accounts: number
  by_type: Record<string, number>
  by_institution: Record<string, number>
  total_balance: number
}
