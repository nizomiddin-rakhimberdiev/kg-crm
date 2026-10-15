/**
 * Pul qoplari (ADR-17).
 *
 * Qoplar dashboard javobida ham keladi, lekin u yerda faqat QOLDIQ
 * bilan va faqat moliyaga to'liq haqli rolga. Chiqim yozayotgan
 * kassirga esa ro'yxatning o'zi kerak — shuning uchun alohida chaqiruv.
 */

import { api } from '@/lib/api/client'
import type { CashAccountBalance } from '@/lib/api/types'

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
}

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
  closeDay: (payload: { cash_account_id: string; counted: string; reason?: string }) =>
    api.post<CashCount>('/cash-counts', payload),
}
