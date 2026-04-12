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
  es.addEventListener('ping', handle('ping'))

  // Handle both server-sent "error" events and native connection errors.
  // Native errors (connection drop) have no .data — let EventSource reconnect
  // to the same endpoint; the server will replay cached lines instead of
  // starting a duplicate subprocess.
  es.addEventListener('error', (e) => {
    const me = e as MessageEvent
    if (me.data) {
      // Server-sent error event with payload
      handle('error')(me)
    }
    // Native connection error — EventSource auto-reconnects, server handles it
  })

  return es
}
