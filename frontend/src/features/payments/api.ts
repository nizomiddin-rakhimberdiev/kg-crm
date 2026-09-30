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
  create: (payload: { name: string; amount: string }) => api.post<TariffPlan>('/tariffs', payload),
  remove: (id: string) => api.delete(`/tariffs/${id}`),
}

export const invoicesApi = {
  list: (params?: Record<string, unknown>) => api.list<Invoice>('/invoices', params),

  generate: (periodYear: number, periodMonth: number) =>
    api.post<BillingRunResult>('/invoices/generate', {
      period_year: periodYear,
      period_month: periodMonth,
    }),

  cancel: (id: string, reason: string) => api.post<Invoice>(`/invoices/${id}/cancel`, { reason }),
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

  /**
   * To'lovni qayd etadi.
   *
   * `idempotencyKey` — bitta FOYDALANUVCHI HARAKATINI bildiradi, bitta
   * so'rovni emas. Kassir tugmani ikki marta bossa yoki tarmoq so'rovni
   * qayta yuborsa, server o'sha kalitni ko'rib mavjud to'lovni
   * qaytaradi — ikkinchi to'lov yozilmaydi (P1-003).
   *
   * Chaqiruvchi kalitni FORMA ochilganda yaratadi va qayta urinishda
   * O'ZGARTIRMAYDI. Har safar yangisi yaratilsa, himoyaning ma'nosi
   * qolmaydi.
   */
  record: (
    payload: {
      child_id: string
      invoice_id?: string | null
      amount: string
      method: string
      reference?: string
    },
    idempotencyKey?: string,
  ) =>
    api.post<Payment>(
      '/payments',
      payload,
      idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    ),

  /**
   * Bitta kassir harakati — bir nechta usul (docs/03 §13.5a).
   * Ortiqcha summa rad etilmaydi: u avans bo'lib yoziladi.
   */
  recordBatch: (
    payload: {
      child_id: string
      invoice_id?: string | null
      lines: Array<{ method: string; amount: string; reference?: string }>
    },
    idempotencyKey?: string,
  ) =>
    api.post<Payment[]>(
      '/payments/batch',
      payload,
      idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    ),

  reverse: (id: string, reason: string) => api.post<Payment>(`/payments/${id}/reverse`, { reason }),

  dailySummary: (date?: string) =>
    api.get<DailyCashSummary>('/payments/daily-summary', date ? { date } : undefined),
}

export const debtorsApi = {
  list: (params?: { overdue?: string; min_amount?: string }) =>
    api.get<DebtorList>('/debtors', params),
  statement: (childId: string) => api.get<ChildStatement>(`/debtors/${childId}`),
}
