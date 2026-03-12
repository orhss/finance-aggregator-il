import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { LoginRequest, TokenResponse, AuthStatus } from '@/types/auth'

export const authKeys = {
  status: ['auth', 'status'] as const,
}

export function useAuthStatus() {
  return useQuery({
    queryKey: authKeys.status,
    queryFn: () => apiClient.get<AuthStatus>('/auth/status').then((r) => r.data),
  })
}

export function useLogin() {
  return useMutation({
    mutationFn: (body: LoginRequest) =>
      apiClient.post<TokenResponse>('/auth/login', body).then((r) => r.data),
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
    },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    qc.clear()
  }
}
