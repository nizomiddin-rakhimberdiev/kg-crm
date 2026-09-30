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

/** To'lov qabul qilish ekranining bitta qatori (docs/04 §9.7). */
export interface BoardRow {
  child_id: string
  child_name: string
  group_name: string
  invoice_id: string | null
  invoice_number: string
  charged: string
  paid: string
  outstanding: string
  state: 'unpaid' | 'partial' | 'paid' | 'no_invoice'
  /** Manfiy = avans bor: kassir buni to'lovdan OLDIN ko'rishi kerak. */
  balance: string
}

export interface BoardSummary {
  period_year: number
  period_month: number
  charged: string
  paid: string
  outstanding: string
  children: number
  with_invoice: number
  without_invoice: number
  debtors: number
}

export const paymentsApi = {
  /**
   * Kassirning ekrani: shu oyda qaysi bola qancha to'lashi kerak.
   *
   * Qidiruv, filtr va sahifalash SERVERDA — ekran bog'chaning
   * kattaligiga bog'liq emas. Ilgari bu ro'yxat hisob-fakturalardan
   * `page_size` siz olinar, ya'ni 25 tadan keyingi bolalar umuman
   * ko'rinmasdi.
   */
  board: (params: {
    period_year: number
    period_month: number
    search?: string
    status?: string
    page?: number
  }) => api.list<BoardRow>('/payments/board', { page_size: 100, ...params }),

  boardSummary: (periodYear: number, periodMonth: number) =>
    api.get<BoardSummary>('/payments/board-summary', {
      period_year: periodYear,
      period_month: periodMonth,
    }),

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
