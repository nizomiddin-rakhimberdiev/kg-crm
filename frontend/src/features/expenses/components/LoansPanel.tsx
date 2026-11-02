/**
 * Qarzga berilgan pul (mijoz soʻrovi, 2026-10-28).
 *
 * Mijozning soʻzi: *"Qoralama pullar kiritish, chiqimlar boʻlimida
 * alohida windowda boʻlsin. summadan ayrilaversin, lekin xisob
 * kitobga ham tushaversin, u qarz pullar boʻlishi mumkin, uni
 * qaytarish imkoniyati ham boʻlishi kerak qaytsa yana umumiy summaga
 * tushib qolaversin"*.
 *
 * Bu CHIQIM emas va shuning uchun alohida turadi: pul ketdi, lekin
 * yoʻqolmadi — u kimdadir turibdi. Kassadan chiqadi (pul haqiqatan
 * qoʻldan ketdi), foyda-zararga esa kirmaydi (bogʻcha kambagʻal
 * boʻlgani yoʻq).
 */

import { useState } from 'react'
import { today } from '@/lib/format'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { HandCoins, Plus, Undo2 } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useCan } from '@/lib/rbac/useCan'
import { DateInput } from '@/components/ui/DateInput'
import { Modal } from '@/components/ui/Modal'
import { PotSelect } from '@/features/expenses/components/PotSelect'
import { usePots } from '@/features/expenses/pots'
import { loansApi, type Loan } from '@/features/expenses/loansApi'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { formatDate, formatMoney } from '@/lib/utils'
import { t } from '@/lib/i18n'

export function LoansPanel() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [open, setOpen] = useState(false)
  const [returning, setReturning] = useState<Loan | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    person: '',
    amount: '',
    reason: '',
    cash_account_id: '',
    occurred_on: today(),
  })
  const [back, setBack] = useState({ amount: '', occurred_on: today(), note: '' })

  const loans = useQuery({
    queryKey: ['org', organizationId, 'loans'],
    queryFn: () => loansApi.list(),
  })
  const { pots } = usePots(can('expenses.create'))

  const done = () => {
    invalidateMoney(queryClient, organizationId)
    queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'loans'] })
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const lend = useMutation({
    mutationFn: () =>
      loansApi.create({
        person: form.person,
        amount: form.amount,
        reason: form.reason,
        cash_account_id: form.cash_account_id,
        occurred_on: form.occurred_on,
      }),
    onSuccess: () => {
      done()
      setOpen(false)
      setForm({ person: '', amount: '', reason: '', cash_account_id: '', occurred_on: today() })
    },
    onError: fail,
  })

  const giveBack = useMutation({
    mutationFn: () =>
      loansApi.returnMoney(returning!.id, {
        amount: back.amount,
        occurred_on: back.occurred_on,
        note: back.note,
      }),
    onSuccess: () => {
      done()
      setReturning(null)
    },
    onError: fail,
  })

  const rows = loans.data?.items ?? []
  const outstanding = rows.reduce((sum, row) => sum + Number(row.outstanding), 0)
  const field =
    'h-10 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

  return (
    <section className="rounded-2xl border border-slate-200 bg-white">
      <header className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
        <HandCoins className="h-4 w-4 text-slate-500" />
        <h2 className="text-sm font-semibold text-slate-800">{t('Qarzga berilgan pul')}</h2>
        {outstanding > 0 && (
          <span className="num rounded-full bg-orik-50 px-2 py-0.5 text-xs font-semibold text-orik-700">
            {t('qaytmagan {money}', { money: formatMoney(outstanding) })}
          </span>
        )}
        {can('expenses.create') && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="ml-auto flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            <Plus className="h-4 w-4" /> {t('Qarz berish')}
          </button>
        )}
      </header>

      {error && (
        <p role="alert" className="mx-4 mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {rows.length === 0 ? (
        <p className="px-4 py-8 text-center text-sm text-slate-500">
          {t('Hozircha qarzga pul berilmagan.')}
        </p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {rows.map((loan) => (
            <li key={loan.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-slate-800">
                  {loan.person}
                </span>
                <span className="block truncate text-xs text-slate-500">
                  {formatDate(loan.occurred_on)} · {loan.cash_account_name} · {loan.reason}
                </span>
              </span>
              <span className="text-right">
                <span className="num block text-sm font-semibold text-slate-900">
                  {formatMoney(Number(loan.amount))}
                </span>
                <span
                  className={
                    Number(loan.outstanding) > 0
                      ? 'num block text-xs text-orik-700'
                      : 'num block text-xs text-emerald-700'
                  }
                >
                  {Number(loan.outstanding) > 0
                    ? t('qaytmagan {money}', { money: formatMoney(Number(loan.outstanding)) })
                    : t('toʻliq qaytdi')}
                </span>
              </span>
              {can('expenses.update') && Number(loan.outstanding) > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    setReturning(loan)
                    setBack({ amount: loan.outstanding, occurred_on: today(), note: '' })
                  }}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  <Undo2 className="h-4 w-4" /> {t('Qaytdi')}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {open && (
        <Modal open onClose={() => setOpen(false)} className="max-w-md">
          <form
            className="p-6"
            onSubmit={(event) => {
              event.preventDefault()
              lend.mutate()
            }}
          >
            <h2 className="pr-10 text-lg font-bold text-slate-900">{t('Qarz berish')}</h2>
            <p className="mt-0.5 text-sm text-slate-500">
              {t('Pul kassadan chiqadi, lekin chiqim hisoblanmaydi — u qaytishi kutilmoqda.')}
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label
                  htmlFor="ln-person"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {t('Kimga')} <span className="text-red-500">*</span>
                </label>
                <input
                  id="ln-person"
                  required
                  maxLength={120}
                  value={form.person}
                  onChange={(event) => setForm((p) => ({ ...p, person: event.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label
                  htmlFor="ln-amount"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {t('Summa')} <span className="text-red-500">*</span>
                </label>
                <input
                  id="ln-amount"
                  type="number"
                  required
                  min="1"
                  value={form.amount}
                  onChange={(event) => setForm((p) => ({ ...p, amount: event.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label
                  htmlFor="ln-reason"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {t('Nima uchun')} <span className="text-red-500">*</span>
                </label>
                <input
                  id="ln-reason"
                  required
                  maxLength={255}
                  value={form.reason}
                  onChange={(event) => setForm((p) => ({ ...p, reason: event.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label
                  htmlFor="ln-account"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {t('Qaysi hisobdan')} <span className="text-red-500">*</span>
                </label>
                <PotSelect
                  id="ln-account"
                  pots={pots}
                  value={form.cash_account_id}
                  onChange={(value) => setForm((p) => ({ ...p, cash_account_id: value }))}
                />
              </div>
              <div>
                <label htmlFor="ln-date" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Qachon')} <span className="text-red-500">*</span>
                </label>
                <DateInput
                  id="ln-date"
                  required
                  max={today()}
                  value={form.occurred_on}
                  onChange={(iso) => setForm((p) => ({ ...p, occurred_on: iso }))}
                />
              </div>
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                {t('Bekor qilish')}
              </button>
              <button
                type="submit"
                disabled={lend.isPending}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
              >
                {lend.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {returning && (
        <Modal open onClose={() => setReturning(null)} className="max-w-md">
          <form
            className="p-6"
            onSubmit={(event) => {
              event.preventDefault()
              giveBack.mutate()
            }}
          >
            <h2 className="pr-10 text-lg font-bold text-slate-900">{t('Qarz qaytdi')}</h2>
            <p className="mt-0.5 text-sm text-slate-500">
              {returning.person} ·{' '}
              {t('qaytmagan {money}', { money: formatMoney(Number(returning.outstanding)) })}
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <label
                  htmlFor="rt-amount"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {t('Summa')} <span className="text-red-500">*</span>
                </label>
                <input
                  id="rt-amount"
                  type="number"
                  required
                  min="1"
                  max={returning.outstanding}
                  value={back.amount}
                  onChange={(event) => setBack((p) => ({ ...p, amount: event.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label htmlFor="rt-date" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Qachon')} <span className="text-red-500">*</span>
                </label>
                <DateInput
                  id="rt-date"
                  required
                  max={today()}
                  value={back.occurred_on}
                  onChange={(iso) => setBack((p) => ({ ...p, occurred_on: iso }))}
                />
              </div>
              <div>
                <label htmlFor="rt-note" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Izoh')}
                </label>
                <input
                  id="rt-note"
                  maxLength={255}
                  value={back.note}
                  onChange={(event) => setBack((p) => ({ ...p, note: event.target.value }))}
                  className={field}
                />
              </div>
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setReturning(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                {t('Bekor qilish')}
              </button>
              <button
                type="submit"
                disabled={giveBack.isPending}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
              >
                {giveBack.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  )
}
