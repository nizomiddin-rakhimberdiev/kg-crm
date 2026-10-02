import { api } from '@/lib/api/client'
import { withBranch } from '@/lib/branchScope'
import type { EmployeeAdvance, PayrollItem, PayrollRun } from '@/lib/api/types'

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
  markPaid: (id: string) => api.post<PayrollRun>(`/payroll/runs/${id}/mark-paid`),

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
  }) => api.post<EmployeeAdvance>('/payroll/advances', payload),
  removeAdvance: (id: string) => api.delete(`/payroll/advances/${id}`),
}
