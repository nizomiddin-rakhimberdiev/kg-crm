/**
 * Chiqimlar (docs/04 §13).
 *
 * Tasdiqlash oqimi: kutilmoqda → tasdiqlangan → to'langan (yoki rad
 * etilgan). Rad etilgan chiqim o'chirilmaydi — u nima so'ralgani va nega
 * rad etilgani haqidagi yozuv bo'lib qoladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Pencil, Plus, Receipt, Trash2, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { expensesApi } from '@/features/expenses/api'
import { cashApi } from '@/features/cash/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { EmptyRow } from '@/components/ui/EmptyState'
import { t } from '@/lib/i18n'

const money = (v: string) => new Intl.NumberFormat('uz-UZ').format(Number(v)) + t(" so'm")

const STATUS: Record<string, [string, string]> = {
  pending: [t('Kutilmoqda'), 'bg-amber-50 text-amber-700'],
  approved: [t('Tasdiqlangan'), 'border border-ildiz-300 bg-ildiz-50 text-ildiz-800'],
  rejected: [t('Rad etilgan'), 'bg-red-50 text-red-700'],
  paid: [t("To'langan"), 'bg-emerald-50 text-emerald-700'],
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
  const [form, setForm] = useState({
    category_id: '',
    amount: '',
    expense_date: '',
    description: '',
    // Qaysi puldan to'lanadi (ADR-17) — mijozning so'zi: "chiqim
    // kiritayotgan paytda qaysi puldan ketayotgani hisobga olinishi
    // kerak". Bo'sh qoldirilsa tasdiqlashda naqd kassa olinadi.
    cash_account_id: '',
  })
  const accountsQuery = useQuery({
    queryKey: queryKeys.cashAccounts(organizationId),
    queryFn: cashApi.accounts,
    enabled: can('expenses.create'),
  })
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

  // Chiqim tasdiqlanganda pul kassadan chiqadi (ADR-17) — ya'ni
  // kassa, hisobot, bosh sahifa va brifing ham o'zgaradi. Auditda
  // "Shu oy (tasdiqlangan) 0 so'm" aynan shu sababdan qolib ketgan edi.
  const invalidate = () => invalidateMoney(queryClient, organizationId)
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const create = useMutation({
    mutationFn: () =>
      expensesApi.create({
        ...form,
        ...(form.cash_account_id ? {} : { cash_account_id: undefined }),
      }),
    onSuccess: () => {
      setForm({
        category_id: '',
        amount: '',
        expense_date: '',
        description: '',
        cash_account_id: '',
      })
      setError(null)
      invalidate()
    },
    onError: fail,
  })
  // Kategoriyani qayta nomlash / o'chirish. Ilgari kategoriya faqat
  // BITTA marta, ro'yxat bo'sh bo'lganda qo'shilardi va keyin unga umuman
  // tegib bo'lmasdi — xato yozilgan nom abadiy qolardi.
  const [editingCategory, setEditingCategory] = useState<{ id: string; name: string } | null>(null)

  const renameCategory = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) =>
      expensesApi.updateCategory(id, { name }),
    onSuccess: () => {
      setEditingCategory(null)
      setError(null)
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseCategories(organizationId) })
    },
    onError: fail,
  })

  const removeCategory = useMutation({
    mutationFn: (id: string) => expensesApi.removeCategory(id),
    onSuccess: () => {
      setError(null)
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseCategories(organizationId) })
    },
    // Kategoriyada chiqim bo'lsa backend `422` qaytaradi (ON DELETE RESTRICT) —
    // xabarni ko'rsatamiz, jimgina yutmaymiz.
    onError: fail,
  })

  const addCategory = useMutation({
    mutationFn: () => expensesApi.createCategory({ name: newCategory }),
    onSuccess: () => {
      setNewCategory('')
      setError(null)
      void queryClient.invalidateQueries({ queryKey: queryKeys.expenseCategories(organizationId) })
    },
    onError: fail,
  })
  const decide = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' | 'markPaid' }) =>
      action === 'approve'
        ? expensesApi.approve(id)
        : action === 'reject'
          ? expensesApi.reject(id)
          : expensesApi.markPaid(id),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Chiqimlar')}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('Faqat tasdiqlangan chiqim hisobotga kiradi.')}
          </p>
        </div>
        {summaryQuery.data && (
          <div className="text-right">
            <p className="text-xs text-slate-500">{t('Shu oy (tasdiqlangan)')}</p>
            <p className="text-xl font-bold text-slate-900">{money(summaryQuery.data.total)}</p>
          </div>
        )}
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {can('expenses.create') && (
        <>
          {/* Kategoriyalar — DOIMO ko'rinadi: qo'shish, qayta nomlash,
              o'chirish. Ilgari bu forma faqat ro'yxat bo'sh bo'lganda
              chiqardi, ya'ni ikkinchi kategoriyani qo'shishning iloji
              yo'q edi. */}
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs font-medium text-slate-600">{t('Kategoriyalar')}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {categoriesQuery.data?.items.map((c) =>
                editingCategory?.id === c.id ? (
                  <form
                    key={c.id}
                    onSubmit={(e) => {
                      e.preventDefault()
                      renameCategory.mutate(editingCategory)
                    }}
                    className="flex items-center gap-1"
                  >
                    <input
                      autoFocus
                      value={editingCategory.name}
                      onChange={(e) =>
                        setEditingCategory((prev) =>
                          prev ? { ...prev, name: e.target.value } : prev,
                        )
                      }
                      className="w-36 rounded-lg border border-brand-300 px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-brand-100"
                    />
                    <button
                      type="submit"
                      className="rounded-lg bg-brand-600 px-2 py-1 text-xs font-semibold text-white"
                    >
                      {t('Saqlash')}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingCategory(null)}
                      className="rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-600"
                    >
                      {t('Bekor')}
                    </button>
                  </form>
                ) : (
                  <span
                    key={c.id}
                    className="group flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 py-1 pl-3 pr-1.5 text-sm text-slate-700"
                  >
                    {c.name}
                    <button
                      type="button"
                      onClick={() => setEditingCategory({ id: c.id, name: c.name })}
                      title={t('Tahrirlash')}
                      className="rounded p-0.5 text-slate-300 transition hover:text-slate-700 group-hover:text-slate-500"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => removeCategory.mutate(c.id)}
                      title={t("O'chirish")}
                      className="rounded p-0.5 text-slate-300 transition hover:text-red-600 group-hover:text-slate-500"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </span>
                ),
              )}

              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  addCategory.mutate()
                }}
                className="flex items-center gap-1"
              >
                <input
                  id="cat"
                  required
                  value={newCategory}
                  placeholder={t('Yangi kategoriya')}
                  aria-label={t('Yangi kategoriya')}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="w-40 rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500"
                />
                <button
                  type="submit"
                  className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700"
                >
                  {t("Qo'shish")}
                </button>
              </form>
            </div>
          </div>

          {(categoriesQuery.data?.items.length ?? 0) > 0 && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                create.mutate()
              }}
              className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-3"
            >
              <div>
                <label htmlFor="ecat" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Kategoriya')}
                </label>
                <select
                  id="ecat"
                  required
                  value={form.category_id}
                  onChange={(e) => setForm((p) => ({ ...p, category_id: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                >
                  <option value="">{t('Tanlang…')}</option>
                  {categoriesQuery.data?.items.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="eamt" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Summa')}
                </label>
                <input
                  id="eamt"
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  value={form.amount}
                  onChange={(e) => setForm((p) => ({ ...p, amount: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <div>
                <label htmlFor="edate" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Sana')}
                </label>
                <input
                  id="edate"
                  type="date"
                  required
                  value={form.expense_date}
                  onChange={(e) => setForm((p) => ({ ...p, expense_date: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              {/* Tavsif maydoni bazada ham, jadvalda ham bor edi — faqat
                  formada yo'q edi, ya'ni har doim bo'sh saqlanardi.
                  "Ta'mirlash" o'zi kam: nimaga ketgani yozilsin. */}
              <div className="sm:col-span-2">
                <label htmlFor="edesc" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Tavsif')}
                </label>
                <input
                  id="edesc"
                  maxLength={255}
                  value={form.description}
                  placeholder={t('Masalan: kraska, konditsioner ta’miri')}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              {/* Qaysi puldan to'lanadi (ADR-17). Ixtiyoriy: so'rovni
                  yozgan odam ko'pincha uni to'laydigan odam emas. */}
              <div>
                <label htmlFor="eacct" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Qaysi puldan')}
                </label>
                <select
                  id="eacct"
                  value={form.cash_account_id}
                  onChange={(e) => setForm((p) => ({ ...p, cash_account_id: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                >
                  <option value="">{t('Naqd kassa (sukut)')}</option>
                  {accountsQuery.data?.items.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={create.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
                >
                  <Plus className="h-4 w-4" /> {t("Qo'shish")}
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
            <p className="text-sm text-slate-500">{t("Chiqim yo'q.")}</p>
          </div>
        )}

        {(expensesQuery.data?.items.length ?? 0) > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">{t('Sana')}</th>
                  <th className="px-4 py-3 font-medium">{t('Kategoriya')}</th>
                  <th className="px-4 py-3 font-medium">{t('Izoh')}</th>
                  <th className="px-4 py-3 text-right font-medium">{t('Summa')}</th>
                  <th className="px-4 py-3 font-medium">{t('Holat')}</th>
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
                      <td className="px-4 py-3 text-right font-medium text-slate-900">
                        {money(e.amount)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                          {label}
                        </span>
                        {e.approved_by_name && (
                          <p className="mt-0.5 text-xs text-slate-400">{e.approved_by_name}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {can('expenses.approve') && e.status === 'pending' && (
                          <>
                            <button
                              type="button"
                              title={t('Tasdiqlash')}
                              onClick={() => decide.mutate({ id: e.id, action: 'approve' })}
                              className="mr-1 rounded-lg p-2 text-emerald-600 hover:bg-emerald-50"
                            >
                              <Check className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              title={t('Rad etish')}
                              onClick={() => decide.mutate({ id: e.id, action: 'reject' })}
                              className="rounded-lg p-2 text-red-600 hover:bg-red-50"
                            >
                              <X className="h-4 w-4" />
                            </button>
                          </>
                        )}
                        {can('expenses.update') && e.status === 'approved' && (
                          <button
                            type="button"
                            onClick={() => decide.mutate({ id: e.id, action: 'markPaid' })}
                            className="rounded-lg px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50"
                          >
                            {t("To'landi")}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
                {expensesQuery.data?.items.length === 0 && (
                  <EmptyRow
                    colSpan={7}
                    icon={Receipt}
                    title={t('Chiqim yozilmagan')}
                    hint={t(
                      "Bog'cha xarajatlari shu yerda qayd etiladi — oziq-ovqat, kommunal, ta'mir.",
                    )}
                  />
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
