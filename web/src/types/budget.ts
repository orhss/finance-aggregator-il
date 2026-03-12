export interface Budget {
  id: number
  year: number
  month: number
  amount: number
}

export interface BudgetProgress {
  year: number
  month: number
  budget: number | null
  spent: number
  remaining: number | null
  percent: number | null
  percent_actual: number | null
  is_over_budget: boolean | null
}
