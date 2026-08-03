/**
 * Chiqimlar (docs/04 §13).
 *
 * Tasdiqlash oqimi: kutilmoqda → tasdiqlangan → to'langan (yoki rad
 * etilgan). Rad etilgan chiqim o'chirilmaydi — u nima so'ralgani va nega
 * rad etilgani haqidagi yozuv bo'lib qoladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Plus, Receipt, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { expensesApi } from '@/features/expenses/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const money = (v: string) => new Intl.NumberFormat('uz-UZ').format(Number(v)) + " so'm"

const STATUS: Record<string, [string, string]> = {
  pending: ['Kutilmoqda', 'bg-amber-50 text-amber-700'],
  approved: ['Tasdiqlangan', 'bg-sky-50 text-sky-700'],
  rejected: ['Rad etilgan', 'bg-red-50 text-red-700'],
  paid: ["To'langan", 'bg-emerald-50 text-emerald-700'],
}

const monthRange = () => {
  const now = new Date()
  const first = new Date(now.getFullYear(), now.getMonth(), 1)
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return [first.toISOString().slice(0, 10), last.toISOString().slice(0, 10)] as const
}

export default function ExpensesPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [from, to] = monthRange()
  const [form, setForm] = useState({ category_id: '', amount: '', expense_date: '', description: '' })
  const [newCategory, setNewCategory] = useState('')
  const [error, setError] = useState<string | null>(null)

  const expensesQuery = useQuery({
    queryKey: queryKeys.expenses(organizationId),
    queryFn: () => expensesApi.list(),
  })
  const categoriesQuery = useQuery({
    queryKey: queryKeys.expenseCategories(organizationId),
    queryFn: expensesApi.categories,
  })
  const summaryQuery = useQuery({
    queryKey: [...queryKeys.expenses(organizationId), 'summary', from, to],
    queryFn: () => expensesApi.summary(from, to),
  })

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'expenses'] })
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : 'Xatolik yuz berdi.')

  const create = useMutation({
    mutationFn: () => expensesApi.create(form),
    onSuccess: () => {
      setForm({ category_id: '', amount: '', expense_date: '', description: '' })
      setError(null); invalidate()
    },
    onError: fail,
  })
  const addCategory = useMutation({
    mutationFn: () => expensesApi.createCategory({ name: newCategory }),
    onSuccess: () => { setNewCategory(''); setError(null); void queryClient.invalidateQueries({ queryKey: queryKeys.expenseCategories(organizationId) }) },
    onError: fail,
  })
  const decide = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' | 'markPaid' }) =>
      action === 'approve' ? expensesApi.approve(id)
        : action === 'reject' ? expensesApi.reject(id) : expensesApi.markPaid(id),
    onSuccess: () => { setError(null); invalidate() },
    onError: fail,
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Chiqimlar</h1>
          <p className="mt-1 text-sm text-slate-500">
            Faqat tasdiqlangan chiqim hisobotga kiradi.
          </p>
        </div>
        {summaryQuery.data && (
          <div className="text-right">
            <p className="text-xs text-slate-500">Shu oy (tasdiqlangan)</p>
            <p className="text-xl font-bold text-slate-900">{money(summaryQuery.data.total)}</p>
          </div>
        )}
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {can('expenses.create') && (
        <>
          {categoriesQuery.data?.items.length === 0 && (
            <form onSubmit={(e) => { e.preventDefault(); addCategory.mutate() }}
              className="flex items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
              <div className="flex-1">
                <label htmlFor="cat" className="mb-1 block text-xs font-medium text-slate-600">
                  Avval kategoriya yarating
                </label>
                <input id="cat" required value={newCategory} placeholder="Kommunal"
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500" />
              </div>
              <button type="submit" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
                Qo'shish
              </button>
            </form>
          )}

          {(categoriesQuery.data?.items.length ?? 0) > 0 && (
            <form onSubmit={(e) => { e.preventDefault(); create.mutate() }}
              className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-4">
              <div>
                <label htmlFor="ecat" className="mb-1 block text-xs font-medium text-slate-600">Kategoriya</label>
                <select id="ecat" required value={form.category_id}
                  onChange={(e) => setForm((p) => ({ ...p, category_id: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500">
                  <option value="">Tanlang…</option>
                  {categoriesQuery.data?.items.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label htmlFor="eamt" className="mb-1 block text-xs font-medium text-slate-600">Summa</label>
                <input id="eamt" type="number" required min="0.01" step="0.01" value={form.amount}
                  onChange={(e) => setForm((p) => ({ ...p, amount: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500" />
              </div>
              <div>
                <label htmlFor="edate" className="mb-1 block text-xs font-medium text-slate-600">Sana</label>
                <input id="edate" type="date" required value={form.expense_date}
                  onChange={(e) => setForm((p) => ({ ...p, expense_date: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500" />
              </div>
              <div className="flex items-end">
                <button type="submit" disabled={create.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
                  <Plus className="h-4 w-4" /> Qo'shish
                </button>
              </div>
            </form>
          )}
        </>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {expensesQuery.data?.items.length === 0 && (
          <div className="px-4 py-12 text-center">
            <Receipt className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm text-slate-500">Chiqim yo'q.</p>
          </div>
        )}

        {(expensesQuery.data?.items.length ?? 0) > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Sana</th>
                <th className="px-4 py-3 font-medium">Kategoriya</th>
                <th className="px-4 py-3 font-medium">Izoh</th>
                <th className="px-4 py-3 text-right font-medium">Summa</th>
                <th className="px-4 py-3 font-medium">Holat</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {expensesQuery.data?.items.map((e) => {
                const [label, tone] = STATUS[e.status] ?? [e.status, '']
                return (
                  <tr key={e.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-slate-500">{e.expense_date}</td>
                    <td className="px-4 py-3 text-slate-700">{e.category_name}</td>
                    <td className="px-4 py-3 text-slate-600">{e.description || '—'}</td>
                    <td className="px-4 py-3 text-right font-medium text-slate-900">{money(e.amount)}</td>
                    <td className="px-4 py-3">
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>{label}</span>
                      {e.approved_by_name && (
                        <p className="mt-0.5 text-xs text-slate-400">{e.approved_by_name}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {can('expenses.approve') && e.status === 'pending' && (
                        <>
                          <button type="button" title="Tasdiqlash"
                            onClick={() => decide.mutate({ id: e.id, action: 'approve' })}
                            className="mr-1 rounded-lg p-2 text-emerald-600 hover:bg-emerald-50">
                            <Check className="h-4 w-4" />
                          </button>
                          <button type="button" title="Rad etish"
                            onClick={() => decide.mutate({ id: e.id, action: 'reject' })}
                            className="rounded-lg p-2 text-red-600 hover:bg-red-50">
                            <X className="h-4 w-4" />
                          </button>
                        </>
                      )}
                      {can('expenses.update') && e.status === 'approved' && (
                        <button type="button"
                          onClick={() => decide.mutate({ id: e.id, action: 'markPaid' })}
                          className="rounded-lg px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50">
                          To'landi
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
