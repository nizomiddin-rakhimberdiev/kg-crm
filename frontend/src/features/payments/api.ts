import { api } from '@/lib/api/client'
import type {
  BillingRunResult,
  ChildStatement,
  DailyCashSummary,
  DebtorList,
  Invoice,
  Payment,
  TariffPlan,
} from '@/lib/api/types'

export const tariffsApi = {
  list: () => api.list<TariffPlan>('/tariffs'),
  create: (payload: { name: string; amount: string }) =>
    api.post<TariffPlan>('/tariffs', payload),
  remove: (id: string) => api.delete(`/tariffs/${id}`),
}

export const invoicesApi = {
  list: (params?: Record<string, unknown>) => api.list<Invoice>('/invoices', params),

  generate: (periodYear: number, periodMonth: number) =>
    api.post<BillingRunResult>('/invoices/generate', {
      period_year: periodYear,
      period_month: periodMonth,
    }),

  cancel: (id: string, reason: string) =>
    api.post<Invoice>(`/invoices/${id}/cancel`, { reason }),
}

export const discountsApi = {
  create: (payload: {
    child_id: string
    discount_type: 'percent' | 'fixed'
    value: string
    valid_from: string
    reason?: string
  }) => api.post('/discounts', payload),
}

export const paymentsApi = {
  list: (params?: Record<string, unknown>) => api.list<Payment>('/payments', params),

  record: (payload: {
    child_id: string
    invoice_id?: string | null
    amount: string
    method: string
    reference?: string
  }) => api.post<Payment>('/payments', payload),

  reverse: (id: string, reason: string) =>
    api.post<Payment>(`/payments/${id}/reverse`, { reason }),

  dailySummary: (date?: string) =>
    api.get<DailyCashSummary>('/payments/daily-summary', date ? { date } : undefined),
}

export const debtorsApi = {
  list: (params?: { overdue?: string; min_amount?: string }) =>
    api.get<DebtorList>('/debtors', params),
  statement: (childId: string) => api.get<ChildStatement>(`/debtors/${childId}`),
}
