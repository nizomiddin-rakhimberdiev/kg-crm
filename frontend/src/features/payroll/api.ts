import { api } from '@/lib/api/client'
import type { PayrollItem, PayrollRun } from '@/lib/api/types'

// Xodimlar va lavozimlar API'si `features/staff/api.ts` da — ular
// "Xodimlar" sahifasiga tegishli; oylik faqat hisoblashlar bilan ishlaydi.

export const payrollApi = {
  listRuns: (params?: Record<string, unknown>) => api.list<PayrollRun>('/payroll/runs', params),
  getRun: (id: string) => api.get<PayrollRun>(`/payroll/runs/${id}`),

  createRun: (periodYear: number, periodMonth: number) =>
    api.post<PayrollRun>('/payroll/runs', {
      period_year: periodYear,
      period_month: periodMonth,
    }),

  updateItem: (
    runId: string,
    itemId: string,
    payload: { bonus?: string; deduction?: string; note?: string },
  ) => api.patch<PayrollItem>(`/payroll/runs/${runId}/items/${itemId}`, payload),

  finalize: (id: string) => api.post<PayrollRun>(`/payroll/runs/${id}/finalize`),
  markPaid: (id: string) => api.post<PayrollRun>(`/payroll/runs/${id}/mark-paid`),
}
