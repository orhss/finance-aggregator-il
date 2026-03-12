export interface Rule {
  pattern: string
  match_type: string
  category: string | null
  tags: string[]
  remove_tags: string[]
  description: string | null
  enabled: boolean
}

export interface RuleCreate {
  pattern: string
  match_type?: string
  category?: string | null
  tags?: string[]
  remove_tags?: string[]
  description?: string | null
}

export interface ApplyRulesResult {
  processed: number
  modified: number
  details: Array<{
    id: number
    description: string
    category: string | null
    tags: string[]
    remove_tags: string[]
    matched_rules: string[]
  }>
  message?: string | null
}
