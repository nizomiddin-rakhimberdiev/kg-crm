/**
 * Hisob-fakturalar va tariflar (docs/04 §9).
 *
 * Hisob-faktura bu yerda TAHRIRLANMAYDI — u ledger yozuvini yaratgan
 * hujjat (D3). Xato bo'lsa bekor qilinadi (qarshi yozuv bilan) va
 * yangisi chiqariladi.
 */

import { useState } from 'react'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Ban, FileText, Plus, Printer, Search, Trash2, Users, Wallet } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { paymentsApi, tariffsApi, type BoardRow } from '@/features/payments/api'
import { GenerateInvoicesDialog } from '@/features/payments/components/GenerateInvoicesDialog'
import { ReceiptModal } from '@/features/payments/components/ReceiptModal'
import { TakePaymentModal } from '@/features/payments/components/TakePaymentModal'
import { PAYMENT_METHODS, paymentMethodLabel } from '@/features/payments/methods'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { invalidateMoney } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type BillingRunResult, type Payment } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate, formatMoney } from '@/lib/utils'
import { EmptyRow } from '@/components/ui/EmptyState'
import { Modal } from '@/components/ui/Modal'
import { som } from '@/lib/format'
import { t } from '@/lib/i18n'

const money = som

const MONTHS = [
  t('Yanvar'),
  t('Fevral'),
  t('Mart'),
  t('Aprel'),
  t('May'),
  t('Iyun'),
  t('Iyul'),
  t('Avgust'),
  t('Sentabr'),
  t('Oktabr'),
  t('Noyabr'),
  t('Dekabr'),
]

/** Qatordagi holat belgisi — rangi bir qarashda o'qiladi. */
const BOARD_STATE: Record<BoardRow['state'], [string, string]> = {
  unpaid: [t("To'lanmagan"), 'bg-red-50 text-red-700'],
  partial: [t("Qisman to'langan"), 'bg-amber-50 text-amber-700'],
  paid: [t("To'langan"), 'bg-emerald-50 text-emerald-700'],
  no_invoice: [t('Fakturasiz'), 'bg-slate-100 text-slate-500'],
}

export default function PaymentsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const now = new Date()
  const [tab, setTab] = useState<'board' | 'payments' | 'tariffs'>('board')
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [tariffForm, setTariffForm] = useState({ name: '', amount: '' })
  // Qidiruv SERVERDA bajariladi, lekin har harfda so'rov yubormaymiz:
  // `debounced` 250 ms kutadi. Kassir tez yozadi, tarmoq esa sekin.
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search, 250)
  const [status, setStatus] = useState<'' | 'debtor' | 'paid' | 'no_invoice'>('')
  // Bosilgan bola — to'lov oynasi shu qator bilan ochiladi.
  const [paying, setPaying] = useState<BoardRow | null>(null)
  const [runResult, setRunResult] = useState<BillingRunResult | null>(null)
  const [generating, setGenerating] = useState(false)
  const [receiptFor, setReceiptFor] = useState<string | null>(null)

  // Jurnal filtri (PLAN 1.8). Sukut — shu oy: kassir odatda "bugun va
  // kecha nima bo'ldi" degan savol bilan keladi.
  const monthStart = `${year}-${String(month).padStart(2, '0')}-01`
  const monthEnd = new Date(year, month, 0).toISOString().slice(0, 10)
  const [journal, setJournal] = useState({
    paid_from: monthStart,
    paid_to: monthEnd,
    method: '',
  })
  // Qaytarish sababi so'raladigan to'lov.
  const [reversing, setReversing] = useState<Payment | null>(null)
  const [reverseReason, setReverseReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Sahifalar `useInfiniteQuery` bilan yig'iladi — qo'lda emas.
  //
  // Avval sahifalar `useState` + `useEffect` bilan to'planardi va u
  // JIMGINA noto'g'ri edi: "Yana ko'rsatish" bosilganda effekt avval
  // ESKI ma'lumot bilan ishga tushib, birinchi sahifani ikkinchi
  // marta qo'shib yuborardi — jonli sinovda 100 qator 205 ta bo'lib
  // ko'rindi. Bu vosita aynan shu ish uchun mo'ljallangan va
  // takrorlanish tuzilishi bo'yicha mumkin emas.
  const boardFilters = {
    period_year: year,
    period_month: month,
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(status ? { status } : {}),
  }
  const boardQuery = useInfiniteQuery({
    queryKey: queryKeys.paymentBoard(organizationId, boardFilters),
    queryFn: ({ pageParam }) => paymentsApi.board({ ...boardFilters, page: pageParam }),
    initialPageParam: 1,
    getNextPageParam: (last) =>
      last.pagination && last.pagination.page < last.pagination.total_pages
        ? last.pagination.page + 1
        : undefined,
  })

  // Yakuniy raqamlar ALOHIDA so'rovda va sahifasiz: ular butun oyga
  // tegishli, ko'rinib turgan qatorlarga emas.
  const summaryQuery = useQuery({
    queryKey: ['org', organizationId, 'payments', 'board-summary', year, month],
    queryFn: () => paymentsApi.boardSummary(year, month),
  })

  const tariffsQuery = useQuery({
    queryKey: queryKeys.tariffs(organizationId),
    queryFn: tariffsApi.list,
  })

  // To'lovlar ro'yxati — kassirning kunlik jurnali. Ilgari UI'da umuman
  // yo'q edi: qabul qilingan to'lovni faqat hisob-faktura qatoridan
  // ko'rish mumkin edi, fakturasiz kelgan pul esa hech qayerda
  // ko'rinmasdi.
  const journalParams = {
    page_size: 100,
    paid_at__date__gte: journal.paid_from,
    paid_at__date__lte: journal.paid_to,
    ...(journal.method ? { method: journal.method } : {}),
  }
  const paymentsQuery = useQuery({
    queryKey: queryKeys.payments(organizationId, journalParams),
    queryFn: () => paymentsApi.list(journalParams),
    enabled: tab === 'payments',
  })

  // Yig'indi ALOHIDA so'rovda va sahifasiz — u butun oraliqqa tegishli.
  const journalSummary = useQuery({
    queryKey: ['org', organizationId, 'payments', 'journal-summary', journal],
    queryFn: () =>
      paymentsApi.journalSummary({
        paid_from: journal.paid_from,
        paid_to: journal.paid_to,
        ...(journal.method ? { method: journal.method } : {}),
      }),
    enabled: tab === 'payments',
  })

  const reverseMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => paymentsApi.reverse(id, reason),
    onSuccess: () => {
      setReversing(null)
      setReverseReason('')
      setError(null)
      invalidateMoney(queryClient, organizationId)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const invalidate = () => {
    invalidateMoney(queryClient, organizationId)
    void queryClient.invalidateQueries({ queryKey: queryKeys.tariffs(organizationId) })
  }

  const createTariff = useMutation({
    mutationFn: () => tariffsApi.create(tariffForm),
    onSuccess: () => {
      setTariffForm({ name: '', amount: '' })
      setError(null)
      invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const removeTariff = useMutation({
    mutationFn: tariffsApi.remove,
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const rows = boardQuery.data?.pages.flatMap((chunk) => chunk.items) ?? []
  const summary = summaryQuery.data

  return (
    <div className="space-y-6">
      {/* To'lov oynasi — bolaning qatori bosilganda. Alohida "yangi
          to'lov" tugmasi YO'Q: kassir bolani qidiradi, ustiga bosadi
          va pulni qabul qiladi. */}
      {paying && (
        <TakePaymentModal row={paying} onClose={() => setPaying(null)} onPaid={setReceiptFor} />
      )}

      {/* Qaytarish — sabab MAJBURIY: kassa jurnalida "nega qaytarildi?"
          degan savol javobsiz qolmasin (to'lovning o'zi o'chirilmaydi,
          ustiga qarshi yozuv qo'shiladi). */}
      <Modal open={Boolean(reversing)} onClose={() => setReversing(null)} className="max-w-md">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (reversing) reverseMutation.mutate({ id: reversing.id, reason: reverseReason })
          }}
          className="p-5"
        >
          <h2 className="text-base font-semibold text-slate-900">{t("To'lovni qaytarish")}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {reversing?.child_name} · {reversing ? money(reversing.amount) : ''}
          </p>
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
            {t(
              "To'lov o'chirilmaydi — ustiga qarshi yozuv qo'shiladi va jurnalda ikkalasi ham ko'rinadi.",
            )}
          </p>
          <label htmlFor="rev-reason" className="mt-4 block text-xs font-medium text-slate-600">
            {t('Sabab')}
          </label>
          <input
            id="rev-reason"
            required
            autoFocus
            maxLength={255}
            value={reverseReason}
            onChange={(e) => setReverseReason(e.target.value)}
            placeholder={t('Masalan: xato summa kiritilgan')}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setReversing(null)}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={reverseMutation.isPending}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-60"
            >
              {t('Qaytarish')}
            </button>
          </div>
        </form>
      </Modal>

      {receiptFor && <ReceiptModal paymentId={receiptFor} onClose={() => setReceiptFor(null)} />}

      {generating && (
        <GenerateInvoicesDialog
          year={year}
          month={month}
          onClose={() => setGenerating(false)}
          onDone={(result) => {
            setRunResult(result)
            setError(null)
            setGenerating(false)
            invalidate()
          }}
        />
      )}

      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t("To'lovlar")}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('Bolani qidiring, ustiga bosing va pulni qabul qiling.')}
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(
          [
            ['board', t("To'lov qabul qilish")],
            ['payments', t('Jurnal')],
            ['tariffs', t('Tariflar')],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              '-mb-px border-b-2 px-4 py-2 text-sm font-medium transition',
              tab === key
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-800',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {tab === 'board' && (
        <>
          {/* Davr, qidiruv va filtr — bitta qatorda. Kassirning ishi
              shu yerdan boshlanadi: bolani topish. */}
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="year" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Yil')}
              </label>
              <input
                id="year"
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="w-24 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label htmlFor="month" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Oy')}
              </label>
              <select
                id="month"
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              >
                {MONTHS.map((label, index) => (
                  <option key={label} value={index + 1}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div className="min-w-[14rem] flex-1">
              <label
                htmlFor="board-search"
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t('Bolani qidirish')}
              </label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  id="board-search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={t('Ism yoki familiya…')}
                  className="w-full rounded-lg border border-slate-200 py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
              </div>
            </div>

            {can('payments.create') && (
              <button
                type="button"
                onClick={() => setGenerating(true)}
                className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
              >
                <FileText className="h-4 w-4" />
                {t('Hisob-faktura chiqarish')}
              </button>
            )}
          </div>

          {/* Holat bo'yicha filtr — serverda, ya'ni sonlar sahifaga
              bog'liq emas. */}
          <div className="flex flex-wrap gap-2">
            {(
              [
                ['', t('Hammasi'), summary?.children],
                ['debtor', t('Shu oy toʻlanmagan'), summary?.debtors],
                ['paid', t("To'langan"), (summary?.with_invoice ?? 0) - (summary?.debtors ?? 0)],
                ['no_invoice', t('Fakturasiz'), summary?.without_invoice],
              ] as const
            ).map(([value, label, count]) => (
              <button
                key={value || 'all'}
                type="button"
                onClick={() => setStatus(value)}
                className={cn(
                  'rounded-full border px-3 py-1.5 text-sm font-medium transition',
                  status === value
                    ? 'border-brand-300 bg-brand-50 text-brand-700'
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50',
                )}
              >
                {label}
                {count !== undefined && (
                  <span className="ml-1.5 text-xs tabular-nums opacity-70">{count}</span>
                )}
              </button>
            ))}
          </div>

          {/* Oyning yakuni — SERVERDAN, ya'ni sahifadan qat'i nazar
              to'g'ri. Ilgari u yuklangan 25 qatordan hisoblanar va
              har doim kam ko'rsatardi. */}
          <div className="grid gap-3 sm:grid-cols-3">
            {(
              [
                [t('Hisoblangan'), summary?.charged, 'text-slate-900'],
                [t("To'langan"), summary?.paid, 'text-emerald-600'],
                [t('Qolgan'), summary?.outstanding, 'text-amber-600'],
              ] as const
            ).map(([label, value, tone]) => (
              <div key={label} className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {label}
                </p>
                <p className={cn('num mt-1 text-xl font-bold', tone)}>
                  {value === undefined ? '…' : money(value)}
                </p>
              </div>
            ))}
          </div>

          {(summary?.without_invoice ?? 0) > 0 && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {t(
                "{v} ta bolaga bu oy uchun hisob-faktura chiqarilmagan — tarifi yo'q bo'lishi mumkin.",
                { v: summary?.without_invoice },
              )}
            </p>
          )}

          {runResult && (
            <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              {t('{created} ta chiqarildi · {skipped} ta o‘tkazib yuborildi', {
                created: runResult.created,
                skipped: runResult.skipped_existing,
              })}
            </div>
          )}

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <ul className="divide-y divide-slate-100">
              {rows.map((row) => {
                const [label, tone] = BOARD_STATE[row.state]
                const credit = Math.max(0, -Number(row.balance))
                const clickable = can('payments.create')
                return (
                  <li key={row.child_id}>
                    <button
                      type="button"
                      disabled={!clickable}
                      onClick={() => setPaying(row)}
                      className={cn(
                        'flex w-full items-center gap-3 px-4 py-3 text-left transition',
                        clickable ? 'hover:bg-slate-50' : 'cursor-default',
                      )}
                    >
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-medium text-slate-900">
                          {row.child_name}
                        </span>
                        <span className="block truncate text-xs text-slate-400">
                          {row.group_name || t('Guruhsiz')}
                          {credit > 0 && (
                            <span className="ml-1.5 text-emerald-600">
                              {t('avans {money}', { money: money(String(credit)) })}
                            </span>
                          )}
                        </span>
                      </span>

                      <span className="hidden shrink-0 text-right sm:block">
                        <span className="block text-xs text-slate-400">{t('Hisoblangan')}</span>
                        <span className="block text-sm tabular-nums text-slate-600">
                          {money(row.charged)}
                        </span>
                      </span>

                      <span className="w-28 shrink-0 text-right">
                        <span className="block text-xs text-slate-400">{t('Qolgan')}</span>
                        <span
                          className={cn(
                            'block text-sm font-semibold tabular-nums',
                            Number(row.outstanding) > 0 ? 'text-amber-600' : 'text-slate-400',
                          )}
                        >
                          {money(row.outstanding)}
                        </span>
                      </span>

                      <span
                        className={cn(
                          'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                          tone,
                        )}
                      >
                        {label}
                      </span>
                    </button>
                  </li>
                )
              })}

              {rows.length === 0 && !boardQuery.isPending && (
                <li className="px-4 py-12 text-center">
                  <Users className="mx-auto h-8 w-8 text-slate-300" />
                  <p className="mt-2 text-sm font-medium text-slate-600">
                    {search ? t('Hech kim topilmadi') : t("Bola yo'q")}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    {search
                      ? t('Boshqa ism bilan qidirib ko‘ring.')
                      : t("Avval bolalarni ro'yxatga oling.")}
                  </p>
                </li>
              )}

              {boardQuery.isPending && (
                <li className="px-4 py-12 text-center text-sm text-slate-400">
                  {t('Yuklanmoqda…')}
                </li>
              )}
            </ul>

            {boardQuery.hasNextPage && (
              <button
                type="button"
                disabled={boardQuery.isFetchingNextPage}
                onClick={() => void boardQuery.fetchNextPage()}
                className="w-full border-t border-slate-100 px-4 py-3 text-sm font-medium text-brand-700 transition hover:bg-brand-50"
              >
                {boardQuery.isFetchingNextPage ? t('Yuklanmoqda…') : t('Yana ko‘rsatish')}
              </button>
            )}
          </div>
        </>
      )}
      {tab === 'payments' && (
        <>
          {/* Bu yerda "to'lov qabul qilish" tugmasi ATAYLAB yo'q:
              pul faqat bolaning qatoridan qabul qilinadi, ya'ni har
              doim kimga tegishli ekani ma'lum. Jurnal esa o'qish
              uchun — nima bo'lgani va kim qabul qilgani. */}
          <div className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4">
            <div>
              <label
                htmlFor="journal-from"
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t('Sanadan')}
              </label>
              <input
                id="journal-from"
                type="date"
                value={journal.paid_from}
                onChange={(e) => setJournal((p) => ({ ...p, paid_from: e.target.value }))}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label htmlFor="journal-to" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Sanagacha')}
              </label>
              <input
                id="journal-to"
                type="date"
                value={journal.paid_to}
                onChange={(e) => setJournal((p) => ({ ...p, paid_to: e.target.value }))}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label
                htmlFor="journal-method"
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t("To'lov usuli")}
              </label>
              <select
                id="journal-method"
                value={journal.method}
                onChange={(e) => setJournal((p) => ({ ...p, method: e.target.value }))}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              >
                <option value="">{t('Hammasi')}</option>
                {PAYMENT_METHODS.map((value) => (
                  <option key={value} value={value}>
                    {paymentMethodLabel(value)}
                  </option>
                ))}
              </select>
            </div>

            {/* Yig'indi — filtr bilan birga o'zgaradi. */}
            <div className="ml-auto text-right">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('Jami qabul qilingan')}
              </p>
              <p className="num text-xl font-bold text-slate-900">
                {journalSummary.data
                  ? t("{money} so'm", { money: formatMoney(Number(journalSummary.data.total)) })
                  : '—'}
              </p>
              {journalSummary.data && (
                <p className="text-xs text-slate-400">
                  {t('{n} ta toʻlov', { n: journalSummary.data.count })}
                  {journalSummary.data.reversed_count > 0 &&
                    t(' · {n} ta qaytarilgan', { n: journalSummary.data.reversed_count })}
                </p>
              )}
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="border-b border-slate-200 bg-slate-50/70 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">{t('Sana')}</th>
                    <th className="px-4 py-3">{t('Bola')}</th>
                    <th className="px-4 py-3">{t('Hisob-faktura')}</th>
                    <th className="px-4 py-3">{t("To'lov usuli")}</th>
                    <th className="px-4 py-3 text-right">{t('Summa')}</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {paymentsQuery.data?.items.map((payment) => (
                    <tr
                      key={payment.id}
                      className={cn('tabular-nums', payment.is_reversed && 'text-slate-400')}
                    >
                      <td className="px-4 py-3">{formatDate(payment.paid_at)}</td>
                      <td className="px-4 py-3 font-medium text-slate-800">{payment.child_name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">
                        {payment.invoice_number ?? t('— avans —')}
                      </td>
                      <td className="px-4 py-3">{paymentMethodLabel(payment.method)}</td>
                      <td
                        className={cn(
                          'px-4 py-3 text-right font-semibold',
                          payment.is_reversed ? 'text-slate-400 line-through' : 'text-emerald-700',
                        )}
                      >
                        {money(payment.amount)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {/* Kvitansiyani qayta chop etish — qaytarilgan
                            to'lov uchun ham: o'sha qog'oz ota-onada
                            qolgan va u nima bo'lganini so'raydi. */}
                        <button
                          type="button"
                          onClick={() => setReceiptFor(payment.id)}
                          title={t('Kvitansiya')}
                          className="mr-1 rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                        >
                          <Printer className="h-4 w-4" />
                        </button>
                        {payment.is_reversed ? (
                          <span
                            title={payment.reversal_reason || undefined}
                            className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500"
                          >
                            {t('Qaytarilgan')}
                          </span>
                        ) : (
                          can('payments.update') && (
                            <button
                              type="button"
                              onClick={() => {
                                setReversing(payment)
                                setReverseReason('')
                              }}
                              title={t('Qaytarish')}
                              className="rounded-lg p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                            >
                              <Ban className="h-4 w-4" />
                            </button>
                          )
                        )}
                      </td>
                    </tr>
                  ))}
                  {paymentsQuery.data?.items.length === 0 && (
                    <EmptyRow
                      colSpan={6}
                      icon={Wallet}
                      title={t("Hozircha to'lov qabul qilinmagan.")}
                    />
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {tab === 'tariffs' && (
        <>
          {can('payments.create') && (
            <form
              onSubmit={(event) => {
                event.preventDefault()
                createTariff.mutate()
              }}
              className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4"
            >
              <div className="min-w-[200px] flex-1">
                <label htmlFor="t-name" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Tarif nomi')}
                </label>
                <input
                  id="t-name"
                  required
                  value={tariffForm.name}
                  onChange={(e) => setTariffForm((p) => ({ ...p, name: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <div className="w-44">
                <label htmlFor="t-amount" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Oylik summa')}
                </label>
                <input
                  id="t-amount"
                  required
                  type="number"
                  min={0}
                  step="0.01"
                  value={tariffForm.amount}
                  onChange={(e) => setTariffForm((p) => ({ ...p, amount: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <button
                type="submit"
                disabled={createTariff.isPending}
                className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
              >
                <Plus className="h-4 w-4" />
                {t("Qo'shish")}
              </button>
            </form>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {tariffsQuery.data?.items.map((tariff) => (
              <div key={tariff.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-900">{tariff.name}</p>
                    <p className="mt-0.5 text-sm text-slate-600">{money(tariff.amount)}</p>
                  </div>
                  {can('payments.delete') && (
                    <button
                      type="button"
                      onClick={() => removeTariff.mutate(tariff.id)}
                      className="shrink-0 rounded-lg p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                      title={t("O'chirish")}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {tariffsQuery.data?.items.length === 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center">
              <p className="text-sm text-slate-500">
                {t(
                  "Hozircha tarif yo'q. Hisob-faktura chiqarish uchun avval tarif yarating va bolalarga biriktiring.",
                )}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
