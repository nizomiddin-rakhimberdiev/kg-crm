import { api, httpClient } from '@/lib/api/client'
import { withBranch } from '@/lib/branchScope'
import type { Envelope, Expense, ExpenseCategory, ExpenseSummary } from '@/lib/api/types'

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
    /** Qaysi puldan to'lanadi (ADR-17) — MAJBURIY (2026-10-14), nasiyadan tashqari. */
    cash_account_id?: string
    /** Chiqim qatorlari (PLAN 7.5): nima, qancha, qanchadan. */
    items?: ExpenseItemInput[]
    /** Qopda yetmasa ham yozilsin — foydalanuvchi ogohlantirishni o'qidi (ADR-29). */
    allow_negative?: boolean
    /** Bosqich 13.2a: tegishli oy, investitsiya, nasiya. */
    period?: string
    is_capex?: boolean
    amortize_months?: number
    on_credit?: boolean
    supplier_id?: string
    due_date?: string
  }) => api.post<Expense>('/expenses', withBranch(payload)),

  /** Chek rasmi yoki PDF (Bosqich 13.3a). */
  async uploadReceipt(id: string, file: File) {
    const form = new FormData()
    form.append('file', file)
    // Content-Type'ni brauzer boundary bilan o'zi qo'yadi.
    const response = await httpClient.post<Envelope<Expense>>(`/expenses/${id}/receipt`, form, {
      headers: { 'Content-Type': undefined },
    })
    return response.data.data
  },
  /** Nasiyani toʻlash — pul shu kuni tanlangan qopdan chiqadi. */
  payCredit: (id: string, cashAccountId: string, paidOn?: string) =>
    api.post<Expense>(`/expenses/${id}/mark-paid`, {
      cash_account_id: cashAccountId,
      ...(paidOn ? { paid_on: paidOn } : {}),
    }),
  /**
   * Tahrirlash (2026-10-14). Summa, sana yoki qop o'zgarsa backend eski
   * chiqimga qarshi yozuv va yangisiga chiqim yozadi — jurnal append-only.
   */
  update: (
    id: string,
    payload: {
      category_id?: string
      expense_date?: string
      description?: string
      cash_account_id?: string
      items?: ExpenseItemInput[]
      amount?: string
      allow_negative?: boolean
    },
  ) => api.patch<Expense>(`/expenses/${id}`, payload),
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
  /** Oxirgi ishlatilgani tepada (Bosqich 13.3a). */
  recentCategories: () =>
    api.list<ExpenseCategory>('/expense-categories', { ordering: 'recent', page_size: 200 }),
  createCategory: (payload: { name: string }) =>
    api.post<ExpenseCategory>('/expense-categories', withBranch(payload)),
  updateCategory: (id: string, payload: { name: string }) =>
    api.patch<ExpenseCategory>(`/expense-categories/${id}`, payload),
  removeCategory: (id: string) => api.delete(`/expense-categories/${id}`),
}
