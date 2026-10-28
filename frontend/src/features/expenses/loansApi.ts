/**
 * Qarzga berilgan pul (mijoz soʻrovi, 2026-10-28).
 *
 * Server tomonda bu alohida jadval emas — `money_operation` hujjati
 * (13.2b). Ekran uchun esa alohida roʻyxat: savol "kimda qancha
 * qoldi?" va unga faqat shu koʻrinish javob beradi.
 */

import { api } from '@/lib/api/client'

export interface LoanReturn {
  id: string
  amount: string
  occurred_on: string
  cash_account_name: string
  reason: string
}

export interface Loan {
  id: string
  person: string
  amount: string
  /** Qaytmagan qismi — `amount` minus qaytishlar. */
  outstanding: string
  reason: string
  cash_account: string
  cash_account_name: string
  occurred_on: string
  returns: LoanReturn[]
  created_by_name: string | null
  created_at: string
}

export const loansApi = {
  list: () => api.list<Loan>('/loans'),

  create: (payload: {
    person: string
    amount: string
    reason: string
    cash_account_id: string
    occurred_on: string
  }) => api.post<Loan>('/loans', payload),

  /** Qaytgan pul oʻsha qarzga bogʻlanadi; hisob berilmasa — oʻsha hisobga. */
  returnMoney: (
    id: string,
    payload: { amount: string; occurred_on: string; note?: string; cash_account_id?: string },
  ) => api.post<Loan>(`/loans/${id}/return`, payload),
}
