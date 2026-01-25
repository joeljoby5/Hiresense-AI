import { useQuery } from '@tanstack/react-query'
import { ApiError, request } from '../../services/api'

export interface Account {
  profile: { id: string; email: string; display_name: string }
  csrf_token: string
}

export const accountKey = ['account'] as const

export function useAccount() {
  return useQuery({
    queryKey: accountKey,
    queryFn: async ({ signal }) => {
      try { return await request<Account>('/auth/me', 'GET', undefined, signal) }
      catch (error) {
        if (error instanceof ApiError && error.status === 401) return null
        throw error
      }
    },
  })
}
