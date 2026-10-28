/**
 * Oylik maosh (docs/04 §11).
 *
 * Oqim bir tomonlama: qoralama → yakunlangan → to'langan. Yakunlangandan
 * keyin tahrirlash yo'q — xato keyingi oyda tuzatuvchi bonus/ushlab qolish
 * bilan hal qilinadi. Bu ledger'dagi qarshi yozuv bilan bir xil mantiq.
 *
 * Xodimlar ro'yxati bu yerda EMAS — u "Xodimlar" sahifasida
 * (`features/staff`). Oylik faqat hisoblashlar bilan ishlaydi.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowUpRight,
  Banknote,
  CheckCircle2,
  Lock,
  Plus,
  RefreshCw,
  Trash2,
  Unlock,
  Wallet,
} from 'lucide-react'
import { DateInput } from '@/components/ui/DateInput'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { QueryError } from '@/components/ui/QueryError'
import { EmptyRow } from '@/components/ui/EmptyState'
import { Modal } from '@/components/ui/Modal'
import { employeesApi } from '@/features/staff/api'
import { payrollApi, type PayoutLine } from '@/features/payroll/api'
import { PayslipModal } from '@/features/payroll/components/PayslipModal'
import { invalidateMoney } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type PayrollItem, type PayrollRun } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate } from '@/lib/utils'
import { cashApi } from '@/features/cash/api'
import { PayoutModal } from '@/features/payroll/components/PayoutModal'
import { money, monthLabel } from '@/lib/format'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'

const STATUS = {
  draft: [t('Qoralama'), 'bg-slate-100 text-slate-600'],
  finalized: [t('Yakunlangan'), 'border border-ildiz-300 bg-ildiz-50 text-ildiz-800'],
  paid: [t('Toʻlangan'), 'bg-emerald-50 text-emerald-700'],
} as const

export default function PayrollPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const now = new Date()
  const [openRun, setOpenRun] = useState<string | null>(null)
  const [advanceForm, setAdvanceForm] = useState({
    employee_id: '',
    amount: '',
    paid_on: new Date().toISOString().slice(0, 10),
    note: '',
    // Avans QAYSI qopdan berildi (ADR-29). Ilgari u hamisha naqd
    // kassadan yechilardi va buni hech kim tanlamasdi.
    cash_account_id: '',
  })
  const [error, setError] = useState<string | null>(null)
  // Qayta ochish oynasi: qaysi hisoblash va nima sababdan.
  const [reopening, setReopening] = useState<PayrollRun | null>(null)
  const [reopenReason, setReopenReason] = useState('')
  // Oylik varaqasi — rasmiy/naqd bo'linishi (ADR-18).
  const [payslip, setPayslip] = useState<PayrollItem | null>(null)

  const runsQuery = useQuery({
    queryKey: queryKeys.payrollRuns(organizationId),
    queryFn: () => payrollApi.listRuns(),
  })
  const runQuery = useQuery({
    queryKey: queryKeys.payrollRun(organizationId, openRun ?? ''),
    queryFn: () => payrollApi.getRun(openRun!),
    enabled: Boolean(openRun),
  })

  // Oylik to'lash kassadan pul chiqaradi va foyda-zararga tushadi.
  const invalidate = () => invalidateMoney(queryClient, organizationId)
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const createRun = useMutation({
    mutationFn: () => payrollApi.createRun(now.getFullYear(), now.getMonth() + 1),
    onSuccess: (run) => {
      setError(null)
      setOpenRun(run.id)
      invalidate()
    },
    onError: fail,
  })
  const finalize = useMutation({
    mutationFn: (id: string) => payrollApi.finalize(id),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })
  // Avanslar — oy davomida berib yuborilgan pul. Ular oylik hisoblashga
  // sana bo'yicha tushadi (docs/03), shuning uchun ro'yxat shu sahifada:
  // "qancha berdim?" va "oy oxirida qancha qoldi?" bitta ekranda.
  const employeesQuery = useQuery({
    queryKey: queryKeys.employees(organizationId, { page_size: 200 }),
    queryFn: () => employeesApi.list({ page_size: 200 }),
    enabled: can('payroll.read'),
  })

  const cashAccounts = useQuery({
    queryKey: ['org', organizationId, 'cash-accounts'],
    queryFn: () => cashApi.accounts(),
    enabled: can('payroll.create'),
  })

  const advancesQuery = useQuery({
    queryKey: queryKeys.payrollAdvances(organizationId),
    queryFn: () => payrollApi.listAdvances({ page_size: 50 }),
    enabled: can('payroll.read'),
  })

  const addAdvance = useMutation({
    mutationFn: () =>
      payrollApi.createAdvance({
        employee_id: advanceForm.employee_id,
        amount: advanceForm.amount,
        paid_on: advanceForm.paid_on,
        note: advanceForm.note,
        ...(advanceForm.cash_account_id ? { cash_account_id: advanceForm.cash_account_id } : {}),
      }),
    onSuccess: () => {
      setAdvanceForm((prev) => ({ ...prev, amount: '', note: '' }))
      invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const removeAdvance = useMutation({
    mutationFn: (id: string) => payrollApi.removeAdvance(id),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const recalculate = useMutation({
    mutationFn: (id: string) => payrollApi.recalculate(id),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  // Qayta ochish — yakunlangan hisoblashdagi xatoni tuzatishning YAGONA
  // yo'li. Sabab majburiy: yakunlangan hujjatni ochish izsiz qolmasin.
  const reopen = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => payrollApi.reopen(id, reason),
    onSuccess: () => {
      setError(null)
      setReopening(null)
      setReopenReason('')
      invalidate()
    },
    onError: fail,
  })

  /*
   * To'lov endi OYNA orqali (ADR-29): qaysi qopdan chiqishi
   * ko'rsatiladi va qoldiq yetmasa so'raydi. Ilgari tugma darhol
   * yuborardi va pul foydalanuvchi tanlamagan qopdan chiqib ketardi.
   */
  const [payingRun, setPayingRun] = useState<PayrollRun | null>(null)
  const markPaid = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string
      payload: { payouts: PayoutLine[]; allow_negative: boolean }
    }) => payrollApi.markPaid(id, payload),
    onSuccess: () => {
      setError(null)
      setPayingRun(null)
      invalidate()
    },
    onError: fail,
  })
  const updateItem = useMutation({
    mutationFn: ({ itemId, field, value }: { itemId: string; field: string; value: string }) =>
      payrollApi.updateItem(openRun!, itemId, { [field]: value || '0' }),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const run: PayrollRun | undefined = runQuery.data
  // Oy nomi bilan: "2026-10 uchun hisoblash" raqamli kod kabi o'qiladi,
  // holbuki bu mudira uchun oddiy "Oktabr 2026" (PLAN 10.9).
  const currentPeriod = monthLabel(now.getFullYear(), now.getMonth() + 1)
  // Ochiq hisoblashdagi avanslar yig'indisi — sarlavhadagi tenglama uchun.
  const advanceTotal = (run?.items ?? []).reduce((sum, item) => sum + Number(item.advance), 0)

  return (
    <div className="space-y-6">
      {/* Qayta ochish — sabab MAJBURIY: yakunlangan hujjat jimgina
          ochilmasin, audit jurnalida "nega ochildi?" javobsiz qolmasin. */}
      <Modal open={Boolean(reopening)} onClose={() => setReopening(null)} className="max-w-md">
        <form
          className="p-6"
          onSubmit={(event) => {
            event.preventDefault()
            if (reopening) reopen.mutate({ id: reopening.id, reason: reopenReason })
          }}
        >
          {/* `pr-10` — sarlavha yopish tugmasining ostiga kirmasin. */}
          <h2 className="pr-10 text-lg font-bold text-slate-900">
            {t('Hisoblashni qayta ochish')}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {reopening &&
              t('{period} — qoralamaga qaytariladi va yana tahrirlanadi.', {
                period: monthLabel(reopening.period_year, reopening.period_month),
              })}
          </p>
          {reopening?.status === 'paid' && (
            <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {t(
                'Bu hisoblash toʻlangan deb belgilangan. Pul allaqachon berilgan boʻlsa, oʻzgartirish kiritishdan oldin xodim bilan kelishing.',
              )}
            </p>
          )}
          <label htmlFor="reopen-reason" className="mt-4 block text-xs font-medium text-slate-600">
            {t('Sabab')}
          </label>
          <input
            id="reopen-reason"
            required
            autoFocus
            value={reopenReason}
            onChange={(event) => setReopenReason(event.target.value)}
            placeholder={t('Masalan: bonus kiritilmay qolgan')}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none"
          />
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setReopening(null)}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={reopen.isPending || !reopenReason.trim()}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
            >
              {t('Qayta ochish')}
            </button>
          </div>
        </form>
      </Modal>

      <PayslipModal item={payslip} onClose={() => setPayslip(null)} />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Oylik maosh')}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {t(
              'Yakunlangan hisoblashni tahrirlash uchun avval qoralamaga qaytaring — sabab soʻraladi.',
            )}
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {can('payroll.read') && (
            <Link
              to="/staff"
              className="inline-flex min-h-11 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              {t('Xodimlar roʻyxati')}
              <ArrowUpRight className="h-4 w-4 text-slate-500" />
            </Link>
          )}
          {can('payroll.create') && (
            <button
              type="button"
              onClick={() => createRun.mutate()}
              disabled={createRun.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              <Plus className="h-4 w-4" />
              {t('{period} uchun hisoblash', { period: currentPeriod })}
            </button>
          )}
        </div>
      </div>

      {/* Avanslar — oy davomida berilgan pul. Hisoblash oy oxirida
          yaratiladi, avans esa undan oldin beriladi: shuning uchun u
          alohida yoziladi va sana bo'yicha o'sha oyning hisoblashiga
          o'zi tushadi. */}
      {can('payroll.read') && (
        <details className="rounded-2xl border border-slate-200 bg-white" open={false}>
          <summary className="flex cursor-pointer items-center gap-2 px-4 py-3 text-sm font-semibold text-slate-800">
            <Banknote className="h-4 w-4 text-slate-500" />
            {t('Avanslar')}
            {(advancesQuery.data?.items.length ?? 0) > 0 && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                {advancesQuery.data?.items.length}
              </span>
            )}
          </summary>

          <div className="border-t border-slate-100 p-4">
            {can('payroll.create') && (
              <form
                onSubmit={(event) => {
                  event.preventDefault()
                  addAdvance.mutate()
                }}
                className="grid gap-3 sm:grid-cols-[1.4fr_1fr_1fr_1.4fr_auto]"
              >
                <div>
                  <label
                    htmlFor="adv-emp"
                    className="mb-1 block text-xs font-medium text-slate-600"
                  >
                    {t('Xodim')}
                  </label>
                  <Select
                    id="adv-emp"
                    required
                    value={advanceForm.employee_id}
                    onChange={(e) =>
                      setAdvanceForm((prev) => ({ ...prev, employee_id: e.target.value }))
                    }
                    className="w-full"
                  >
                    <option value="">{t('Tanlang…')}</option>
                    {employeesQuery.data?.items.map((employee) => (
                      <option key={employee.id} value={employee.id}>
                        {employee.full_name}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label
                    htmlFor="adv-amt"
                    className="mb-1 block text-xs font-medium text-slate-600"
                  >
                    {t('Summa')}
                  </label>
                  <input
                    id="adv-amt"
                    type="number"
                    required
                    min="1"
                    value={advanceForm.amount}
                    onChange={(e) =>
                      setAdvanceForm((prev) => ({ ...prev, amount: e.target.value }))
                    }
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label
                    htmlFor="adv-date"
                    className="mb-1 block text-xs font-medium text-slate-600"
                  >
                    {t('Sana')}
                  </label>
                  <DateInput
                    id="adv-date"
                    required
                    value={advanceForm.paid_on}
                    onChange={(iso) => setAdvanceForm((prev) => ({ ...prev, paid_on: iso }))}
                  />
                </div>
                <div>
                  <label
                    htmlFor="adv-account"
                    className="mb-1 block text-xs font-medium text-slate-600"
                  >
                    {t('Qaysi hisobdan')}
                  </label>
                  <Select
                    id="adv-account"
                    value={advanceForm.cash_account_id}
                    onChange={(e) =>
                      setAdvanceForm((prev) => ({ ...prev, cash_account_id: e.target.value }))
                    }
                    className="w-full"
                  >
                    <option value="">{t('Naqd kassa')}</option>
                    {cashAccounts.data?.items.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label
                    htmlFor="adv-note"
                    className="mb-1 block text-xs font-medium text-slate-600"
                  >
                    {t('Izoh')}
                  </label>
                  <input
                    id="adv-note"
                    maxLength={255}
                    value={advanceForm.note}
                    onChange={(e) => setAdvanceForm((prev) => ({ ...prev, note: e.target.value }))}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={addAdvance.isPending}
                    className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
                  >
                    <Plus className="h-4 w-4" /> {t('Qoʻshish')}
                  </button>
                </div>
              </form>
            )}

            <ul className="mt-4 divide-y divide-slate-100">
              {advancesQuery.data?.items.map((advance) => (
                <li key={advance.id} className="flex items-center justify-between gap-3 py-2">
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-slate-800">
                      {advance.employee_name}
                    </span>
                    {/* Pul QAYSI hisobdan chiqqani (mijoz soʻrovi,
                        2026-10-28): forma buni soʻrardi, roʻyxat esa
                        aytmasdi — ya'ni javob yozilgan, lekin
                        koʻrinmaydigan joyda edi. */}
                    <span className="text-xs text-slate-500">
                      {formatDate(advance.paid_on)}
                      {` · ${advance.cash_account_name ?? t('Naqd kassa')}`}
                      {advance.note ? ` · ${advance.note}` : ''}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <span className="text-sm font-semibold tabular-nums text-slate-700">
                      {money(advance.amount)}
                    </span>
                    {can('payroll.delete') && (
                      <button
                        type="button"
                        onClick={() => removeAdvance.mutate(advance.id)}
                        title={t('Oʻchirish')}
                        aria-label={t('Oʻchirish')}
                        className="rounded-lg p-1.5 text-slate-300 transition hover:bg-red-50 hover:text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </span>
                </li>
              ))}
              {advancesQuery.data?.items.length === 0 && (
                <li className="py-4 text-center text-sm text-slate-500">
                  {t('Hozircha avans berilmagan.')}
                </li>
              )}
            </ul>
          </div>
        </details>
      )}

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {runsQuery.data?.items.map((r) => {
          const [label, tone] = STATUS[r.status]
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => setOpenRun(r.id)}
              className={cn(
                'rounded-2xl border bg-white p-4 text-left transition hover:border-brand-300',
                openRun === r.id ? 'border-brand-400 ring-2 ring-brand-100' : 'border-slate-200',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold text-slate-900">
                  {monthLabel(r.period_year, r.period_month)}
                </p>
                <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                  {label}
                </span>
              </div>
              <p className="mt-2 text-lg font-bold text-slate-900 tabular-nums">
                {t('{money} soʻm', { money: money(r.total_net) })}
              </p>
              <p className="text-xs text-slate-500">
                {t('{length} ta xodim', { length: r.items.length })}
              </p>
            </button>
          )
        })}
      </div>

      {runsQuery.isError && (
        <QueryError
          error={runsQuery.error}
          onRetry={() => runsQuery.refetch()}
          className="rounded-2xl border border-slate-200 bg-white"
        />
      )}

      {runsQuery.data?.items.length === 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center">
          <Wallet className="mx-auto mb-3 h-10 w-10 text-slate-200" />
          <p className="text-sm text-slate-500">{t('Hozircha hisoblash yoʻq.')}</p>
          <p className="mt-1 text-xs text-slate-500">
            {t('Avval')}{' '}
            <Link to="/staff" className="font-medium text-brand-600 hover:underline">
              {t('xodimlarni kiriting')}
            </Link>
            {t(', keyin joriy oy uchun hisoblashni boshlang.')}
          </p>
        </div>
      )}

      {payingRun && (
        <PayoutModal
          runId={payingRun.id}
          period={monthLabel(payingRun.period_year, payingRun.period_month)}
          saving={markPaid.isPending}
          onClose={() => setPayingRun(null)}
          onConfirm={(payload) => markPaid.mutate({ id: payingRun.id, payload })}
        />
      )}

      {run && (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-semibold text-slate-900">
                {monthLabel(run.period_year, run.period_month)} · {STATUS[run.status][0]}
              </p>
              <p className="text-xs text-slate-500">
                {t('Yalpi {money} · ushlab qolindi {money2} · sof', {
                  money: money(run.total_gross),
                  money2: money(run.total_deductions),
                })}{' '}
                <strong>{money(run.total_net)}</strong>
                {/* Avans jami — aks holda "yalpi − ushlab qolindi = sof"
                    tenglamasi to'g'ri kelmasdi va raqamlar xato ko'rinardi. */}
                {advanceTotal > 0 && (
                  <span className="ml-1 text-slate-500">
                    {t('(shundan avans {money})', { money: money(String(advanceTotal)) })}
                  </span>
                )}
              </p>
            </div>
            {can('payroll.update') && (
              <div className="flex gap-2">
                {run.status === 'draft' && (
                  <button
                    type="button"
                    onClick={() => recalculate.mutate(run.id)}
                    disabled={recalculate.isPending}
                    title={t('Yangi xodimlar va avanslarni tortib oladi')}
                    aria-label={t('Yangi xodimlar va avanslarni tortib oladi')}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60 sm:flex-none"
                  >
                    <RefreshCw className="h-4 w-4" /> {t('Qayta hisoblash')}
                  </button>
                )}
                {run.status === 'draft' && (
                  <button
                    type="button"
                    onClick={() => finalize.mutate(run.id)}
                    disabled={finalize.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-ildiz-700 px-3 py-2 text-sm font-semibold text-white hover:bg-ildiz-800 disabled:opacity-60 sm:flex-none"
                  >
                    <Lock className="h-4 w-4" /> {t('Yakunlash')}
                  </button>
                )}
                {run.status === 'finalized' && (
                  <button
                    type="button"
                    onClick={() => setPayingRun(run)}
                    disabled={markPaid.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60 sm:flex-none"
                  >
                    <CheckCircle2 className="h-4 w-4" /> {t('Toʻlangan')}
                  </button>
                )}
                {/* Yakunlangan yoki to'langan hisoblashni tahrirlashning
                    yagona yo'li. `approve` talab qilinadi: yakunlashni
                    bajara olgan rol uni bekor ham qila olishi shart emas. */}
                {run.status !== 'draft' && can('payroll.approve') && (
                  <button
                    type="button"
                    onClick={() => {
                      setReopenReason('')
                      setReopening(run)
                    }}
                    title={t('Tahrirlash uchun qoralamaga qaytarish')}
                    aria-label={t('Tahrirlash uchun qoralamaga qaytarish')}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 sm:flex-none"
                  >
                    <Unlock className="h-4 w-4" /> {t('Qayta ochish')}
                  </button>
                )}
              </div>
            )}
          </div>

          {/*
            Telefonda — kartochka, jadval emas (PLAN 10.9).

            Jadvalda oltita ustun bor va 375 px da ulardan faqat uchtasi
            koʻrinardi: xodim, baza va bonus. Yaʼni ekranda xodimga
            QANCHA TOʻLANISHI — "Sof" — umuman yoʻq edi, uning oʻrniga
            tahrirlash maydoni turardi. Mudira esa oylikni aynan shu
            raqam uchun ochadi.
          */}
          <ul className="divide-y divide-slate-100 sm:hidden">
            {run.items.map((item) => (
              <li key={item.id} className="px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => setPayslip(item)}
                    aria-label={t('Oylik varaqasi')}
                    className="min-h-11 min-w-0 flex-1 text-left text-sm font-semibold text-slate-900 underline-offset-2 hover:underline"
                  >
                    {item.employee_name}
                    {Number(item.official_base) > 0 && (
                      <span className="ml-1.5 rounded-full bg-ildiz-100 px-1.5 py-0.5 text-xs font-medium text-ildiz-800">
                        {t('rasmiy')}
                      </span>
                    )}
                  </button>
                  <span className="num shrink-0 text-base font-bold text-slate-900">
                    {money(item.net)}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-500">
                  {t('Baza {base}', { base: money(item.base_amount) })}
                  {Number(item.bonus) > 0 && t(' · bonus {bonus}', { bonus: money(item.bonus) })}
                  {Number(item.advance) > 0 && t(' · avans −{adv}', { adv: money(item.advance) })}
                  {Number(item.deduction) > 0 &&
                    t(' · ushlab qolish −{ded}', { ded: money(item.deduction) })}
                </p>
                {/* Oylik QAYSI hisobdan berilgani (mijoz soʻrovi,
                    2026-10-28): javob yozilgan edi, lekin faqat toʻlov
                    oynasida koʻrinardi va yopilgandan keyin yoʻqolardi. */}
                {(item.payouts ?? []).length > 0 && (
                  <p className="mt-0.5 text-xs text-slate-500">
                    {t('Berildi:')}{' '}
                    {(item.payouts ?? [])
                      .map((row) => `${row.cash_account_name} ${money(row.amount)}`)
                      .join(' · ')}
                  </p>
                )}
                {run.is_editable && can('payroll.update') && (
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    {(['bonus', 'deduction'] as const).map((field) => (
                      <label key={field} className="block">
                        <span className="mb-1 block text-xs font-medium text-slate-600">
                          {field === 'bonus' ? t('Bonus') : t('Ushlab qolish')}
                        </span>
                        <input
                          type="number"
                          min={0}
                          inputMode="numeric"
                          defaultValue={item[field]}
                          onBlur={(e) => {
                            if (e.target.value !== item[field]) {
                              updateItem.mutate({ itemId: item.id, field, value: e.target.value })
                            }
                          }}
                          className="w-full rounded-lg border border-slate-200 px-2 text-right text-sm outline-none focus:border-brand-500"
                        />
                      </label>
                    ))}
                  </div>
                )}
              </li>
            ))}
            {run.items.length === 0 && (
              <li className="px-4 py-10 text-center text-sm text-slate-500">
                {t('Bu davrda xodim yoʻq')}
              </li>
            )}
          </ul>

          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">{t('Xodim')}</th>
                  <th className="px-4 py-3 text-right font-medium">{t('Baza')}</th>
                  <th className="px-4 py-3 text-right font-medium">{t('Bonus')}</th>
                  <th className="px-4 py-3 text-right font-medium">{t('Avans')}</th>
                  <th className="px-4 py-3 text-right font-medium">{t('Ushlab qolish')}</th>
                  <th className="px-4 py-3 text-right font-medium">{t('Sof')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {run.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-2 font-medium text-slate-800">
                      {/* Ism bosilsa oylik varaqasi ochiladi: rasmiy va
                          naqd qism, ushlanmalar bilan (ADR-18). Ular
                          jadvalga sig'masdi. */}
                      <button
                        type="button"
                        onClick={() => setPayslip(item)}
                        title={t('Oylik varaqasi')}
                        aria-label={t('Oylik varaqasi')}
                        className="rounded text-left underline-offset-2 hover:underline"
                      >
                        {item.employee_name}
                        {Number(item.official_base) > 0 && (
                          <span className="ml-1.5 rounded-full bg-ildiz-100 px-1.5 py-0.5 text-xs font-medium text-ildiz-800">
                            {t('rasmiy')}
                          </span>
                        )}
                      </button>
                      {(item.payouts ?? []).length > 0 && (
                        <span className="block text-xs text-slate-500">
                          {(item.payouts ?? [])
                            .map((row) => `${row.cash_account_name} ${money(row.amount)}`)
                            .join(' · ')}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-right text-slate-600 tabular-nums">
                      {money(item.base_amount)}
                    </td>
                    {/* Avans qo'lda tahrirlanmaydi: u «Avanslar» ro'yxatidan
                        yig'iladi (sana bo'yicha), ya'ni raqam ortida har doim
                        aniq yozuv turadi. */}
                    {(['bonus'] as const).map((field) => (
                      <td key={field} className="px-4 py-2 text-right">
                        {run.is_editable && can('payroll.update') ? (
                          <input
                            type="number"
                            min={0}
                            inputMode="numeric"
                            defaultValue={item[field]}
                            aria-label={field}
                            onBlur={(e) => {
                              if (e.target.value !== item[field]) {
                                updateItem.mutate({ itemId: item.id, field, value: e.target.value })
                              }
                            }}
                            className="w-28 rounded border border-slate-200 px-2 py-1 text-right text-sm outline-none focus:border-brand-500"
                          />
                        ) : (
                          <span className="text-slate-600 tabular-nums">{money(item[field])}</span>
                        )}
                      </td>
                    ))}
                    {/* Avans qo'lda tahrirlanmaydi: u «Avanslar» ro'yxatidan
                        sana bo'yicha yig'iladi, ya'ni raqam ortida har doim
                        aniq yozuv turadi. */}
                    <td className="px-4 py-2 text-right tabular-nums text-slate-600">
                      {Number(item.advance) > 0 ? `−${money(item.advance)}` : '—'}
                    </td>
                    {(['deduction'] as const).map((field) => (
                      <td key={field} className="px-4 py-2 text-right">
                        {run.is_editable && can('payroll.update') ? (
                          <input
                            type="number"
                            min={0}
                            inputMode="numeric"
                            defaultValue={item[field]}
                            aria-label={field}
                            onBlur={(e) => {
                              if (e.target.value !== item[field]) {
                                updateItem.mutate({ itemId: item.id, field, value: e.target.value })
                              }
                            }}
                            className="w-28 rounded border border-slate-200 px-2 py-1 text-right text-sm outline-none focus:border-brand-500"
                          />
                        ) : (
                          <span className="text-slate-600 tabular-nums">{money(item[field])}</span>
                        )}
                      </td>
                    ))}
                    <td className="px-4 py-2 text-right font-semibold text-slate-900 tabular-nums">
                      {money(item.net)}
                    </td>
                  </tr>
                ))}
                {run.items.length === 0 && (
                  <EmptyRow
                    colSpan={6}
                    icon={Wallet}
                    title={t('Bu davrda xodim yoʻq')}
                    hint={t(
                      'Hisoblash yaratilgan paytda ishlayotgan xodim topilmadi. Xodimlar sahifasida ularni kiriting va yangi davr oching.',
                    )}
                  />
                )}
              </tbody>
            </table>
          </div>

          {!run.is_editable && (
            <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
              {t(
                'Hisoblash yakunlangan — tahrirlash yopiq. Tuzatishni keyingi oyda bonus yoki ushlab qolish sifatida kiriting.',
              )}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
