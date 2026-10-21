/**
 * Xarajat ham, ota-ona toʻlovi ham boʻlmagan pul (Bosqich 13.2b):
 * boshqa daromad, egaga toʻlov (dividend — soligʻi bilan), egadan kiritma,
 * kredit, soliq toʻlovi. Egaga toʻlov xarajat emas — foyda-zararga
 * kirmaydi, pul oqimida alohida qator.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Landmark } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { DateInput } from '@/components/ui/DateInput'
import { cashApi, type OperationKind } from '@/features/cash/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { formatDate, money, som, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { MonthInput } from '@/components/ui/MonthInput'

const field =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'
const label = 'mb-1 block text-xs font-medium text-slate-600'

const KINDS: Array<{ kind: OperationKind; label: string; incoming: boolean }> = [
  { kind: 'other_income', label: t('Boshqa daromad'), incoming: true },
  { kind: 'owner_draw', label: t('Egasiga toʻlov'), incoming: false },
  { kind: 'owner_contribution', label: t('Egadan kiritma'), incoming: true },
  { kind: 'loan_in', label: t('Kredit olindi'), incoming: true },
  { kind: 'loan_repay', label: t('Kredit qaytarildi'), incoming: false },
  { kind: 'tax_payment', label: t('Soliq toʻlovi'), incoming: false },
]

const SUBTYPES: Partial<Record<OperationKind, Array<[string, string]>>> = {
  other_income: [
    ['subsidy', t('Davlat subsidiyasi')],
    ['club', t('Qoʻshimcha toʻgarak')],
    ['rent', t('Ijara')],
    ['other', t('Boshqa')],
  ],
  owner_draw: [
    ['dividend', t('Dividend (MChJ)')],
    ['draw', t('Egasining olishi (YaTT)')],
  ],
  tax_payment: [
    ['dividend_tax', t('Dividend soligʻi')],
    ['social_tax', t('Ijtimoiy soliq')],
    ['income_tax', t('JShDS')],
    ['other', t('Boshqa')],
  ],
}

const KIND_LABEL = Object.fromEntries(KINDS.map((row) => [row.kind, row.label]))

export function MoneyOperationsPanel() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const key = ['org', organizationId, 'cash', 'operations']
  const operations = useQuery({ queryKey: key, queryFn: cashApi.operations })
  const accounts = useQuery({
    queryKey: ['org', organizationId, 'cash', 'accounts'],
    queryFn: cashApi.accounts,
  })
  const pots = (accounts.data?.items ?? []).filter(
    (account) => account.is_active && (account.kind === 'cash' || account.kind === 'bank'),
  )

  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    kind: 'other_income' as OperationKind,
    subtype: 'subsidy',
    pot: '',
    amount: '',
    date: today(),
    reason: '',
    period: '',
  })
  const [error, setError] = useState<string | null>(null)
  const subtypes = SUBTYPES[form.kind] ?? []
  const pot = form.pot || pots.find((row) => row.kind === 'bank')?.id || ''

  const create = useMutation({
    mutationFn: () =>
      cashApi.createOperation({
        kind: form.kind,
        subtype: subtypes.length ? form.subtype : '',
        cash_account_id: pot,
        amount: form.amount,
        occurred_on: form.date,
        reason: form.reason.trim(),
        ...(form.kind === 'other_income' && form.period ? { period: form.period } : {}),
      }),
    onSuccess: () => {
      setOpen(false)
      setError(null)
      setForm((p) => ({ ...p, amount: '', reason: '', period: '' }))
      invalidateMoney(queryClient, organizationId)
      void queryClient.invalidateQueries({ queryKey: key })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const rows = operations.data?.items ?? []

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Landmark className="h-4 w-4 text-slate-500" />
            {t('Boshqa pul harakatlari')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('Subsidiya, egaga toʻlov, egadan kiritma, kredit, soliq — xarajat emas.')}
          </p>
        </div>
        {!open && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-lg px-2.5 py-1.5 text-sm font-medium text-brand-700 hover:bg-brand-50"
          >
            {t('Qoʻshish')}
          </button>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {open && (
        <form
          className="mt-3 grid gap-2 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault()
            create.mutate()
          }}
        >
          <div>
            <label htmlFor="op-kind" className={label}>
              {t('Turi')}
            </label>
            <select
              id="op-kind"
              value={form.kind}
              onChange={(event) => {
                const kind = event.target.value as OperationKind
                setForm((p) => ({ ...p, kind, subtype: SUBTYPES[kind]?.[0]?.[0] ?? '' }))
              }}
              className={field}
            >
              {KINDS.map((row) => (
                <option key={row.kind} value={row.kind}>
                  {row.label}
                </option>
              ))}
            </select>
          </div>
          {subtypes.length > 0 && (
            <div>
              <label htmlFor="op-subtype" className={label}>
                {t('Aniqroq')}
              </label>
              <select
                id="op-subtype"
                value={form.subtype}
                onChange={(event) => setForm((p) => ({ ...p, subtype: event.target.value }))}
                className={field}
              >
                {subtypes.map(([value, text]) => (
                  <option key={value} value={value}>
                    {text}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label htmlFor="op-amount" className={label}>
              {t('Summa')}
            </label>
            <input
              id="op-amount"
              required
              inputMode="numeric"
              value={form.amount ? money(Number(form.amount)) : ''}
              onChange={(event) =>
                setForm((p) => ({ ...p, amount: event.target.value.replace(/\D/g, '') }))
              }
              className={cn(field, 'text-right tabular-nums')}
            />
          </div>
          <div>
            <label htmlFor="op-pot" className={label}>
              {KINDS.find((row) => row.kind === form.kind)?.incoming
                ? t('Qayerga tushdi')
                : t('Qaysi puldan')}
            </label>
            <select
              id="op-pot"
              value={pot}
              onChange={(event) => setForm((p) => ({ ...p, pot: event.target.value }))}
              className={field}
            >
              {pots.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="op-date" className={label}>
              {t('Sana')}
            </label>
            <DateInput
              id="op-date"
              value={form.date}
              onChange={(iso) => setForm((p) => ({ ...p, date: iso || today() }))}
            />
          </div>
          {form.kind === 'other_income' && (
            <MonthInput
              id="op-period"
              label={t('Qaysi oy uchun')}
              value={form.period}
              onChange={(value) => setForm((p) => ({ ...p, period: value }))}
            />
          )}
          <div className="sm:col-span-2">
            <label htmlFor="op-reason" className={label}>
              {t('Asos (majburiy)')}
            </label>
            <input
              id="op-reason"
              required
              maxLength={255}
              value={form.reason}
              onChange={(event) => setForm((p) => ({ ...p, reason: event.target.value }))}
              className={field}
            />
          </div>
          {form.kind === 'owner_draw' && form.subtype === 'dividend' && (
            <p className="text-xs text-slate-500 sm:col-span-2">
              {t('Dividend soligʻi (sozlamadagi foiz) majburiyat boʻlib yoziladi.')}
            </p>
          )}
          <div className="flex justify-end gap-2 sm:col-span-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={create.isPending || !form.amount || !form.reason.trim() || !pot}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {t('Saqlash')}
            </button>
          </div>
        </form>
      )}

      {rows.length > 0 && (
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {rows.map((row) => {
            const incoming = KINDS.find((item) => item.kind === row.kind)?.incoming
            return (
              <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="min-w-0">
                  <span className="block text-slate-700">
                    {KIND_LABEL[row.kind] ?? row.kind} — {row.reason}
                  </span>
                  <span className="text-xs text-slate-500">
                    {formatDate(row.occurred_on)} · {row.cash_account_name}
                    {Number(row.tax_amount) > 0 &&
                      ` · ${t('soliq {money}', { money: som(row.tax_amount) })}`}
                  </span>
                </span>
                <span
                  className={cn(
                    'font-semibold tabular-nums',
                    incoming ? 'text-emerald-700' : 'text-slate-900',
                  )}
                >
                  {incoming ? '+' : '−'}
                  {som(row.amount)}
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
