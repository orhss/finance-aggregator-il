import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'
import type { SyncHistory, SyncProgress } from '@/types/sync'

const syncKeys = {
  history: (params?: object) => ['sync', 'history', params] as const,
}

export function useSyncHistory(params?: { limit?: number; institution?: string; status?: string }) {
  return useQuery({
    queryKey: syncKeys.history(params),
    queryFn: () => apiClient.get<SyncHistory[]>('/sync/history', { params }).then((r) => r.data),
  })
}

export async function startSync(institution: string, monthsBack?: number): Promise<{ job_id: string }> {
  const { data } = await apiClient.post<{ job_id: string }>(`/sync/${institution}`, {
    months_back: monthsBack ?? null,
  })
  return data
}

/**
 * Returns an EventSource connected to the sync SSE stream.
 * Caller is responsible for closing it.
 */
export function createSyncStream(
  jobId: string,
  onMessage: (event: SyncProgress) => void,
  onClose: (success: boolean) => void
): EventSource {
  const token = localStorage.getItem('access_token')
  const base = import.meta.env.VITE_API_URL || ''
  // SSE with auth header via URL param (EventSource doesn't support custom headers)
  const url = `${base}/sync/stream/${jobId}${token ? `?token=${token}` : ''}`
  const es = new EventSource(url)

  const handle = (type: string) => (e: MessageEvent) => {
    const data = JSON.parse(e.data) as SyncProgress
    onMessage({ ...data, type: type as SyncProgress['type'] })
    if (type === 'success' || type === 'error') {
      es.close()
      onClose(type === 'success')
    }
  }

  es.addEventListener('progress', handle('progress'))
  es.addEventListener('success', handle('success'))
  es.addEventListener('error', handle('error'))
  es.addEventListener('ping', handle('ping'))

  return es
}
