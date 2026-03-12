import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'
import type { Account, AccountSummary } from '@/types/account'

export const accountKeys = {
  all: ['accounts'] as const,
  list: (params?: object) => [...accountKeys.all, 'list', params] as const,
  detail: (id: number) => [...accountKeys.all, id] as const,
  summary: ['accounts', 'summary'] as const,
}

export function useAccounts(params?: { active_only?: boolean; account_type?: string; institution?: string }) {
  return useQuery({
    queryKey: accountKeys.list(params),
    queryFn: () => apiClient.get<Account[]>('/accounts', { params }).then((r) => r.data),
  })
}

export function useAccount(id: number) {
  return useQuery({
    queryKey: accountKeys.detail(id),
    queryFn: () => apiClient.get<Account>(`/accounts/${id}`).then((r) => r.data),
    enabled: id > 0,
  })
}

export function useAccountSummary() {
  return useQuery({
    queryKey: accountKeys.summary,
    queryFn: () => apiClient.get<AccountSummary>('/accounts/summary').then((r) => r.data),
  })
}
