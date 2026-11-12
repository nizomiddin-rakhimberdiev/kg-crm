/**
 * Pul qoplari (ADR-17).
 *
 * Qoplar dashboard javobida ham keladi, lekin u yerda faqat QOLDIQ
 * bilan va faqat moliyaga to'liq haqli rolga. Chiqim yozayotgan
 * kassirga esa ro'yxatning o'zi kerak — shuning uchun alohida chaqiruv.
 */

import { api, httpClient } from '@/lib/api/client'
import type { CashAccountBalance, Envelope } from '@/lib/api/types'

export interface CashAccount {
  id: string
  name: string
  kind: 'cash' | 'terminal' | 'bank' | 'ewallet'
  handles_method: string
  branch: string
  branch_name: string
  is_active: boolean
}

/** Naqd pulni qoʻldan qoʻlga topshirish (Bosqich 12.5). */
export interface CashHandover {
  id: string
  cash_account: string
  from_user: string
  from_user_name: string
  to_user: string
  to_user_name: string
  amount: string
  note: string
  status: 'pending' | 'confirmed' | 'rejected'
  decided_at: string | null
  decision_note: string
  created_at: string
}

/** Kun yopilishi — sanoq tizim bilan (Bosqich 12.5). */
export interface CashCount {
  id: string
  cash_account: string
  cash_account_name: string
  counted_on: string
  system_balance: string
  counted: string
  /** counted − system: manfiy — kamomad, musbat — ortiqcha. */
  difference: string
  reason: string
  created_by_name: string | null
  created_at: string
}

/** Kimning javobgarligida qancha — naqd va bank hisobi alohida. */
export interface CustodyRow {
  user_id: string
  full_name: string
  cash: string
  bank: string
  amount: string
  /** Topshirishga va'da qilingan, hali tasdiqlanmagan summa. */
  pending_out: string
  /** Qo'lda bo'sh turgan pul: `amount − pending_out`. */
  available: string
}

/** Bankka hali tushmagan terminal/Click/Payme puli (Bosqich 13.2c). */
export interface InTransitRow {
  payment_id: string
  child: string
  method: string
  paid_on: string
  amount: string
  commission: string
  expected_amount: string
  expected_on: string
  overdue: boolean
}

export type OperationKind =
  | 'other_income'
  | 'owner_draw'
  | 'owner_contribution'
  | 'loan_in'
  | 'loan_repay'
  | 'loan_out'
  | 'loan_return'
  | 'tax_payment'

/** Xarajat ham, tushum ham boʻlmagan pul harakati (Bosqich 13.2b). */
export interface MoneyOperation {
  id: string
  kind: OperationKind
  subtype: string
  cash_account: string
  cash_account_name: string
  amount: string
  occurred_on: string
  period: string
  counterparty: string
  reason: string
  tax_amount: string
  created_by_name: string | null
  created_at: string
}

/** Bank koʻchirmasi (Bosqich 13.3d). */
export interface BankStatement {
  id: string
  cash_account: string
  cash_account_name: string
  file_name: string
  period_from: string | null
  period_to: string | null
  closing_balance: string | null
  system_balance: string | null
  balance_difference: string | null
  line_count: number
  matched_count: number
  skipped_count: number
  unmatched_count: number
  created_at: string
  matched?: number
  skipped?: number
}

export interface StatementLine {
  id: string
  statement: string
  line_no: number
  booked_on: string
  direction: 'in' | 'out'
  amount: string
  purpose: string
  counterparty: string
  reference: string
  status: 'unmatched' | 'matched' | 'ignored'
  match_kind: string
  note: string
}

export type StatementMapping = Partial<
  Record<'date' | 'amount' | 'debit' | 'credit' | 'purpose' | 'counterparty' | 'reference', string>
>

export const cashApi = {
  accounts: () => api.list<CashAccount>('/cash-accounts', { page_size: 50 }),
  balances: () => api.get<CashAccountBalance[]>('/cash-accounts/balances'),

  /**
   * Qoldiqni qo'lda to'g'rilash (ADR-29).
   *
   * Busiz qoldiq doim noldan boshlanardi: tizimga yil o'rtasida
   * kelgan bog'chaning seyfidagi pul hech qayerda yo'q edi va
   * birinchi chiqimdayoq qoldiq manfiyga tushardi.
   */
  adjust: (
    id: string,
    payload: { amount: string; reason: string; opening?: boolean; occurred_on?: string },
  ) => api.post<{ id: string; balance: string }>(`/cash-accounts/${id}/adjust`, payload),

  /** Inkassa, bankdan naqd yechish — tushum ham, xarajat ham emas. */
  transfer: (payload: {
    from_account_id: string
    to_account_id: string
    amount: string
    reason: string
    allow_negative?: boolean
  }) =>
    api.post<{ transfer_group: string; from_balance: string; to_balance: string }>(
      '/cash-accounts/transfer',
      payload,
    ),

  /** Kimning qoʻlida qancha naqd pul. */
  custody: () => api.get<CustodyRow[]>('/cash-accounts/custody'),

  handovers: () => api.list<CashHandover>('/cash-handovers', { page_size: 30 }),
  receivers: () => api.get<Array<{ id: string; full_name: string }>>('/cash-handovers/receivers'),
  handOver: (payload: {
    to_user_id: string
    amount: string
    note?: string
    /** Naqd kassa yoki bank hisobi; boʻsh — naqd. */
    cash_account_id?: string
  }) => api.post<CashHandover>('/cash-handovers', payload),
  confirmHandover: (id: string) => api.post<CashHandover>(`/cash-handovers/${id}/confirm`),
  rejectHandover: (id: string, reason: string) =>
    api.post<CashHandover>(`/cash-handovers/${id}/reject`, { reason }),

  counts: () => api.list<CashCount>('/cash-counts', { page_size: 20 }),
  closeDay: (payload: {
    cash_account_id: string
    counted: string
    reason?: string
    /** Kupyuralar: {"200000": 5} — berilsa sanoq ularning yigʻindisi. */
    denominations?: Record<string, number>
  }) => api.post<CashCount>('/cash-counts', payload),

  inTransit: () =>
    api.get<{ items: InTransitRow[]; expected_total: string; overdue_count: number }>(
      '/payments/in-transit',
    ),
  settle: (payload: { payment_ids: string[]; settled_on: string; reference?: string }) =>
    api.post<{ count: number; expected_total: string }>('/payments/settle', payload),

  operations: () => api.list<MoneyOperation>('/money-operations', { page_size: 20 }),
  createOperation: (payload: {
    kind: OperationKind
    subtype?: string
    cash_account_id: string
    amount: string
    occurred_on: string
    reason: string
    period?: string
    counterparty?: string
  }) => api.post<MoneyOperation>('/money-operations', payload),

  async statementPreview(file: File) {
    const form = new FormData()
    form.append('file', file)
    const response = await httpClient.post<Envelope<{ headers: string[]; sample: string[][] }>>(
      '/bank-statements/preview',
      form,
      { headers: { 'Content-Type': undefined } },
    )
    return response.data.data
  },
  async importStatement(payload: {
    file: File
    cash_account_id: string
    mapping: StatementMapping
    closing_balance?: string
  }) {
    const form = new FormData()
    form.append('file', payload.file)
    form.append('cash_account_id', payload.cash_account_id)
    form.append('mapping', JSON.stringify(payload.mapping))
    if (payload.closing_balance) form.append('closing_balance', payload.closing_balance)
    const response = await httpClient.post<Envelope<BankStatement>>('/bank-statements', form, {
      headers: { 'Content-Type': undefined },
    })
    return response.data.data
  },
  statements: () => api.list<BankStatement>('/bank-statements', { page_size: 10 }),
  unmatchedLines: () => api.get<StatementLine[]>('/bank-statements/lines', { status: 'unmatched' }),
  ignoreLine: (id: string, note: string) =>
    api.post<StatementLine>(`/bank-statements/lines/${id}/ignore`, { note }),
  lineToExpense: (id: string, categoryId: string) =>
    api.post<StatementLine>(`/bank-statements/lines/${id}/expense`, { category_id: categoryId }),
  lineToPayment: (id: string, childId: string) =>
    api.post<StatementLine>(`/bank-statements/lines/${id}/payment`, { child_id: childId }),
}
