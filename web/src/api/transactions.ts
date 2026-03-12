import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { PaginatedResponse } from '@/types/common'
import type { Transaction, TransactionFilters, TransactionUpdate } from '@/types/transaction'

export const txnKeys = {
  all: ['transactions'] as const,
  list: (filters?: TransactionFilters) => [...txnKeys.all, 'list', filters] as const,
  detail: (id: number) => [...txnKeys.all, id] as const,
  count: (filters?: object) => [...txnKeys.all, 'count', filters] as const,
}

export function useTransactions(filters?: TransactionFilters) {
  return useQuery({
    queryKey: txnKeys.list(filters),
    queryFn: () =>
      apiClient.get<PaginatedResponse<Transaction>>('/transactions', { params: filters }).then((r) => r.data),
  })
}

export function useTransaction(id: number) {
  return useQuery({
    queryKey: txnKeys.detail(id),
    queryFn: () => apiClient.get<Transaction>(`/transactions/${id}`).then((r) => r.data),
    enabled: id > 0,
  })
}

export function useUpdateTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: TransactionUpdate }) =>
      apiClient.patch<Transaction>(`/transactions/${id}`, body).then((r) => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: txnKeys.all })
      qc.setQueryData(txnKeys.detail(data.id), data)
    },
  })
}
