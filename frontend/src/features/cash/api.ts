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
}
