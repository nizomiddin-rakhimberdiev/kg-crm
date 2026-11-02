import { api } from '@/lib/api/client'
import { withBranch } from '@/lib/branchScope'
import type { EmployeeAdvance, PayrollItem, PayrollRun } from '@/lib/api/types'

/** Server taklif qilgan bitta to'lov qatori. */
export interface PlannedPayout {
  payroll_item_id: string
  employee: string
  part: 'official' | 'cash'
  amount: string
  cash_account_id: string
  cash_account_name: string
}

/** `mark-paid` ga yuboriladigan qator — qopi o'zgartirilgan bo'lishi mumkin. */
export interface PayoutLine {
  payroll_item_id: string
  part: 'official' | 'cash'
  amount: string
  cash_account_id: string
}

// Xodimlar va lavozimlar API'si `features/staff/api.ts` da — ular
// "Xodimlar" sahifasiga tegishli; oylik faqat hisoblashlar bilan ishlaydi.

export const payrollApi = {
  listRuns: (params?: Record<string, unknown>) => api.list<PayrollRun>('/payroll/runs', params),
  getRun: (id: string) => api.get<PayrollRun>(`/payroll/runs/${id}`),

  createRun: (periodYear: number, periodMonth: number) =>
    api.post<PayrollRun>(
      '/payroll/runs',
      withBranch({ period_year: periodYear, period_month: periodMonth }),
    ),

  updateItem: (
    runId: string,
    itemId: string,
    payload: { bonus?: string; deduction?: string; note?: string },
  ) => api.patch<PayrollItem>(`/payroll/runs/${runId}/items/${itemId}`, payload),

  finalize: (id: string) => api.post<PayrollRun>(`/payroll/runs/${id}/finalize`),

  /**
   * To'lov TAKLIFI: kim, qaysi qismi, qaysi qopdan (ADR-29).
   *
   * Ilgari "To'langan" tugmasi bu ro'yxatni ko'rsatmay yuborardi va
   * pul foydalanuvchi tanlamagan qopdan chiqib ketardi.
   */
  plannedPayouts: (id: string) => api.get<PlannedPayout[]>(`/payroll/runs/${id}/planned-payouts`),

  markPaid: (
    id: string,
    payload?: {
      payouts?: PayoutLine[]
      allow_negative?: boolean
      /** Pul QAYSI kuni chiqqani (audit, 2026-10-30). */
      paid_on?: string
    },
  ) => api.post<PayrollRun>(`/payroll/runs/${id}/mark-paid`, payload ?? {}),

  /**
   * Qoralamani qayta hisoblash: yangi xodimlar va avanslar.
   * Yakunlangan hisoblashga ta'sir qilmaydi (backend rad etadi).
   */
  recalculate: (id: string) => api.post<PayrollRun>(`/payroll/runs/${id}/recalculate`),

  /**
   * Yakunlangan (yoki to'langan) hisoblashni qoralamaga qaytaradi.
   * Sabab majburiy va audit jurnaliga tushadi; `payroll.approve` kerak.
   */
  reopen: (id: string, reason: string) =>
    api.post<PayrollRun>(`/payroll/runs/${id}/reopen`, { reason }),

  listAdvances: (params?: Record<string, unknown>) =>
    api.list<EmployeeAdvance>('/payroll/advances', params),
  createAdvance: (payload: {
    employee_id: string
    amount: string
    paid_on: string
    note?: string
    cash_account_id?: string
    allow_negative?: boolean
  }) => api.post<EmployeeAdvance>('/payroll/advances', payload),
  removeAdvance: (id: string) => api.delete(`/payroll/advances/${id}`),
}
