export interface SyncHistory {
  id: number
  sync_type: string
  institution: string | null
  status: string
  started_at: string
  completed_at: string | null
  records_added: number
  records_updated: number
  error_message: string | null
}

export interface SyncProgress {
  type: 'progress' | 'success' | 'error' | 'ping'
  message: string
  institution?: string
  data?: Record<string, unknown>
}
