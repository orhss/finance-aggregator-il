import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { Scenario, ScenarioCreate, ScenarioUpdate, SimulationResponse } from '@/types/retirement'

const SCENARIOS_KEY = ['retirement', 'scenarios'] as const

export function useSimulate() {
  return useMutation({
    mutationFn: (config: Record<string, unknown>) =>
      apiClient
        .post<SimulationResponse>('/retirement/simulate', config, { timeout: 45_000 })
        .then((r) => r.data),
  })
}

export function useScenarios() {
  return useQuery({
    queryKey: SCENARIOS_KEY,
    queryFn: () => apiClient.get<Scenario[]>('/retirement/scenarios').then((r) => r.data),
  })
}

export function useCreateScenario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ScenarioCreate) =>
      apiClient.post<Scenario>('/retirement/scenarios', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: SCENARIOS_KEY }),
  })
}

export function useUpdateScenario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: ScenarioUpdate & { id: number }) =>
      apiClient.patch<Scenario>(`/retirement/scenarios/${id}`, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: SCENARIOS_KEY }),
  })
}

export function useDeleteScenario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiClient.delete(`/retirement/scenarios/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: SCENARIOS_KEY }),
  })
}
