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
}
