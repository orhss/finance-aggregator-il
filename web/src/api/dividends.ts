import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from './client'
import type {
  DividendSummary,
  DripCompareRequest,
  DripCompareResponse,
  DripProjection,
  DripRequest,
  HoldingRequest,
  PortfolioIncome,
  TickerSearchResult,
} from '@/types/dividends'

const dividendKeys = {
  summary: (ticker: string) => ['dividends', 'summary', ticker] as const,
  search: (q: string) => ['dividends', 'search', q] as const,
  drip: (req: DripRequest) => ['dividends', 'drip', req] as const,
  portfolio: () => ['dividends', 'portfolio'] as const,
}

export function useTickerSearch(query: string) {
  return useQuery({
    queryKey: dividendKeys.search(query),
    queryFn: () =>
      apiClient
        .get<TickerSearchResult[]>('/dividends/search', { params: { q: query, limit: 8 } })
        .then((r) => r.data),
    enabled: query.length >= 1,
    staleTime: 60_000,
  })
}

export function useDividendSummary(ticker: string | null) {
  return useQuery({
    queryKey: dividendKeys.summary(ticker ?? ''),
    queryFn: () =>
      apiClient.get<DividendSummary>(`/dividends/summary/${ticker}`).then((r) => r.data),
    enabled: !!ticker,
  })
}

export function useDripProjection() {
  return useMutation({
    mutationFn: (req: DripRequest) =>
      apiClient.post<DripProjection>('/dividends/drip', req, { timeout: 30_000 }).then((r) => r.data),
  })
}

export function useDripCompare() {
  return useMutation({
    mutationFn: (req: DripCompareRequest) =>
      apiClient
        .post<DripCompareResponse>('/dividends/drip-compare', req, { timeout: 60_000 })
        .then((r) => r.data),
  })
}

export function usePortfolioIncome() {
  return useMutation({
    mutationFn: (holdings: HoldingRequest[]) =>
      apiClient
        .post<PortfolioIncome>('/dividends/portfolio-income', { holdings }, { timeout: 45_000 })
        .then((r) => r.data),
  })
}
