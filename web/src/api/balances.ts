import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'
import type { PnLSummaryItem, PortfolioProgression } from '@/types/balance'

export const balanceKeys = {
  portfolioByType: (params?: object) => ['balances', 'progression', 'by-type', params] as const,
  portfolioByAccount: (params?: object) => ['balances', 'progression', 'by-account', params] as const,
  pnlSummary: ['balances', 'pnl-summary'] as const,
}

export function usePortfolioByType(params?: { from_date?: string; to_date?: string }) {
  return useQuery({
    queryKey: balanceKeys.portfolioByType(params),
    queryFn: () =>
      apiClient.get<PortfolioProgression>('/balances/progression/by-type', { params }).then((r) => r.data),
  })
}

export function usePortfolioByAccount(params?: { from_date?: string; to_date?: string }) {
  return useQuery({
    queryKey: balanceKeys.portfolioByAccount(params),
    queryFn: () =>
      apiClient.get<PortfolioProgression>('/balances/progression/by-account', { params }).then((r) => r.data),
  })
}

export function usePnLSummary() {
  return useQuery({
    queryKey: balanceKeys.pnlSummary,
    queryFn: () => apiClient.get<PnLSummaryItem[]>('/balances/pnl-summary').then((r) => r.data),
  })
}
