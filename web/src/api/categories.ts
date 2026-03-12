import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type {
  CategoryMapping,
  MerchantMapping,
  MerchantSuggestion,
  UnmappedCategory,
} from '@/types/category'

// ── Provider mappings ────────────────────────────────────────────────────────

export function useCategoryMappings(provider?: string) {
  return useQuery({
    queryKey: ['category-mappings', provider],
    queryFn: () =>
      apiClient
        .get<CategoryMapping[]>('/categories/mappings', { params: provider ? { provider } : {} })
        .then((r) => r.data),
  })
}

export function useUnmappedCategories() {
  return useQuery({
    queryKey: ['unmapped-categories'],
    queryFn: () => apiClient.get<UnmappedCategory[]>('/categories/unmapped').then((r) => r.data),
  })
}

export function useAddCategoryMapping() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { provider: string; raw_category: string; unified_category: string }) =>
      apiClient.post<CategoryMapping>('/categories/mappings', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['category-mappings'] })
      qc.invalidateQueries({ queryKey: ['unmapped-categories'] })
    },
  })
}

export function useDeleteCategoryMapping() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ provider, raw_category }: { provider: string; raw_category: string }) =>
      apiClient.delete(`/categories/mappings/${provider}/${encodeURIComponent(raw_category)}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['category-mappings'] })
    },
  })
}

export function useApplyMappings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (provider?: string) =>
      apiClient.post('/categories/apply', {}, { params: provider ? { provider } : {} }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
    },
  })
}

// ── Merchant mappings ────────────────────────────────────────────────────────

export function useMerchantMappings(provider?: string) {
  return useQuery({
    queryKey: ['merchant-mappings', provider],
    queryFn: () =>
      apiClient
        .get<MerchantMapping[]>('/categories/merchants', { params: provider ? { provider } : {} })
        .then((r) => r.data),
  })
}

export function useMerchantSuggestions(minCount = 2) {
  return useQuery({
    queryKey: ['merchant-suggestions', minCount],
    queryFn: () =>
      apiClient
        .get<MerchantSuggestion[]>('/categories/suggest', { params: { min_count: minCount } })
        .then((r) => r.data),
  })
}

export function useBulkAssignCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { pattern: string; category: string; provider?: string; save_mapping?: boolean }) =>
      apiClient.post('/categories/bulk-assign', body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['merchant-mappings'] })
      qc.invalidateQueries({ queryKey: ['merchant-suggestions'] })
    },
  })
}
