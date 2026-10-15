import { api } from '@/lib/api/client'
import { withBranch } from '@/lib/branchScope'
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
    api.post<TariffPlan>('/tariffs', withBranch(payload)),
  // Tahrirlash (2026-10-14). Yangi summa KEYINGI hisob-fakturadan
  // ishlaydi — chiqarilgan hujjat o'zgarmaydi (Q4).
  update: (id: string, payload: { name: string; amount: string }) =>
    api.patch<TariffPlan>(`/tariffs/${id}`, payload),
  remove: (id: string) => api.delete(`/tariffs/${id}`),
}

export const invoicesApi = {
  list: (params?: Record<string, unknown>) => api.list<Invoice>('/invoices', params),

  generate: (periodYear: number, periodMonth: number) =>
    api.post<BillingRunResult>('/invoices/generate', {
      period_year: periodYear,
      period_month: periodMonth,
    }),

  /**
   * Generatsiya nima qilishini OLDINDAN aytadi — hech narsa yozmaydi.
   *
   * 200 bolali bog'chada "Hisob-faktura chiqarish" bitta bosishda 200 ta
   * moliyaviy hujjat yaratadi va ularni qaytarish uchun har birini
   * alohida bekor qilish kerak.
   */
  previewRun: (periodYear: number, periodMonth: number) =>
    api.post<BillingPreview>('/invoices/preview-run', {
      period_year: periodYear,
      period_month: periodMonth,
    }),

  cancel: (id: string, reason: string) => api.post<Invoice>(`/invoices/${id}/cancel`, { reason }),
}

/** Generatsiya preview'i (`POST /invoices/preview-run`). */
export interface BillingPreviewRow {
  child_id: string
  full_name: string
  group_name: string
  amount: string
  note: string
  advance: string
}

export interface BillingPreview {
  period: string
  will_create: number
  skipped_existing: number
  skipped_no_tariff: string[]
  skipped_next_month: string[]
  total_amount: string
  rows: BillingPreviewRow[]
}

/** Imtiyoz turi (Bosqich 12.2). `sibling` — oiladan avtomatik, qoʻlda kiritilmaydi. */
export type BenefitKind = 'sibling' | 'staff_child' | 'low_income' | 'full' | 'custom'

export interface Benefit {
  id: string
  child_id: string
  child_name: string
  kind: BenefitKind
  discount_type: 'percent' | 'fixed'
  value: string
  /** Amaldagi shart — "50%" yoki "100 000" (sozlamadan). */
  terms: string
  reason: string
  valid_from: string
  valid_to: string | null
  created_by_name: string | null
  created_at: string
}

export interface FamilyMember {
  id: string
  full_name: string
  enrollment_status: string
  is_self: boolean
}

export const benefitsApi = {
  list: (childId: string) => api.list<Benefit>('/discounts', { child: childId, page_size: 100 }),
  create: (payload: {
    child_id: string
    kind: Exclude<BenefitKind, 'sibling'>
    reason: string
    valid_from: string
    valid_to?: string
    discount_type?: 'percent' | 'fixed'
    value?: string
  }) => api.post<Benefit>('/discounts', payload),
  /** Imtiyoz oʻchirilmaydi — tugatiladi, tarix qoladi. */
  end: (id: string, validTo: string) =>
    api.post<Benefit>(`/discounts/${id}/end`, { valid_to: validTo }),
  family: (childId: string) => api.get<FamilyMember[]>(`/children/${childId}/family`),
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
  /** Taqsimlanmagan pul — "bu bolaning kassamizda qancha puli bor". */
  advance: string
}

/** Ochiq hisob-faktura — to'lov oynasidagi taqsimot ko'rinishi uchun. */
export interface OpenInvoice {
  id: string
  number: string
  period: string
  due_date: string
  amount_due: string
  amount_paid: string
  outstanding: string
  is_overdue: boolean
}

/**
 * Bolaning to'liq moliyaviy manzarasi (`GET /ledger/balance?child=`).
 *
 * Uchta raqam ataylab alohida: ular boshqa savollarga javob beradi va
 * teng bo'lishi shart emas. `balance` — oila qancha qarz, `advance` —
 * qo'limizda uning qancha puli bor, `overdue_amount` — shundan qanchasi
 * muddati o'tgan.
 */
export interface ChildBalance {
  child_id: string
  full_name: string
  charged: string
  credited: string
  paid: string
  allocated: string
  advance: string
  balance: string
  outstanding: string
  overdue_amount: string
  overdue_days: number
  oldest_overdue_date: string | null
  open_invoices: OpenInvoice[]
}

/** To'lovlar jurnalining filtri (PLAN 1.8). */
export interface JournalFilters {
  paid_from?: string
  paid_to?: string
  method?: string
  child?: string
  received_by?: string
}

export interface JournalSummary {
  date_from: string
  date_to: string
  count: number
  total: string
  reversed_count: number
  by_method: Array<{ method: string; total: string; count: number }>
}

/** Kvitansiya (`GET /payments/{id}/receipt`, PLAN 1.7). */
export interface Receipt {
  number: string
  paid_at: string
  child: string
  branch: string
  cashier: string
  reversed: boolean
  lines: Array<{ method: string; amount: string; reference: string }>
  total: string
  allocations: Array<{ invoice: string; period: string; amount: string }>
  balance_after: string
  advance_after: string
}

export interface BoardSummary {
  period_year: number
  period_month: number
  /**
   * `null` — bu foydalanuvchiga oyning umumiy pul raqamlari
   * koʻrsatilmaydi (kassir, ADR-30). Doskaning oʻzi ishlayveradi.
   */
  charged: string | null
  paid: string | null
  outstanding: string | null
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
   * Jurnal yig'indisi — SAHIFADAN qat'i nazar.
   *
   * "1–25 / 105" ostida turgan "jami" faqat 25 qatordan hisoblansa,
   * u har doim kam ko'rsatadi.
   */
  journalSummary: (params: JournalFilters) =>
    api.get<JournalSummary>('/payments/journal-summary', params as Record<string, unknown>),

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

  receipt: (id: string) => api.get<Receipt>(`/payments/${id}/receipt`),

  reverse: (id: string, reason: string) => api.post<Payment>(`/payments/${id}/reverse`, { reason }),

  /**
   * Bolaning balansi va ochiq hujjatlari — FIFO tartibida.
   *
   * Kassir oynasidagi taqsimot ko'rinishi aynan shu ro'yxat bo'yicha
   * chiziladi, ya'ni ekranda ko'rsatilgan taqsimot server qiladigan
   * taqsimot bilan bir xil bo'ladi.
   */
  childBalance: (childId: string) => api.get<ChildBalance>('/ledger/balance', { child: childId }),

  dailySummary: (date?: string) =>
    api.get<DailyCashSummary>('/payments/daily-summary', date ? { date } : undefined),
}

/** Oy boʻyicha qarzdorlik (PLAN 9.2) — "qaysi oyning qarzi qolgan?". */
export interface DebtPeriodRow {
  period: string
  period_year: number
  period_month: number
  invoiced: string
  paid: string
  /** Muddatidan KEYIN toʻlangan qism — "kech toʻlandi" ustuni. */
  paid_late: string
  outstanding: string
  children: number
  debtors: number
}

export interface DebtPeriodPayment {
  paid_at: string
  method: string
  amount: string
  payment_id: string
}

export interface DebtPeriodChild {
  invoice_id: string
  invoice_number: string
  child_id: string
  child_name: string
  invoiced: string
  paid: string
  outstanding: string
  due_date: string
  days_overdue: number
  payments: DebtPeriodPayment[]
}

export const debtorsApi = {
  list: (params?: { overdue?: string; min_amount?: string }) =>
    api.get<DebtorList>('/debtors', params),
  statement: (childId: string) => api.get<ChildStatement>(`/debtors/${childId}`),
  byPeriod: (params: { from?: string; to?: string; group_id?: string }) =>
    api.get<{ count: number; totals: Record<string, string>; results: DebtPeriodRow[] }>(
      '/debtors/by-period',
      params,
    ),
  periodChildren: (params: { period: string; group_id?: string; debtors_only?: string }) =>
    api.get<{ period: string; count: number; results: DebtPeriodChild[] }>(
      '/debtors/by-period',
      params,
    ),
}
