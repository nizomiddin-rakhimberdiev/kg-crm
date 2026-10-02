/**
 * Hisobotlar (docs/04 §14.2).
 *
 * Davr — kun, hafta, oy, chorak, yil yoki ixtiyoriy oraliq; kesim
 * (`group_by`) preset'dan bir pog'ona mayda tanlanadi (`period.ts`).
 *
 * Sahifada `basis` ochiq yozilgan: "daromad" so'zi ikki xil ma'noga ega —
 * yozilgan hisob-faktura va qabul qilingan pul. Ekranda qaysi biri
 * ekanini o'qiyotgan odam taxmin qilmasligi kerak.
 *
 * Oylik maosh — oylik ko'rsatkich. Kun va hafta kesimida u ustunlarga
 * taqsimlanmaydi (backend `payroll_in_periods: false` qaytaradi), lekin
 * davr jamisida qoladi — bu ekranda ham aytiladi, jim o'tkazilmaydi.
 *
 * Eksport darhol fayl bermaydi: u ish yaratadi va fon ishchisi tayyorlaydi.
 * Katta davrni so'rov ichida hisoblash brauzerni kutdirib qo'yardi.
 *
 * RUXSAT DOIRASI. Har bir hisobot `reports.read` ustiga o'z mavzusining
 * ruxsatini ham talab qiladi (backend `REPORT_SCOPE`). Foyda-zarar ichida
 * oylik maosh bor — u `payroll.read` siz `403`. Avval sahifa uni HAR DOIM
 * so'rardi va oylikni ko'rmaydigan foydalanuvchida (masalan menejerda)
 * butun sahifa yiqilardi, garchi unga tushum va chiqimni ko'rish ruxsat
 * etilgan bo'lsa ham. Endi sahifa ruxsatga qarab yig'iladi.
 */

import { useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileDown, Info, RefreshCw } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { reportsApi } from '@/features/dashboard/api'
import { PeriodPicker } from '@/features/reports/components/PeriodPicker'
import {
  bucketLabel,
  bucketTitle,
  groupByFor,
  periodFor,
  type Period,
} from '@/features/reports/period'
import { PAYMENT_METHOD_COLORS, paymentMethodLabel } from '@/features/payments/methods'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan, type PermissionCode } from '@/lib/rbac/useCan'
import { Modal } from '@/components/ui/Modal'
import { BRAND, CHART, CHART_SEQUENCE } from '@/lib/brand'
import { cn, formatMoney, formatUZS } from '@/lib/utils'
import { t } from '@/lib/i18n'

// Usul nomlari `features/payments/methods.ts` da — bu yerda o'z nusxasi
// bor edi va u eskirgan `transfer` kalitini tutardi, shuning uchun
// diagrammada tarjima o'rniga xom `bank_transfer` chiqardi.
const PIE_FALLBACK = [...CHART_SEQUENCE]
const COLORS = { revenue: BRAND.nihol, expenses: BRAND.orik, payroll: CHART.ildizMid }

const EXPORTABLE: Array<[string, string]> = [
  ['profit-loss', t('Foyda va zarar')],
  ['revenue', t('Tushum')],
  ['expenses', t('Chiqimlar')],
  ['debtors', t('Qarzdorlar')],
  ['payroll', t('Oylik maosh')],
  ['attendance', t('Davomat')],
]

/**
 * Hisobot turi → kerakli ruxsat. `apps/reports/views.py` dagi
 * `REPORT_SCOPE` ning nusxasi. Bu himoya EMAS (backend baribir `403`
 * beradi) — faqat ishlamaydigan tugmani ko'rsatmaslik va yiqiladigan
 * so'rovni yubormaslik uchun.
 */
const REPORT_SCOPE: Record<string, PermissionCode> = {
  'profit-loss': 'payroll.read',
  revenue: 'payments.read',
  expenses: 'expenses.read',
  debtors: 'debtors.read',
  payroll: 'payroll.read',
  attendance: 'attendance.read',
}

const EXPORT_STATUS: Record<string, [string, string]> = {
  queued: [t('Navbatda'), 'bg-slate-100 text-slate-600'],
  running: [t('Tayyorlanmoqda'), 'border border-ildiz-300 bg-ildiz-50 text-ildiz-800'],
  ready: [t('Tayyor'), 'bg-emerald-50 text-emerald-700'],
  failed: [t('Xato'), 'bg-red-50 text-red-700'],
}

/** Grafik o'qi uchun qisqa pul: 1 200 000 → "1.2 mln". */
const compactUZS = (value: number) => {
  const abs = Math.abs(value)
  if (abs >= 1_000_000_000) return t('{v} mlrd', { v: (value / 1_000_000_000).toFixed(1) })
  if (abs >= 1_000_000)
    return t('{v} mln', { v: (value / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1) })
  if (abs >= 1_000) return t('{v} ming', { v: Math.round(value / 1_000) })
  return String(value)
}

export default function ReportsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [period, setPeriod] = useState<Period>(() => periodFor('month', new Date()))
  const [error, setError] = useState<string | null>(null)
  // Sof natija bosilganda ochiladigan qoplar kesimi (ADR-17).
  const [cashOpen, setCashOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const groupBy = groupByFor(period)

  // Qaysi hisobotlar ochiq — backend `REPORT_SCOPE` bilan bir xil.
  const canPL = can(REPORT_SCOPE['profit-loss'])
  const canRevenue = can(REPORT_SCOPE.revenue)
  const canExpenses = can(REPORT_SCOPE.expenses)
  const showRevenue = canPL || canRevenue
  const showExpenses = canPL || canExpenses

  const plQuery = useQuery({
    queryKey: queryKeys.reportProfitLoss(organizationId, period.from, period.to, groupBy),
    queryFn: () => reportsApi.profitLoss(period.from, period.to, groupBy),
    placeholderData: keepPreviousData,
    enabled: canPL,
  })
  const revenueQuery = useQuery({
    queryKey: queryKeys.reportRevenue(organizationId, period.from, period.to, groupBy),
    queryFn: () => reportsApi.revenue(period.from, period.to, groupBy),
    placeholderData: keepPreviousData,
    enabled: canRevenue,
  })
  // Foyda-zarar yopiq bo'lsa, chiqim ustuni shundan olinadi.
  const expensesQuery = useQuery({
    queryKey: queryKeys.reportExpenses(organizationId, period.from, period.to, groupBy),
    queryFn: () => reportsApi.expenses(period.from, period.to, groupBy),
    placeholderData: keepPreviousData,
    enabled: !canPL && canExpenses,
  })
  const exportsQuery = useQuery({
    queryKey: queryKeys.reportExports(organizationId),
    queryFn: reportsApi.listExports,
    // Ish fonda bajariladi; sahifa ochiq turganda holat o'zi yangilansin.
    refetchInterval: (query) =>
      (query.state.data ?? []).some((row) => row.status === 'queued' || row.status === 'running')
        ? 3000
        : false,
  })

  const requestExport = useMutation({
    mutationFn: (reportType: string) =>
      reportsApi.requestExport(reportType, {
        date_from: period.from,
        date_to: period.to,
        group_by: groupBy,
      }),
    onSuccess: () => {
      setError(null)
      setNotice(t('Eksport navbatga qo’yildi — tayyor bo‘lganda yuklab olasiz.'))
      void queryClient.invalidateQueries({ queryKey: queryKeys.reportExports(organizationId) })
    },
    onError: (err: unknown) => {
      setNotice(null)
      setError(err instanceof ApiError ? err.message : t('Eksportni boshlab bo‘lmadi.'))
    },
  })

  const pl = canPL ? plQuery.data : undefined
  const payrollInChart = canPL && (pl?.payroll_in_periods ?? true)

  // Davr qatorlari: foyda-zarardan, yoki u yopiq bo'lsa — tushum va chiqimni
  // davr bo'yicha birlashtirib. Ikkala endpoint ham bir xil uzluksiz davr
  // boshlarini qaytaradi, shuning uchun `period` bo'yicha qo'shish aniq.
  const rows = (() => {
    if (canPL) {
      return (pl?.by_period ?? []).map((row) => ({
        period: row.period,
        label: bucketLabel(row.period, groupBy),
        title: bucketTitle(row.period, groupBy),
        Tushum: Number(row.revenue),
        Chiqim: Number(row.expenses),
        'Oylik maosh': Number(row.payroll),
        net: Number(row.net),
      }))
    }
    const revenueBy = new Map(
      (revenueQuery.data?.by_period ?? []).map((row) => [row.period, Number(row.total)]),
    )
    const expensesBy = new Map(
      (expensesQuery.data?.by_period ?? []).map((row) => [row.period, Number(row.total)]),
    )
    const periods = [...new Set([...revenueBy.keys(), ...expensesBy.keys()])].sort()
    return periods.map((periodStart) => {
      const revenue = revenueBy.get(periodStart) ?? 0
      const expenses = expensesBy.get(periodStart) ?? 0
      return {
        period: periodStart,
        label: bucketLabel(periodStart, groupBy),
        title: bucketTitle(periodStart, groupBy),
        Tushum: revenue,
        Chiqim: expenses,
        'Oylik maosh': 0,
        net: revenue - expenses,
      }
    })
  })()
  const totalRevenue = canPL ? pl?.revenue : revenueQuery.data?.total
  const totalExpenses = canPL ? pl?.expenses : expensesQuery.data?.total
  const cash = plQuery.data?.by_account
  const methodRows = revenueQuery.data?.by_method ?? []
  const methodTotal = methodRows.reduce((sum, row) => sum + Number(row.total), 0)
  const methods = methodRows.map((row, index) => ({
    method: row.method,
    name: paymentMethodLabel(row.method),
    value: Number(row.total),
    count: row.count,
    color: PAYMENT_METHOD_COLORS[row.method] ?? PIE_FALLBACK[index % PIE_FALLBACK.length],
    share: methodTotal > 0 ? (Number(row.total) / methodTotal) * 100 : 0,
  }))
  const firstError = plQuery.error ?? revenueQuery.error ?? expensesQuery.error
  const loadError = firstError instanceof ApiError ? firstError.message : null
  const refreshing =
    plQuery.isPlaceholderData || revenueQuery.isPlaceholderData || expensesQuery.isPlaceholderData

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Hisobotlar')}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('Kassa usuli: daromad — qabul qilingan pul, yozilgan hisob-faktura emas.')}
          </p>
        </div>
        <PeriodPicker value={period} onChange={setPeriod} className="lg:items-end" />
      </div>

      {(error || loadError) && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error ?? loadError}
        </div>
      )}
      {notice && (
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div>
      )}

      {!canPL && (showRevenue || showExpenses) && (
        <div className="flex items-start gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-600">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
          {t(
            "Oylik maosh va sof natija bu ko'rinishda yo'q — ular «Oylik» bo'limiga ruxsati bor xodimga ko'rinadi.",
          )}
        </div>
      )}

      {!showRevenue && !showExpenses && (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center text-sm text-slate-500">
          {t(
            "Moliyaviy hisobotlarni ko'rish uchun to'lovlar yoki chiqimlar bo'limiga ruxsat kerak. Pastdagi eksportdan foydalanishingiz mumkin.",
          )}
        </div>
      )}

      {(showRevenue || showExpenses) && (
        <div className={cn('space-y-6 transition-opacity', refreshing && 'opacity-60')}>
          {/* KPI */}
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {(
              [
                showRevenue && [
                  t('Tushum'),
                  totalRevenue,
                  'text-emerald-600',
                  canRevenue
                    ? t("{v} ta to'lov", { v: revenueQuery.data?.payment_count ?? 0 })
                    : t('qabul qilingan pul'),
                ],
                showExpenses && [
                  t('Chiqimlar'),
                  totalExpenses,
                  'text-slate-900',
                  t('tasdiqlangan va to‘langan'),
                ],
                canPL && [
                  t('Oylik maosh'),
                  pl?.payroll,
                  'text-slate-900',
                  payrollInChart ? t('yakunlangan davrlar') : t('oy kesimida hisoblanadi'),
                ],
                canPL && [
                  t('Sof natija'),
                  pl?.net,
                  Number(pl?.net ?? 0) < 0 ? 'text-red-600' : 'text-emerald-600',
                  t('tushum − chiqim − oylik'),
                ],
              ].filter(Boolean) as Array<[string, string | undefined, string, string]>
            ).map(([label, value, tone, hint]) => {
              // Sof natija BOSILADI: "bu pul qaysi qopda?" — mijozning
              // so'ragan kesimi (ADR-17).
              const isNet = label === t('Sof natija')
              const body = (
                <>
                  <p className="text-sm font-medium text-slate-600">
                    {label as string}
                    {isNet && (cash?.length ?? 0) > 0 && (
                      <span className="ml-1.5 text-xs font-normal text-brand-600">
                        {t('qoplar kesimi')}
                      </span>
                    )}
                  </p>
                  <p
                    className={cn(
                      'num mt-1.5 text-xl font-bold tracking-tight sm:text-2xl',
                      tone as string,
                    )}
                  >
                    {value === undefined ? '…' : formatUZS(Number(value))}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">{hint as string}</p>
                </>
              )
              const shell = 'rounded-2xl border border-slate-200 bg-white p-4 text-left sm:p-5'
              return isNet && (cash?.length ?? 0) > 0 ? (
                <button
                  key={label as string}
                  type="button"
                  onClick={() => setCashOpen(true)}
                  className={cn(shell, 'transition hover:border-brand-300 hover:shadow-md')}
                >
                  {body}
                </button>
              ) : (
                <div key={label as string} className={shell}>
                  {body}
                </div>
              )
            })}
          </div>

          {/* Sof natija qaysi qoplardan yig'ilgan (ADR-17).
            Bu `net` bilan TENG EMAS va bo'lishi ham shart emas: `net`
            hisoblash usulida (yakunlangan oylik — xarajat), bu esa
            kassa usulida (qopga kirgan va undan chiqqan pul). Oynada
            shu ayirma ochiq aytiladi. */}
          <Modal open={cashOpen} onClose={() => setCashOpen(false)} className="max-w-lg">
            <div className="p-6">
              <div className="pr-10">
                <h2 className="text-lg font-bold text-slate-900">{t('Pul qaysi qoplarda')}</h2>
                <p className="mt-1 text-sm text-slate-500">
                  {bucketTitle(period.from, 'day')} — {bucketTitle(period.to, 'day')}
                </p>
              </div>
              <ul className="mt-5 space-y-2">
                {(cash ?? []).map((account) => (
                  <li key={account.id} className="rounded-xl border border-slate-200 px-3 py-3">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-sm font-medium text-slate-700">{account.name}</span>
                      <span
                        className={cn(
                          'text-sm font-semibold tabular-nums',
                          Number(account.net) < 0 ? 'text-red-600' : 'text-emerald-600',
                        )}
                      >
                        {Number(account.net) >= 0 ? '+' : '−'}{' '}
                        {formatUZS(Math.abs(Number(account.net)))}
                      </span>
                    </div>
                    <div className="mt-1 flex justify-between gap-3 text-xs tabular-nums text-slate-400">
                      <span>{t('Kirim {v}', { v: formatUZS(Number(account.inflow)) })}</span>
                      <span>{t('Chiqim {v}', { v: formatUZS(Number(account.outflow)) })}</span>
                    </div>
                  </li>
                ))}
                {(cash?.length ?? 0) === 0 && (
                  <li className="py-8 text-center text-sm text-slate-400">
                    {t("Bu davrda pul harakati yo'q.")}
                  </li>
                )}
              </ul>
              <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">
                {t(
                  "Bu yerdagi yig'indi yuqoridagi sof natijadan farq qilishi mumkin: hisobot yakunlangan oylikni xarajat deb sanaydi, bu esa faqat kassadan haqiqatan chiqqan pulni.",
                )}
              </p>
            </div>
          </Modal>

          {/* Grafiklar */}
          <div className={cn('grid gap-4 lg:gap-6', canRevenue && 'lg:grid-cols-[1.6fr_1fr]')}>
            <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
              <h2 className="text-sm font-semibold text-slate-900">{t('Tushum va chiqim')}</h2>
              <p className="mt-0.5 text-xs text-slate-500">
                {!canPL
                  ? t('Tushum va tasdiqlangan chiqimlar, davr bo‘yicha')
                  : payrollInChart
                    ? t('Chiqim ustuni: xarajat + oylik maosh (ustma-ust)')
                    : t(
                        'Kun/hafta kesimida oylik maosh ustunlarga kirmaydi — u jami ko‘rsatkichda',
                      )}
              </p>
              <div className="mt-4 h-64 sm:h-72">
                {rows.length === 0 ? (
                  <p className="grid h-full place-items-center text-sm text-slate-400">
                    {t("Bu davrda ma'lumot yo'q.")}
                  </p>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={rows}
                      margin={{ left: 0, right: 8, top: 8, bottom: 0 }}
                      // 30 kunlik kesimda telefonda ustunlar 2px bo'lib qolmasin.
                      barCategoryGap="18%"
                      barGap={1}
                    >
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
                      <XAxis
                        dataKey="label"
                        tickLine={false}
                        axisLine={false}
                        fontSize={11}
                        interval="preserveStartEnd"
                        minTickGap={16}
                      />
                      <YAxis
                        tickLine={false}
                        axisLine={false}
                        fontSize={11}
                        width={56}
                        tickFormatter={(v: number) => compactUZS(v)}
                      />
                      <Tooltip
                        formatter={(v: number) => formatUZS(v)}
                        labelFormatter={(_, payload) => payload?.[0]?.payload?.title ?? ''}
                        contentStyle={{
                          borderRadius: 12,
                          border: `1px solid ${CHART.grid}`,
                          fontSize: 13,
                        }}
                      />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                      {showRevenue && (
                        <Bar
                          dataKey={t('Tushum')}
                          fill={COLORS.revenue}
                          radius={[6, 6, 0, 0]}
                          maxBarSize={40}
                        />
                      )}
                      {showExpenses && (
                        <Bar
                          dataKey={t('Chiqim')}
                          stackId="cost"
                          fill={COLORS.expenses}
                          radius={payrollInChart ? [0, 0, 0, 0] : [6, 6, 0, 0]}
                          maxBarSize={40}
                        />
                      )}
                      {payrollInChart && (
                        <Bar
                          dataKey={t('Oylik maosh')}
                          stackId="cost"
                          fill={COLORS.payroll}
                          radius={[6, 6, 0, 0]}
                          maxBarSize={40}
                        />
                      )}
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </section>

            {canRevenue && (
              <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
                <h2 className="text-sm font-semibold text-slate-900">{t("To'lov usullari")}</h2>
                <p className="mt-0.5 text-xs text-slate-500">
                  {t('Davr ichida qabul qilingan pul')}
                </p>
                {methods.length === 0 ? (
                  <p className="mt-4 grid h-40 place-items-center text-sm text-slate-400">
                    {t("Bu davrda to'lov yo'q.")}
                  </p>
                ) : (
                  <div className="mt-4 flex flex-col items-center gap-5">
                    {/* Halqa USTDA, ro'yxat ostida — yonma-yon EMAS.
                    Bu panel hisobot to'rining tor ustunida (≈430px)
                    yashaydi: halqa yonida ro'yxatga atigi 200px qolib,
                    "Bank o'tkazmasi" ikki qatorga bo'linardi. Ustma-ust
                    joylashganda har bir qatorga butun kenglik tegadi,
                    panelning pastidagi bo'sh joy esa ishga tushadi. */}
                    <div className="relative h-44 w-44 shrink-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={methods}
                            dataKey="value"
                            nameKey="name"
                            innerRadius="64%"
                            outerRadius="92%"
                            paddingAngle={methods.length > 1 ? 2 : 0}
                            stroke="none"
                          >
                            {methods.map((entry) => (
                              <Cell key={entry.method} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip
                            formatter={(v: number, _name, item) =>
                              t('{formatUZS} · {v} ta', {
                                formatUZS: formatUZS(v),
                                v: (item?.payload as { count?: number })?.count ?? 0,
                              })
                            }
                            contentStyle={{
                              borderRadius: 12,
                              border: `1px solid ${CHART.grid}`,
                              fontSize: 13,
                            }}
                          />
                        </PieChart>
                      </ResponsiveContainer>

                      {/* Halqaning o'rtasi bo'sh turmasin — jami shu yerda.
                      `pointer-events-none`: aks holda matn diagramma
                      ustidagi sichqonchani to'sib qo'yardi. */}
                      <div className="pointer-events-none absolute inset-0 grid place-items-center">
                        <div className="text-center">
                          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                            {t('Jami')}
                          </p>
                          <p className="text-base font-bold tabular-nums text-slate-900">
                            {formatMoney(methodTotal)}
                          </p>
                          <p className="text-[11px] text-slate-400">UZS</p>
                        </div>
                      </div>
                    </div>

                    {/* Legend O'RNIGA aniq raqamlar.
                    Diagramma ulushni ko'rsatadi, summani esa faqat sichqoncha
                    ustiga kelganda aytardi — ya'ni telefonda umuman aytmasdi.

                    Qatorning tuzilishi ham muhim: nom CHAPDA o'z joyida
                    o'raladi, summa esa O'NGDA birinchi qatorga bog'langan
                    (`items-start` + bir xil `leading-6`). Ilgari soni nom
                    bilan bitta oqimda turgani uchun uzun nom ("Bank
                    o'tkazmasi") qatorni uchga bo'lib, summani ro'yxatdan
                    surib yuborardi. */}
                    <ul className="w-full space-y-3">
                      {methods.map((entry) => (
                        <li key={entry.method} className="flex items-start gap-2.5">
                          <span
                            className="mt-[9px] h-2 w-2 shrink-0 rounded-full"
                            style={{ backgroundColor: entry.color }}
                          />
                          <span className="min-w-0 flex-1 text-sm font-medium leading-6 text-slate-700">
                            {entry.name}
                          </span>
                          <span className="shrink-0 text-right">
                            <span className="block text-sm font-semibold leading-6 tabular-nums text-slate-900">
                              {formatUZS(entry.value)}
                            </span>
                            <span className="block text-xs leading-4 tabular-nums text-slate-400">
                              {t('{share}% · {v} ta', {
                                share: entry.share.toFixed(1),
                                v: entry.count,
                              })}
                            </span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>
            )}
          </div>

          {/* Davr jadvali — hisobotning o'zi: raqamlar qatorlarda, grafik esa
            faqat ko'z uchun. Telefonda grafik tor, jadval esa o'qiladi. */}
          {rows.length > 0 && (
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
                <h2 className="text-sm font-semibold text-slate-900">{t('Davr kesimi')}</h2>
                {canPL && !payrollInChart && (
                  <p className="flex items-center gap-1.5 text-xs text-slate-500">
                    <Info className="h-3.5 w-3.5 text-slate-400" />
                    {t('Oylik maosh faqat jami qatorda')}
                  </p>
                )}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="px-4 py-2.5 font-medium">{t('Davr')}</th>
                      {showRevenue && (
                        <th className="px-4 py-2.5 text-right font-medium">{t('Tushum')}</th>
                      )}
                      {showExpenses && (
                        <th className="px-4 py-2.5 text-right font-medium">{t('Chiqim')}</th>
                      )}
                      {payrollInChart && (
                        <th className="px-4 py-2.5 text-right font-medium">{t('Oylik maosh')}</th>
                      )}
                      {canPL && (
                        <th className="px-4 py-2.5 text-right font-medium">{t('Sof natija')}</th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {rows.map((row) => (
                      <tr key={row.period} className="tabular-nums">
                        <td className="whitespace-nowrap px-4 py-2 text-slate-700">{row.title}</td>
                        {showRevenue && (
                          <td className="px-4 py-2 text-right text-slate-700">
                            {formatMoney(row.Tushum)}
                          </td>
                        )}
                        {showExpenses && (
                          <td className="px-4 py-2 text-right text-slate-700">
                            {formatMoney(row.Chiqim)}
                          </td>
                        )}
                        {payrollInChart && (
                          <td className="px-4 py-2 text-right text-slate-700">
                            {formatMoney(row['Oylik maosh'])}
                          </td>
                        )}
                        {canPL && (
                          <td
                            className={cn(
                              'px-4 py-2 text-right font-medium',
                              row.net < 0 ? 'text-red-600' : 'text-slate-900',
                            )}
                          >
                            {formatMoney(row.net)}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                  {pl && (
                    <tfoot className="border-t border-slate-200 bg-slate-50/70 font-semibold tabular-nums">
                      <tr>
                        <td className="px-4 py-2.5 text-slate-800">{t('Jami')}</td>
                        <td className="px-4 py-2.5 text-right text-slate-800">
                          {formatMoney(Number(pl.revenue))}
                        </td>
                        <td className="px-4 py-2.5 text-right text-slate-800">
                          {formatMoney(Number(pl.expenses))}
                        </td>
                        {payrollInChart && (
                          <td className="px-4 py-2.5 text-right text-slate-800">
                            {formatMoney(Number(pl.payroll))}
                          </td>
                        )}
                        <td
                          className={cn(
                            'px-4 py-2.5 text-right',
                            Number(pl.net) < 0 ? 'text-red-600' : 'text-emerald-700',
                          )}
                        >
                          {formatMoney(Number(pl.net))}
                          {!payrollInChart && (
                            <span className="block text-[10px] font-normal text-slate-400">
                              {t('oylik {formatMoney} bilan', {
                                formatMoney: formatMoney(Number(pl.payroll)),
                              })}
                            </span>
                          )}
                        </td>
                      </tr>
                    </tfoot>
                  )}
                  {!canPL && (
                    <tfoot className="border-t border-slate-200 bg-slate-50/70 font-semibold tabular-nums">
                      <tr>
                        <td className="px-4 py-2.5 text-slate-800">{t('Jami')}</td>
                        {showRevenue && (
                          <td className="px-4 py-2.5 text-right text-slate-800">
                            {formatMoney(Number(totalRevenue ?? 0))}
                          </td>
                        )}
                        {showExpenses && (
                          <td className="px-4 py-2.5 text-right text-slate-800">
                            {formatMoney(Number(totalExpenses ?? 0))}
                          </td>
                        )}
                      </tr>
                    </tfoot>
                  )}
                </table>
              </div>
            </section>
          )}
        </div>
      )}

      {can('reports.export') && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
          <h2 className="text-sm font-semibold text-slate-900">{t('Eksport')}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t(
              "Excel fayli (.xlsx) — har bir yozuv alohida qator bo'lib tushadi. Tanlangan davr bilan, fayl fonda tayyorlanadi.",
            )}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {EXPORTABLE.filter(([type]) => can(REPORT_SCOPE[type])).map(([type, label]) => (
              <button
                key={type}
                type="button"
                disabled={requestExport.isPending}
                onClick={() => requestExport.mutate(type)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                <FileDown className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>

          {(exportsQuery.data ?? []).length > 0 && (
            <ul className="mt-4 divide-y divide-slate-100 border-t border-slate-100">
              {(exportsQuery.data ?? []).slice(0, 8).map((job) => {
                const [label, tone] = EXPORT_STATUS[job.status] ?? [job.status, 'bg-slate-100']
                return (
                  <li key={job.id} className="flex items-center justify-between gap-3 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-slate-900">
                        {job.report_type}
                      </p>
                      <p className="text-xs text-slate-400">
                        {new Date(job.created_at).toLocaleString('uz-UZ', {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })}
                        {job.status === 'ready' &&
                          t(' · {row_count} qator', { row_count: job.row_count })}
                        {job.error && ` · ${job.error}`}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                        {label}
                      </span>
                      {job.is_ready ? (
                        <button
                          type="button"
                          onClick={() =>
                            void reportsApi.downloadExport(job.id, `${job.report_type}.xlsx`)
                          }
                          className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-brand-700"
                        >
                          <Download className="h-3 w-3" />
                          <span className="hidden sm:inline">{t('Yuklab olish')}</span>
                        </button>
                      ) : (
                        job.status !== 'failed' && (
                          <RefreshCw className="h-3.5 w-3.5 animate-spin text-slate-300" />
                        )
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      )}
    </div>
  )
}
