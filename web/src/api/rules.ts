import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { ApplyRulesResult, Rule, RuleCreate } from '@/types/rule'

export function useRules() {
  return useQuery({
    queryKey: ['rules'],
    queryFn: () => apiClient.get<Rule[]>('/rules').then((r) => r.data),
  })
}

export function useCreateRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: RuleCreate) => apiClient.post<Rule>('/rules', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules'] }),
  })
}

export function useDeleteRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (pattern: string) =>
      apiClient.delete(`/rules/${encodeURIComponent(pattern)}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rules'] }),
  })
}

export function useApplyRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { dry_run?: boolean; account_id?: number; rule_indices?: number[] }) =>
      apiClient.post<ApplyRulesResult>('/rules/apply', body).then((r) => r.data),
    onSuccess: (_, vars) => {
      if (!vars.dry_run) {
        qc.invalidateQueries({ queryKey: ['transactions'] })
      }
    },
  })
}
