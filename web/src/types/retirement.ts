/**
 * Types for the retirement calculator UI.
 */

// ==================== Config Types ====================

export interface PersonConfig {
  name: string
  dob: string // YYYY-MM-DD
  gender: 'male' | 'female'
}

export interface CashFlowConfig {
  amount: number
  rise: number
  description: string
  start: string // 'now' | 'fire' | 'forever' | age string
  end: string
  type?: 'one_time'
  start_date?: string // YYYY-MM-DD for one-time or date-based start
  end_date?: string // YYYY-MM-DD for date-based end
  person?: number
  enabled?: boolean // undefined = enabled (backward compatible)
}

export interface PortfolioConfig {
  designation: 'withdraw' | 'goal'
  type: 'portfolio' | 'kaspit'
  balance: number
  interest: number
  fee: number
  profit_fraction: number
  withdrawal_method?: 'fifo' | 'flat'
  goal?: number
  description?: string // UI-only label, ignored by Python parser
  enabled?: boolean // undefined = enabled (backward compatible)
}

export interface PensionConfig {
  balance: number
  deposit: number
  fee1: number
  fee2: number
  interest: number
  tactics: '60' | '67' | '60-67'
  mukeret_pct: number
  end: string
  person: number
  description?: string // UI-only label, ignored by Python parser
  enabled?: boolean // undefined = enabled (backward compatible)
}

export interface KerenConfig {
  balance: number
  deposit: number
  interest: number
  type: string
  fee: number
  end: string
  description?: string // UI-only label, ignored by Python parser
  enabled?: boolean // undefined = enabled (backward compatible)
}

export interface RetirementConfig {
  mode: string
  max_retire_age: number
  retire_rule: number
  withdrawal_order: 'prati' | 'hishtalmut'
  cash_buffer: number
  balance: number
  end_age: number
  start_date?: string
  persons: PersonConfig[]
  incomes: CashFlowConfig[]
  expenses: CashFlowConfig[]
  portfolios: PortfolioConfig[]
  pensions: PensionConfig[]
  kerens: KerenConfig[]
}

// ==================== Response Types ====================

export interface SimulationResponse {
  status: 'success' | 'impossible'
  summary: SimulationSummary
  monthly: MonthlyRow[]
  milestones: Milestone[]
  persons: string[]
}

export interface SimulationSummary {
  fire_age: number
  fire_date: string
  fire_month_index: number
  years_to_fire: number
  min_nw: number
  min_nw_age: number
  end_nw: number
  end_age: number
  portfolio_depletion_age: number | null
  pension_start_ages: number[]
  old_age_start_ages: number[]
  withdrawal_rate_at_fire: number
}

export interface MonthlyRow {
  month: number
  age: number
  date: string
  // Asset values
  net_worth: number
  portfolio: number
  kh_values: number[]
  pension_values: number[]
  kaspit: number
  checking: number
  // Flows
  income: number
  expenses: number
  goals: number
  deposit: number
  withdrawal_portfolio: number
  withdrawal_kh: number[]
  // Pension income (per person)
  pension_mukeret: number[]
  pension_mazka: number[]
  old_age: number[]
  // Tax (per person)
  income_tax: number[]
  bituach_leumi: number[]
  portfolio_tax: number
}

export interface Milestone {
  age: number // The relevant person's actual age
  chart_age?: number // Primary person's age (for chart X-axis positioning)
  date: string
  type:
    | 'fire'
    | 'pension_conversion'
    | 'old_age_start'
    | 'portfolio_depleted'
    | 'kh_depleted'
    | 'one_time_expense'
  label: string
  person?: string
  amount?: number
}

export interface Scenario {
  id: number
  name: string
  config: Record<string, unknown>
}

export interface ScenarioCreate {
  name: string
  config: Record<string, unknown>
}

export interface ScenarioUpdate {
  name?: string
  config?: Record<string, unknown>
}

export type ScenarioResult =
  | { status: 'ok'; data: SimulationResponse }
  | { status: 'error'; message: string }
