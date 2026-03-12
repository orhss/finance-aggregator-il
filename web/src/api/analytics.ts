import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'
import type {
  CardSpendingItem,
  CategoryBreakdownItem,
  CategoryTrends,
  MonthlySummary,
  Stats,
  TagBreakdownItem,
  TrendPoint,
} from '@/types/analytics'

export const analyticsKeys = {
  stats: ['analytics', 'stats'] as const,
  monthly: (year: number, month: number) => ['analytics', 'monthly', year, month] as const,
  trends: (params?: object) => ['analytics', 'trends', params] as const,
  categories: (params?: object) => ['analytics', 'categories', params] as const,
  categoryTrends: (params?: object) => ['analytics', 'category-trends', params] as const,
  tags: (params?: object) => ['analytics', 'tags', params] as const,
  cards: (params?: object) => ['analytics', 'cards', params] as const,
}

export function useStats() {
  return useQuery({
    queryKey: analyticsKeys.stats,
    queryFn: () => apiClient.get<Stats>('/analytics/stats').then((r) => r.data),
  })
}

export function useMonthlySummary(year: number, month: number) {
  return useQuery({
    queryKey: analyticsKeys.monthly(year, month),
    queryFn: () => apiClient.get<MonthlySummary>(`/analytics/monthly?year=${year}&month=${month}`).then((r) => r.data),
  })
}

export function useMonthlyTrends(params?: {
  months?: number
  tag?: string
  card_last4?: string
  include_current?: boolean
}) {
  return useQuery({
    queryKey: analyticsKeys.trends(params),
    queryFn: () => apiClient.get<TrendPoint[]>('/analytics/trends', { params }).then((r) => r.data),
  })
}

export function useCategoryBreakdown(params?: { from_date?: string; to_date?: string }) {
  return useQuery({
    queryKey: analyticsKeys.categories(params),
    queryFn: () =>
      apiClient.get<CategoryBreakdownItem[]>('/analytics/categories', { params }).then((r) => r.data),
  })
}

export function useCategoryTrends(params?: { months?: number; top_n?: number }) {
  return useQuery({
    queryKey: analyticsKeys.categoryTrends(params),
    queryFn: () => apiClient.get<CategoryTrends>('/analytics/category-trends', { params }).then((r) => r.data),
  })
}

export function useTagBreakdown(params?: { from_date?: string; to_date?: string }) {
  return useQuery({
    queryKey: analyticsKeys.tags(params),
    queryFn: () => apiClient.get<TagBreakdownItem[]>('/analytics/tags', { params }).then((r) => r.data),
  })
}

export function useCardSpending(params?: { months?: number }) {
  return useQuery({
    queryKey: analyticsKeys.cards(params),
    queryFn: () => apiClient.get<CardSpendingItem[]>('/analytics/cards', { params }).then((r) => r.data),
  })
}
