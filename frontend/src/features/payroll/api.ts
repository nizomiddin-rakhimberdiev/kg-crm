import { api } from '@/lib/api/client'
import type { Employee, PayrollItem, PayrollRun, Position } from '@/lib/api/types'

export interface EmployeeInput {
  first_name: string
  last_name: string
  phone?: string
  position_id?: string | null
  hire_date: string
  base_salary: string
  employment_status?: string
}

export const employeesApi = {
  list: (params?: Record<string, unknown>) => api.list<Employee>('/employees', params),
  create: (payload: EmployeeInput) => api.post<Employee>('/employees', payload),
  update: (id: string, payload: Partial<EmployeeInput>) =>
    api.patch<Employee>(`/employees/${id}`, payload),
  terminate: (id: string) => api.delete(`/employees/${id}`),
}

export const positionsApi = {
  list: () => api.list<Position>('/positions'),
  create: (payload: { title: string; department?: string }) =>
    api.post<Position>('/positions', payload),
}

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
