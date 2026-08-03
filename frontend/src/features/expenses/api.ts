import { api } from '@/lib/api/client'
import type { Expense, ExpenseCategory, ExpenseSummary } from '@/lib/api/types'

export const expensesApi = {
  list: (params?: Record<string, unknown>) => api.list<Expense>('/expenses', params),
  create: (payload: {
    category_id: string; amount: string; expense_date: string; description?: string
  }) => api.post<Expense>('/expenses', payload),
  approve: (id: string, note = '') => api.post<Expense>(`/expenses/${id}/approve`, { note }),
  reject: (id: string, note = '') => api.post<Expense>(`/expenses/${id}/reject`, { note }),
  markPaid: (id: string) => api.post<Expense>(`/expenses/${id}/mark-paid`),
  summary: (from: string, to: string) =>
    api.get<ExpenseSummary>('/expenses/summary', { from, to }),

  categories: () => api.list<ExpenseCategory>('/expense-categories'),
  createCategory: (payload: { name: string }) =>
    api.post<ExpenseCategory>('/expense-categories', payload),
}
