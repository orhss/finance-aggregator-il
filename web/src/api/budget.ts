import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { Budget, BudgetProgress } from '@/types/budget'

const budgetKeys = {
  all: ['budget'] as const,
  progress: (year?: number, month?: number) => ['budget', 'progress', year, month] as const,
  current: ['budget', 'current'] as const,
}

export function useBudgetProgress(year?: number, month?: number) {
  return useQuery({
    queryKey: budgetKeys.progress(year, month),
    queryFn: () =>
      apiClient.get<BudgetProgress>('/budget/progress', { params: { year, month } }).then((r) => r.data),
  })
}

export function useCurrentBudget() {
  return useQuery({
    queryKey: budgetKeys.current,
    queryFn: () => apiClient.get<Budget | null>('/budget').then((r) => r.data),
  })
}

export function useSetBudget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ amount, year, month }: { amount: number; year?: number; month?: number }) =>
      apiClient.put<Budget>('/budget', { amount }, { params: { year, month } }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: budgetKeys.all }),
  })
}
