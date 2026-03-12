import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { CountResponse } from '@/types/common'
import type { Tag, TagStats } from '@/types/tag'

const tagKeys = {
  all: ['tags'] as const,
  list: ['tags', 'list'] as const,
  stats: ['tags', 'stats'] as const,
  untaggedCount: ['tags', 'untagged-count'] as const,
}

export function useTags() {
  return useQuery({
    queryKey: tagKeys.list,
    queryFn: () => apiClient.get<Tag[]>('/tags').then((r) => r.data),
  })
}

export function useTagStats() {
  return useQuery({
    queryKey: tagKeys.stats,
    queryFn: () => apiClient.get<TagStats[]>('/tags/stats').then((r) => r.data),
  })
}

export function useUntaggedCount() {
  return useQuery({
    queryKey: tagKeys.untaggedCount,
    queryFn: () => apiClient.get<CountResponse>('/tags/untagged-count').then((r) => r.data.count),
  })
}

export function useTagTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ transactionId, tags }: { transactionId: number; tags: string[] }) =>
      apiClient.post<CountResponse>(`/tags/${transactionId}/tag`, { tags }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: tagKeys.all })
    },
  })
}

export function useUntagTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ transactionId, tags }: { transactionId: number; tags: string[] }) =>
      apiClient.post<CountResponse>(`/tags/${transactionId}/untag`, { tags }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: tagKeys.all })
    },
  })
}

export function useDeleteTag() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) => apiClient.delete(`/tags/${encodeURIComponent(name)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: tagKeys.all }),
  })
}
