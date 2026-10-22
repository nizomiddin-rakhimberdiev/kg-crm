/**
 * Kassa — pul qayerda va kimning qoʻlida (Bosqich 12.5, brif §5).
 *
 * Excel'da bank↔kassa oʻtkazmalari kirim/chiqim boʻlib yozilardi, kassa
 * qoldigʻi "tenglashtiruvchi qator" bilan nolga keltirilardi. Bu sahifada
 * har biri oʻz hujjati bilan:
 *
 * - **Topshirish** — kassir naqd pulni masʼulga beradi; qabul qiluvchi
 *   tasdiqlamaguncha pul topshiruvchida hisoblanadi.
 * - **Oʻtkazma** — inkassa yoki bankdan naqd yechish: tushum ham, xarajat
 *   ham oʻzgarmaydi.
 * - **Kunni yopish** — sanoq tizim bilan solishtiriladi; farq sababi bilan
 *   "kamomad/ortiqcha" boʻlib yoziladi.
 *
 * "Faqat oʻziniki" kassir (ADR-30) qoplar qoldigʻini koʻrmaydi — faqat
 * oʻz qoʻlidagini va oʻz topshiriqlarini.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, ArrowLeftRight, Check, HandCoins, Lock, X } from 'lucide-react'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { QueryError } from '@/components/ui/QueryError'
import { cashApi, type CashHandover } from '@/features/cash/api'
import { BankStatementPanel } from '@/features/cash/components/BankStatementPanel'
import { InTransitPanel } from '@/features/cash/components/InTransitPanel'
import { MoneyOperationsPanel } from '@/features/cash/components/MoneyOperationsPanel'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { formatDate, money, som } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const field =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'
const label = 'mb-1 block text-xs font-medium text-slate-600'
const primary =
  'rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60'

/** Oʻzbekiston soʻmi kupyuralari — sanoq oynasi uchun (Bosqich 13.3b). */
const NOTES = [200000, 100000, 50000, 20000, 10000, 5000, 2000, 1000]

const HANDOVER_STATUS: Record<CashHandover['status'], string> = {
  pending: t('Tasdiq kutilmoqda'),
  confirmed: t('Qabul qilindi'),
  rejected: t('Rad etildi'),
}

/** Faqat raqamlar saqlanadi, ekranda ajratgich bilan koʻrinadi. */
function AmountInput({
  id,
  value,
  onChange,
}: {
  id: string
  value: string
  onChange: (digits: string) => void
}) {
  return (
    <input
      id={id}
      inputMode="numeric"
      autoComplete="off"
      required
      value={value ? money(Number(value)) : ''}
      onChange={(event) => onChange(event.target.value.replace(/\D/g, ''))}
      className={cn(field, 'text-right tabular-nums')}
    />
  )
}

export default function CashPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { can } = useCan()
  const ownOnly = user?.payments_own_only ?? false
  const canManage = can('payments.update') && !ownOnly
  const key = ['org', organizationId, 'cash']

  const balances = useQuery({
    queryKey: [...key, 'balances'],
    queryFn: cashApi.balances,
    enabled: !ownOnly,
  })
  const custody = useQuery({ queryKey: [...key, 'custody'], queryFn: cashApi.custody })
  const handovers = useQuery({ queryKey: [...key, 'handovers'], queryFn: cashApi.handovers })
  const counts = useQuery({
    queryKey: [...key, 'counts'],
    queryFn: cashApi.counts,
    enabled: canManage,
  })

  const [error, setError] = useState<string | null>(null)
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))
  const done = () => {
    setError(null)
    invalidateMoney(queryClient, organizationId)
  }

  // --- Topshirish ---
  const [handOpen, setHandOpen] = useState(false)
  const [hand, setHand] = useState({ to_user_id: '', amount: '', note: '', cash_account_id: '' })
  // Ikki qop: naqd kassa va bank hisobi. Roʻyxat kassirga ham ochiq
  // (qoldiqsiz) — u kun oxirida ikkalasini ham topshiradi.
  const accounts = useQuery({ queryKey: [...key, 'accounts'], queryFn: cashApi.accounts })
  const handPots = (accounts.data?.items ?? []).filter(
    (account) => account.is_active && (account.kind === 'cash' || account.kind === 'bank'),
  )
  const receivers = useQuery({
    queryKey: [...key, 'receivers'],
    queryFn: cashApi.receivers,
    enabled: handOpen,
  })
  const handOver = useMutation({
    mutationFn: () =>
      cashApi.handOver({
        to_user_id: hand.to_user_id,
        amount: hand.amount,
        note: hand.note,
        ...(hand.cash_account_id ? { cash_account_id: hand.cash_account_id } : {}),
      }),
    onSuccess: () => {
      setHand({ to_user_id: '', amount: '', note: '', cash_account_id: '' })
      setHandOpen(false)
      done()
    },
    onError: fail,
  })
  const confirm = useMutation({
    mutationFn: (id: string) => cashApi.confirmHandover(id),
    onSuccess: done,
    onError: fail,
  })
  const [refusing, setRefusing] = useState<{ id: string; reason: string } | null>(null)
  const reject = useMutation({
    mutationFn: (draft: { id: string; reason: string }) =>
      cashApi.rejectHandover(draft.id, draft.reason),
    onSuccess: () => {
      setRefusing(null)
      done()
    },
    onError: fail,
  })

  // --- Oʻtkazma ---
  const pots = balances.data ?? []
  const [move, setMove] = useState({ from: '', to: '', amount: '', reason: '' })
  const [moveOpen, setMoveOpen] = useState(false)
  const transfer = useMutation({
    mutationFn: () =>
      cashApi.transfer({
        from_account_id: move.from,
        to_account_id: move.to,
        amount: move.amount,
        reason: move.reason,
      }),
    onSuccess: () => {
      setMove({ from: '', to: '', amount: '', reason: '' })
      setMoveOpen(false)
      done()
    },
    onError: fail,
  })

  // --- Kunni yopish ---
  // Naqd — sanoq bilan, bank — koʻchirma (vypiska) bilan solishtiriladi.
  const tills = pots
  const [count, setCount] = useState({ account: '', counted: '', reason: '' })
  // Kupyuralar boʻyicha sanoq (Bosqich 13.3b): yigʻindi oʻzi chiqadi.
  const [notes, setNotes] = useState<Record<string, string>>({})
  const setNote = (note: string, value: string) => {
    const next = { ...notes, [note]: value.replace(/\D/g, '') }
    setNotes(next)
    const total = Object.entries(next).reduce(
      (sum, [face, pieces]) => sum + Number(face) * (Number(pieces) || 0),
      0,
    )
    setCount((p) => ({ ...p, counted: total > 0 ? String(total) : '' }))
  }
  const usedNotes = Object.fromEntries(
    Object.entries(notes)
      .filter(([, pieces]) => Number(pieces) > 0)
      .map(([face, pieces]) => [face, Number(pieces)]),
  )
  const [countOpen, setCountOpen] = useState(false)
  const countPot = pots.find((pot) => pot.id === (count.account || tills[0]?.id))
  const countDiff =
    countPot && count.counted !== '' ? Number(count.counted) - Number(countPot.balance) : 0
  const closeDay = useMutation({
    mutationFn: () =>
      cashApi.closeDay({
        cash_account_id: countPot?.id ?? '',
        counted: count.counted,
        ...(Object.keys(usedNotes).length ? { denominations: usedNotes } : {}),
        ...(countDiff !== 0 ? { reason: count.reason } : {}),
      }),
    onSuccess: () => {
      setCount({ account: '', counted: '', reason: '' })
      setNotes({})
      setCountOpen(false)
      done()
    },
    onError: fail,
  })

  const allHandovers = handovers.data?.items ?? []
  const waiting = allHandovers.filter((row) => row.status === 'pending' && row.to_user === user?.id)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Kassa')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('Pul qayerda va kimning qoʻlida — har bir harakat oʻz hujjati bilan.')}
        </p>
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* Menga topshirilgan pul — birinchi navbatda, chunki u mening javobimni kutadi. */}
      {waiting.length > 0 && (
        <section className="rounded-2xl border border-orik-200 bg-orik-50 p-4">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('Sizga topshirilgan pul — tasdiqlang')}
          </h2>
          <ul className="mt-2 space-y-2">
            {waiting.map((row) => (
              <li key={row.id} className="rounded-xl bg-white px-3 py-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm text-slate-700">
                    <span className="font-semibold text-slate-900">{row.from_user_name}</span>
                    {' · '}
                    <span className="font-semibold tabular-nums">{som(row.amount)}</span>
                    {row.note && <span className="text-slate-500"> — {row.note}</span>}
                  </span>
                  <span className="flex gap-2">
                    <button
                      type="button"
                      disabled={confirm.isPending}
                      onClick={() => confirm.mutate(row.id)}
                      className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
                    >
                      <Check className="h-3.5 w-3.5" />
                      {t('Oldim')}
                    </button>
                    <button
                      type="button"
                      onClick={() => setRefusing({ id: row.id, reason: '' })}
                      className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      <X className="h-3.5 w-3.5" />
                      {t('Rad etish')}
                    </button>
                  </span>
                </div>
                {refusing?.id === row.id && (
                  <form
                    className="mt-2 flex flex-wrap items-end gap-2"
                    onSubmit={(event) => {
                      event.preventDefault()
                      reject.mutate(refusing)
                    }}
                  >
                    <div className="min-w-0 flex-1">
                      <label htmlFor={`refuse-${row.id}`} className={label}>
                        {t('Sabab (majburiy)')}
                      </label>
                      <input
                        id={`refuse-${row.id}`}
                        required
                        maxLength={255}
                        value={refusing.reason}
                        onChange={(event) =>
                          setRefusing({ id: row.id, reason: event.target.value })
                        }
                        className={field}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={reject.isPending || !refusing.reason.trim()}
                      className={primary}
                    >
                      {t('Rad etish')}
                    </button>
                  </form>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Qoplar */}
      {!ownOnly && (
        <section>
          {balances.isError ? (
            <QueryError error={balances.error} onRetry={() => void balances.refetch()} />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {pots.map((pot) => {
                const negative = Number(pot.balance) < 0
                return (
                  <div
                    key={pot.id}
                    className={cn(
                      'rounded-2xl border bg-white px-4 py-3',
                      negative ? 'border-red-300' : 'border-slate-200',
                    )}
                  >
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      {pot.name}
                    </p>
                    <p
                      className={cn(
                        'mt-1 text-2xl font-bold tabular-nums',
                        negative ? 'text-red-700' : 'text-slate-900',
                      )}
                    >
                      {som(pot.balance)}
                    </p>
                    {Number(pot.in_transit ?? 0) > 0 && (
                      <p className="mt-1 text-xs text-slate-600">
                        {t('Tushgan {arrived} · yoʻlda {transit}', {
                          arrived: som(pot.arrived ?? pot.balance),
                          transit: som(pot.in_transit ?? 0),
                        })}
                      </p>
                    )}
                    {negative && (
                      <p className="mt-1 flex items-start gap-1.5 text-xs text-red-700">
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        {t(
                          'Manfiy qoldiq — qaysidir kirim yozilmagan. Boshlangʻich qoldiq yoki tuzatishni tekshiring.',
                        )}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )}

      {/* Yoʻldagi pul (Bosqich 13.2c) — boʻlsa koʻrinadi. */}
      <InTransitPanel canSettle={canManage} />

      {/* Bank koʻchirmasi (Bosqich 13.3d) — qoldiqlardan KEYIN, lekin
          kunni yopish va tarixdan OLDIN (audit, 2026-10-21): u
          sahifaning eng pastida, ikki ming piksel ostida turardi va
          mijoz yuklash joyini topa olmadi. Ko'chirma bank qoldigʻini
          haqiqat bilan solishtiradi, ya'ni uning joyi qoldiq
          yonida. */}
      {canManage && <BankStatementPanel />}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Kimning qoʻlida */}
        <section className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-900">
              {ownOnly ? t('Mening qoʻlimda') : t('Pul kimning javobgarligida')}
            </h2>
            {can('payments.create') && !handOpen && (
              <button
                type="button"
                onClick={() => setHandOpen(true)}
                className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-brand-700 hover:bg-brand-50"
              >
                <HandCoins className="h-4 w-4" />
                {t('Pulni topshirish')}
              </button>
            )}
          </div>
          {custody.isError ? (
            <QueryError error={custody.error} onRetry={() => void custody.refetch()} />
          ) : (custody.data ?? []).length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              {t('Hech kimning javobgarligida pul yoʻq.')}
            </p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500">
                    <th className="py-1.5 font-medium">{t('Kim')}</th>
                    <th className="py-1.5 text-right font-medium">{t('Naqd')}</th>
                    <th className="py-1.5 text-right font-medium">{t('Bank hisobi')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {(custody.data ?? []).map((row) => (
                    <tr key={row.user_id}>
                      <td className="py-2 text-slate-700">{row.full_name}</td>
                      <td className="py-2 text-right font-semibold tabular-nums text-slate-900">
                        {som(row.cash)}
                      </td>
                      <td className="py-2 text-right font-semibold tabular-nums text-slate-900">
                        {som(row.bank)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {handOpen && (
            <form
              className="mt-3 grid gap-2 border-t border-slate-100 pt-3 sm:grid-cols-2"
              onSubmit={(event) => {
                event.preventDefault()
                handOver.mutate()
              }}
            >
              <div>
                <label htmlFor="hand-to" className={label}>
                  {t('Kimga')}
                </label>
                <select
                  id="hand-to"
                  required
                  value={hand.to_user_id}
                  onChange={(event) => setHand((p) => ({ ...p, to_user_id: event.target.value }))}
                  className={field}
                >
                  <option value="">{t('Masʼul shaxsni tanlang')}</option>
                  {(receivers.data ?? []).map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.full_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="hand-pot" className={label}>
                  {t('Qaysi pul')}
                </label>
                <select
                  id="hand-pot"
                  value={
                    hand.cash_account_id || handPots.find((pot) => pot.kind === 'cash')?.id || ''
                  }
                  onChange={(event) =>
                    setHand((p) => ({ ...p, cash_account_id: event.target.value }))
                  }
                  className={field}
                >
                  {handPots.map((pot) => (
                    <option key={pot.id} value={pot.id}>
                      {pot.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="hand-amount" className={label}>
                  {t('Summa')}
                </label>
                <AmountInput
                  id="hand-amount"
                  value={hand.amount}
                  onChange={(digits) => setHand((p) => ({ ...p, amount: digits }))}
                />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="hand-note" className={label}>
                  {t('Izoh')}
                </label>
                <input
                  id="hand-note"
                  maxLength={255}
                  value={hand.note}
                  onChange={(event) => setHand((p) => ({ ...p, note: event.target.value }))}
                  className={field}
                />
              </div>
              <p className="text-xs text-slate-500 sm:col-span-2">
                {t('Qabul qiluvchi tasdiqlamaguncha pul sizda hisoblanadi.')}
              </p>
              <div className="flex justify-end gap-2 sm:col-span-2">
                <button
                  type="button"
                  onClick={() => setHandOpen(false)}
                  className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
                >
                  {t('Bekor qilish')}
                </button>
                <button
                  type="submit"
                  disabled={handOver.isPending || !hand.to_user_id || !hand.amount}
                  className={primary}
                >
                  {t('Topshirish')}
                </button>
              </div>
            </form>
          )}
        </section>

        {/* Oʻtkazma va kunni yopish — butun qopga tegadi */}
        {canManage && (
          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setMoveOpen((open) => !open)}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium',
                  moveOpen
                    ? 'border-brand-300 bg-brand-50 text-brand-700'
                    : 'border-slate-200 text-slate-700 hover:bg-slate-50',
                )}
              >
                <ArrowLeftRight className="h-4 w-4" />
                {t('Oʻtkazma')}
              </button>
              <button
                type="button"
                onClick={() => setCountOpen((open) => !open)}
                className={cn(
                  'flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-medium',
                  countOpen
                    ? 'border-brand-300 bg-brand-50 text-brand-700'
                    : 'border-slate-200 text-slate-700 hover:bg-slate-50',
                )}
              >
                <Lock className="h-4 w-4" />
                {t('Kunni yopish')}
              </button>
            </div>

            {moveOpen && (
              <form
                className="grid gap-2 sm:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  transfer.mutate()
                }}
              >
                <p className="text-xs text-slate-500 sm:col-span-2">
                  {t('Inkassa, bankdan naqd yechish — tushum ham, xarajat ham oʻzgarmaydi.')}
                </p>
                <div>
                  <label htmlFor="move-from" className={label}>
                    {t('Qaysi hisobdan')}
                  </label>
                  <select
                    id="move-from"
                    required
                    value={move.from}
                    onChange={(event) => setMove((p) => ({ ...p, from: event.target.value }))}
                    className={field}
                  >
                    <option value="">{t('Tanlang')}</option>
                    {pots.map((pot) => (
                      <option key={pot.id} value={pot.id}>
                        {pot.name} · {som(pot.balance)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="move-to" className={label}>
                    {t('Qaysi hisobga')}
                  </label>
                  <select
                    id="move-to"
                    required
                    value={move.to}
                    onChange={(event) => setMove((p) => ({ ...p, to: event.target.value }))}
                    className={field}
                  >
                    <option value="">{t('Tanlang')}</option>
                    {pots
                      .filter((pot) => pot.id !== move.from)
                      .map((pot) => (
                        <option key={pot.id} value={pot.id}>
                          {pot.name}
                        </option>
                      ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="move-amount" className={label}>
                    {t('Summa')}
                  </label>
                  <AmountInput
                    id="move-amount"
                    value={move.amount}
                    onChange={(digits) => setMove((p) => ({ ...p, amount: digits }))}
                  />
                </div>
                <div>
                  <label htmlFor="move-reason" className={label}>
                    {t('Asos')}
                  </label>
                  <input
                    id="move-reason"
                    required
                    maxLength={255}
                    placeholder={t('Inkassa')}
                    value={move.reason}
                    onChange={(event) => setMove((p) => ({ ...p, reason: event.target.value }))}
                    className={field}
                  />
                </div>
                <div className="flex justify-end sm:col-span-2">
                  <button
                    type="submit"
                    disabled={
                      transfer.isPending ||
                      !move.from ||
                      !move.to ||
                      !move.amount ||
                      !move.reason.trim()
                    }
                    className={primary}
                  >
                    {t('Oʻtkazish')}
                  </button>
                </div>
              </form>
            )}

            {countOpen && countPot && (
              <form
                className="grid gap-2 sm:grid-cols-2"
                onSubmit={(event) => {
                  event.preventDefault()
                  closeDay.mutate()
                }}
              >
                {tills.length > 1 && (
                  <div className="sm:col-span-2">
                    <label htmlFor="count-pot" className={label}>
                      {t('Hisob')}
                    </label>
                    <select
                      id="count-pot"
                      value={countPot.id}
                      onChange={(event) => setCount((p) => ({ ...p, account: event.target.value }))}
                      className={field}
                    >
                      {tills.map((pot) => (
                        <option key={pot.id} value={pot.id}>
                          {pot.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <p className={label}>{t('Tizimda')}</p>
                  <p className="py-2 text-sm font-semibold tabular-nums text-slate-900">
                    {som(countPot.balance)}
                  </p>
                </div>
                <div>
                  <label htmlFor="count-counted" className={label}>
                    {t('Sanaldi')}
                  </label>
                  <AmountInput
                    id="count-counted"
                    value={count.counted}
                    onChange={(digits) => {
                      setNotes({})
                      setCount((p) => ({ ...p, counted: digits }))
                    }}
                  />
                </div>
                {countPot.kind === 'cash' && (
                  <details className="sm:col-span-2">
                    <summary className="cursor-pointer text-xs font-medium text-slate-600">
                      {t('Kupyuralar boʻyicha sanash')}
                    </summary>
                    <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4">
                      {NOTES.map((face) => (
                        <div key={face}>
                          <label htmlFor={`note-${face}`} className={label}>
                            {money(face)}
                          </label>
                          <input
                            id={`note-${face}`}
                            inputMode="numeric"
                            value={notes[String(face)] ?? ''}
                            onChange={(event) => setNote(String(face), event.target.value)}
                            className={cn(field, 'text-right tabular-nums')}
                          />
                        </div>
                      ))}
                    </div>
                  </details>
                )}
                {count.counted !== '' && countDiff !== 0 && (
                  <div className="sm:col-span-2">
                    <p
                      className={cn(
                        'mb-1 text-sm font-semibold tabular-nums',
                        countDiff < 0 ? 'text-red-700' : 'text-orik-700',
                      )}
                    >
                      {countDiff < 0
                        ? t('Kamomad: {money}', { money: som(-countDiff) })
                        : t('Ortiqcha: {money}', { money: som(countDiff) })}
                    </p>
                    <label htmlFor="count-reason" className={label}>
                      {t('Sabab (majburiy)')}
                    </label>
                    <input
                      id="count-reason"
                      required
                      maxLength={255}
                      value={count.reason}
                      onChange={(event) => setCount((p) => ({ ...p, reason: event.target.value }))}
                      className={field}
                    />
                  </div>
                )}
                <div className="flex justify-end sm:col-span-2">
                  <button
                    type="submit"
                    disabled={
                      closeDay.isPending ||
                      count.counted === '' ||
                      (countDiff !== 0 && !count.reason.trim())
                    }
                    className={primary}
                  >
                    {t('Kunni yopish')}
                  </button>
                </div>
              </form>
            )}

            {(counts.data?.items ?? []).length > 0 && (
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('Yopilgan kunlar')}
                </h3>
                <ul className="mt-1 divide-y divide-slate-100 text-sm">
                  {(counts.data?.items ?? []).map((row) => {
                    const diff = Number(row.difference)
                    return (
                      <li key={row.id} className="py-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-slate-700">
                            {formatDate(row.counted_on)} · {row.cash_account_name}
                          </span>
                          <span
                            className={cn(
                              'font-semibold tabular-nums',
                              diff < 0
                                ? 'text-red-700'
                                : diff > 0
                                  ? 'text-orik-700'
                                  : 'text-emerald-700',
                            )}
                          >
                            {diff === 0 ? t('Toʻgʻri') : som(row.difference)}
                          </span>
                        </div>
                        {row.reason && <p className="text-xs text-slate-500">{row.reason}</p>}
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}
          </section>
        )}
      </div>

      {/* Topshiriqlar tarixi */}
      {allHandovers.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">{t('Topshiriqlar')}</h2>
          <ul className="mt-2 divide-y divide-slate-100 text-sm">
            {allHandovers.map((row) => (
              <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span className="text-slate-700">
                  {row.from_user_name} → {row.to_user_name}
                  <span className="block text-xs text-slate-500">
                    {formatDate(row.created_at)}
                    {row.decision_note && ` · ${row.decision_note}`}
                  </span>
                </span>
                <span className="flex items-center gap-2">
                  <span className="font-semibold tabular-nums text-slate-900">
                    {som(row.amount)}
                  </span>
                  <span
                    className={cn(
                      'rounded-full px-2 py-0.5 text-xs font-medium',
                      row.status === 'confirmed' && 'bg-emerald-50 text-emerald-700',
                      row.status === 'pending' && 'bg-orik-50 text-orik-700',
                      row.status === 'rejected' && 'bg-red-50 text-red-700',
                    )}
                  >
                    {HANDOVER_STATUS[row.status]}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {/* Subsidiya, egaga toʻlov, kredit, soliq (Bosqich 13.2b). */}
      {canManage && <MoneyOperationsPanel />}
    </div>
  )
}
