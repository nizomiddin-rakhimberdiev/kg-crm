import { QueryClient } from '@tanstack/react-query'
import { ApiError } from './types'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Ruxsat, topilmadi va validatsiya xatolarini qayta urinish
        // ma'nosiz — javob o'zgarmaydi, faqat foydalanuvchi kutadi.
        if (error instanceof ApiError) {
          const noRetry: string[] = [
            'AUTHENTICATION_REQUIRED',
            'PERMISSION_DENIED',
            'NOT_FOUND',
            'VALIDATION_ERROR',
            'SUBSCRIPTION_INACTIVE',
            // 422 — biznes qoidasi: javob qayta so'raganda o'zgarmaydi
            // (audit 2026-11-12: obunasiz billing 4 × 3 = 12 so'rov).
            'BUSINESS_RULE_VIOLATION',
          ]
          if (noRetry.includes(error.code)) return false
        }
        return failureCount < 2
      },
    },
    mutations: { retry: false },
  },
})
