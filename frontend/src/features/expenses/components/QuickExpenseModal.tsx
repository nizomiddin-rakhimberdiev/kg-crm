/**
 * Tezkor chiqim — 20 soniyada (Bosqich 13.3a, brif §4).
 *
 * Tartib odam oʻylagan tartibda: summa → toifa (oxirgi ishlatilganlari
 * tugma boʻlib tepada) → qaysi puldan → chek rasmi. Qolgani — tegishli
 * oy, investitsiya, nasiya — "Qoʻshimcha" ostida: odatiy chiqimda
 * ularga tegilmaydi, sukut toʻgʻri.
 */

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Camera, ChevronDown } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { DateInput } from '@/components/ui/DateInput'
import { Modal } from '@/components/ui/Modal'
import { cashApi } from '@/features/cash/api'
import { expensesApi } from '@/features/expenses/api'
import { inventoryApi } from '@/features/inventory/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { money, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

const field =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'
const label = 'mb-1 block text-xs font-medium text-slate-600'
const CHIPS = 8

function thisMonth(): string {
  return today().slice(0, 7)
}

export function QuickExpenseModal({ onClose }: { onClose: () => void }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const categories = useQuery({
    queryKey: ['org', organizationId, 'expenses', 'categories', 'recent'],
    queryFn: expensesApi.recentCategories,
  })
  const accounts = useQuery({
    queryKey: ['org', organizationId, 'cash', 'accounts'],
    queryFn: cashApi.accounts,
  })
  const pots = (accounts.data?.items ?? []).filter(
    (account) => account.is_active && (account.kind === 'cash' || account.kind === 'bank'),
  )

  const [amount, setAmount] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [potId, setPotId] = useState('')
  const [note, setNote] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [more, setMore] = useState(false)
  const [date, setDate] = useState(today())
  const [period, setPeriod] = useState(thisMonth())
  const [capex, setCapex] = useState(false)
  const [months, setMonths] = useState('')
  const [credit, setCredit] = useState(false)
  const [supplierId, setSupplierId] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [allowNegative, setAllowNegative] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const suppliers = useQuery({
    queryKey: ['org', organizationId, 'inventory', 'suppliers'],
    queryFn: inventoryApi.suppliers,
    enabled: credit,
  })

  const all = useMemo(
    () => (categories.data?.items ?? []).filter((c) => c.is_active),
    [categories.data],
  )
  const chips = all.slice(0, CHIPS)
  const pot = potId || pots.find((row) => row.kind === 'cash')?.id || ''

  const save = useMutation({
    mutationFn: async () => {
      const expense = await expensesApi.create({
        category_id: categoryId,
        amount,
        expense_date: date,
        description: note.trim(),
        ...(credit ? {} : { cash_account_id: pot }),
        period,
        ...(capex
          ? { is_capex: true, ...(months ? { amortize_months: Number(months) } : {}) }
          : {}),
        ...(credit
          ? { on_credit: true, supplier_id: supplierId, ...(dueDate ? { due_date: dueDate } : {}) }
          : {}),
        ...(allowNegative ? { allow_negative: true } : {}),
      })
      if (photo) await expensesApi.uploadReceipt(expense.id, photo)
      return expense
    },
    onSuccess: () => {
      invalidateMoney(queryClient, organizationId)
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const ready =
    Number(amount) > 0 && Boolean(categoryId) && (credit ? Boolean(supplierId) : Boolean(pot))

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <form
        className="space-y-4 p-5"
        onSubmit={(event) => {
          event.preventDefault()
          if (ready) save.mutate()
        }}
      >
        <h2 className="text-base font-semibold text-slate-900">{t('Tezkor chiqim')}</h2>

        <div>
          <label htmlFor="qe-amount" className={label}>
            {t('Summa')}
          </label>
          <input
            id="qe-amount"
            autoFocus
            inputMode="numeric"
            autoComplete="off"
            value={amount ? money(Number(amount)) : ''}
            onChange={(event) => setAmount(event.target.value.replace(/\D/g, ''))}
            className="w-full rounded-xl border border-slate-200 px-4 py-3 text-right text-2xl font-bold tabular-nums outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>

        <fieldset>
          <legend className={label}>{t('Toifa')}</legend>
          <div className="flex flex-wrap gap-1.5">
            {chips.map((category) => (
              <button
                key={category.id}
                type="button"
                onClick={() => setCategoryId(category.id)}
                aria-pressed={categoryId === category.id}
                className={cn(
                  'rounded-full border px-3 py-1.5 text-sm transition',
                  categoryId === category.id
                    ? 'border-brand-500 bg-brand-50 font-semibold text-brand-700'
                    : 'border-slate-200 text-slate-700 hover:border-slate-300',
                )}
              >
                {category.parent_name ? `${category.parent_name} · ` : ''}
                {category.name}
              </button>
            ))}
          </div>
          {all.length > CHIPS && (
            <select
              aria-label={t('Boshqa toifa')}
              value={chips.some((c) => c.id === categoryId) ? '' : categoryId}
              onChange={(event) => setCategoryId(event.target.value)}
              className={cn(field, 'mt-2')}
            >
              <option value="">{t('Boshqa toifa…')}</option>
              {all.slice(CHIPS).map((category) => (
                <option key={category.id} value={category.id}>
                  {category.parent_name ? `${category.parent_name} · ` : ''}
                  {category.name}
                </option>
              ))}
            </select>
          )}
        </fieldset>

        {!credit && (
          <fieldset>
            <legend className={label}>{t('Qaysi puldan')}</legend>
            <div className="grid grid-cols-2 gap-2">
              {pots.map((row) => (
                <button
                  key={row.id}
                  type="button"
                  onClick={() => setPotId(row.id)}
                  aria-pressed={pot === row.id}
                  className={cn(
                    'rounded-lg border px-3 py-2 text-sm transition',
                    pot === row.id
                      ? 'border-brand-500 bg-brand-50 font-semibold text-brand-700'
                      : 'border-slate-200 text-slate-700',
                  )}
                >
                  {row.name}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <div className="grid grid-cols-[1fr_auto] items-end gap-2">
          <div>
            <label htmlFor="qe-note" className={label}>
              {t('Izoh')}
            </label>
            <input
              id="qe-note"
              maxLength={255}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              className={field}
            />
          </div>
          <label
            className={cn(
              'flex h-[38px] cursor-pointer items-center gap-1.5 rounded-lg border px-3 text-sm',
              photo ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-slate-200',
            )}
          >
            <Camera className="h-4 w-4" />
            {photo ? t('Chek bor') : t('Chek')}
            <input
              type="file"
              accept="image/*,application/pdf"
              capture="environment"
              className="sr-only"
              onChange={(event) => setPhoto(event.target.files?.[0] ?? null)}
            />
          </label>
        </div>

        <button
          type="button"
          onClick={() => setMore((open) => !open)}
          aria-expanded={more}
          className="flex items-center gap-1 text-xs font-medium text-slate-600"
        >
          <ChevronDown className={cn('h-3.5 w-3.5 transition', more && 'rotate-180')} />
          {t('Qoʻshimcha: sana, qaysi oy uchun, investitsiya, nasiya')}
        </button>

        {more && (
          <div className="grid gap-3 rounded-xl bg-slate-50 p-3 sm:grid-cols-2">
            <div>
              <label htmlFor="qe-date" className={label}>
                {t('Sana')}
              </label>
              <DateInput id="qe-date" value={date} onChange={(iso) => setDate(iso || today())} />
            </div>
            <div>
              <label htmlFor="qe-period" className={label}>
                {t('Qaysi oy xarajati')}
              </label>
              <input
                id="qe-period"
                type="month"
                value={period}
                onChange={(event) => setPeriod(event.target.value || thisMonth())}
                className={field}
              />
            </div>
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input type="checkbox" checked={capex} onChange={(e) => setCapex(e.target.checked)} />
              {t('Investitsiya (taʼmir, mebel, texnika) — oylik foydani buzmaydi')}
            </label>
            {capex && (
              <div className="sm:col-span-2">
                <label htmlFor="qe-months" className={label}>
                  {t('Necha oyga taqsimlash (boʻsh — alohida qator)')}
                </label>
                <input
                  id="qe-months"
                  inputMode="numeric"
                  value={months}
                  onChange={(event) => setMonths(event.target.value.replace(/\D/g, '').slice(0, 3))}
                  className={field}
                />
              </div>
            )}
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input
                type="checkbox"
                checked={credit}
                onChange={(e) => setCredit(e.target.checked)}
              />
              {t('Nasiya — pul keyin toʻlanadi')}
            </label>
            {credit && (
              <>
                <div>
                  <label htmlFor="qe-supplier" className={label}>
                    {t('Kimdan olindi')}
                  </label>
                  <select
                    id="qe-supplier"
                    value={supplierId}
                    onChange={(event) => setSupplierId(event.target.value)}
                    className={field}
                  >
                    <option value="">{t('Tanlang')}</option>
                    {(suppliers.data?.items ?? []).map((supplier) => (
                      <option key={supplier.id} value={supplier.id}>
                        {supplier.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="qe-due" className={label}>
                    {t('Toʻlash muddati')}
                  </label>
                  <DateInput id="qe-due" value={dueDate} onChange={(iso) => setDueDate(iso)} />
                </div>
              </>
            )}
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="space-y-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            <p>{error}</p>
            <label className="flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={allowNegative}
                onChange={(e) => setAllowNegative(e.target.checked)}
              />
              {t('Qopda yetmasa ham yozilsin — ogohlantirishni oʻqidim')}
            </label>
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="submit"
            disabled={!ready || save.isPending}
            className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
