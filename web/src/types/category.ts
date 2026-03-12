export interface CategoryMapping {
  id: number
  provider: string
  raw_category: string
  unified_category: string
}

export interface MerchantMapping {
  id: number
  pattern: string
  category: string
  provider: string | null
  match_type: string
}

export interface UnmappedCategory {
  provider: string
  raw_category: string
  count: number
  sample_merchants: string[]
}

export interface MerchantSuggestion {
  merchant_pattern: string
  provider: string
  count: number
  total_amount: number
  transaction_ids: number[]
  sample_descriptions: string[]
}
