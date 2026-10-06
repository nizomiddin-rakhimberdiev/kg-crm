import { api } from '@/lib/api/client'
import { withBranch } from '@/lib/branchScope'
import type { Expense, ExpenseCategory, ExpenseSummary } from '@/lib/api/types'

export interface ExpenseItemInput {
  name: string
  quantity: string
  unit: string
  unit_price: string
  note?: string
}

export const expensesApi = {
  list: (params?: Record<string, unknown>) => api.list<Expense>('/expenses', params),
  create: (payload: {
    category_id: string
    /** Qatorlar berilsa YUBORILMAYDI — summa ulardan hisoblanadi. */
    amount?: string
    expense_date: string
    description?: string
    /** Qaysi puldan to'lanadi (ADR-17) — bo'sh bo'lsa naqd kassa. */
    cash_account_id?: string
    /** Chiqim qatorlari (PLAN 7.5): nima, qancha, qanchadan. */
    items?: ExpenseItemInput[]
  }) => api.post<Expense>('/expenses', withBranch(payload)),
  /** Tasdiqlash — pul aynan shu yerda kassadan chiqadi (ADR-17). */
  approve: (id: string, note = '', cashAccountId?: string) =>
    api.post<Expense>(`/expenses/${id}/approve`, {
      note,
      ...(cashAccountId ? { cash_account_id: cashAccountId } : {}),
    }),
  reject: (id: string, note = '') => api.post<Expense>(`/expenses/${id}/reject`, { note }),
  markPaid: (id: string) => api.post<Expense>(`/expenses/${id}/mark-paid`),
  summary: (from: string, to: string) => api.get<ExpenseSummary>('/expenses/summary', { from, to }),

  categories: () => api.list<ExpenseCategory>('/expense-categories'),
  createCategory: (payload: { name: string }) =>
    api.post<ExpenseCategory>('/expense-categories', withBranch(payload)),
  updateCategory: (id: string, payload: { name: string }) =>
    api.patch<ExpenseCategory>(`/expense-categories/${id}`, payload),
  removeCategory: (id: string) => api.delete(`/expense-categories/${id}`),
}
