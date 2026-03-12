export interface Transaction {
  id: number
  account_id: number
  transaction_id: string | null
  transaction_date: string
  processed_date: string | null
  description: string
  original_amount: number
  original_currency: string
  charged_amount: number | null
  charged_currency: string | null
  transaction_type: string | null
  status: string | null
  raw_category: string | null
  category: string | null
  user_category: string | null
  effective_category: string | null
  memo: string | null
  installment_number: number | null
  installment_total: number | null
  tags: string[]
  created_at: string
}

export interface TransactionUpdate {
  user_category?: string | null
  memo?: string | null
}

export interface TransactionFilters {
  account_id?: number
  from_date?: string
  to_date?: string
  status?: string
  institution?: string
  category?: string
  search?: string
  tags?: string[]
  untagged_only?: boolean
  limit?: number
  offset?: number
}
