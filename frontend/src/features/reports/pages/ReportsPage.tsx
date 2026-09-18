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
import { bucketLabel, bucketTitle, groupByFor, periodFor, type Period } from '@/features/reports/period'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatMoney, formatUZS } from '@/lib/utils'

const METHOD_LABEL: Record<string, string> = {
  cash: 'Naqd pul',
  card: 'Plastik karta',
  transfer: "Bank o'tkazmasi",
  online: 'Onlayn',
}
const PIE_COLORS = ['#6366f1', '#14b8a6', '#f59e0b', '#ef4444']
const COLORS = { revenue: '#6366f1', expenses: '#f59e0b', payroll: '#94a3b8' }

const EXPORTABLE: Array<[string, string]> = [
  ['profit-loss', 'Foyda va zarar'],
  ['revenue', 'Tushum'],
  ['expenses', 'Chiqimlar'],
  ['debtors', 'Qarzdorlar'],
  ['payroll', 'Oylik maosh'],
  ['attendance', 'Davomat'],
]

const EXPORT_STATUS: Record<string, [string, string]> = {
  queued: ['Navbatda', 'bg-slate-100 text-slate-600'],
  running: ['Tayyorlanmoqda', 'bg-sky-50 text-sky-700'],
  ready: ['Tayyor', 'bg-emerald-50 text-emerald-700'],
  failed: ['Xato', 'bg-red-50 text-red-700'],
}

/** Grafik o'qi uchun qisqa pul: 1 200 000 → "1.2 mln". */
const compactUZS = (value: number) => {
  const abs = Math.abs(value)
  if (abs >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)} mlrd`
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)} mln`
  if (abs >= 1_000) return `${Math.round(value / 1_000)} ming`
  return String(value)
}

export default function ReportsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [period, setPeriod] = useState<Period>(() => periodFor('month', new Date()))
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const groupBy = groupByFor(period)

  const plQuery = useQuery({
    queryKey: queryKeys.reportProfitLoss(organizationId, period.from, period.to, groupBy),
    queryFn: () => reportsApi.profitLoss(period.from, period.to, groupBy),
    placeholderData: keepPreviousData,
  })
  const revenueQuery = useQuery({
    queryKey: queryKeys.reportRevenue(organizationId, period.from, period.to, groupBy),
    queryFn: () => reportsApi.revenue(period.from, period.to, groupBy),
    placeholderData: keepPreviousData,
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
      setNotice('Eksport navbatga qo’yildi — tayyor bo‘lganda yuklab olasiz.')
      void queryClient.invalidateQueries({ queryKey: queryKeys.reportExports(organizationId) })
    },
    onError: (err: unknown) => {
      setNotice(null)
      setError(err instanceof ApiError ? err.message : 'Eksportni boshlab bo‘lmadi.')
    },
  })

  const pl = plQuery.data
  const payrollInChart = pl?.payroll_in_periods ?? true
  const rows = (pl?.by_period ?? []).map((row) => ({
    period: row.period,
    label: bucketLabel(row.period, groupBy),
    title: bucketTitle(row.period, groupBy),
    Tushum: Number(row.revenue),
    Chiqim: Number(row.expenses),
    'Oylik maosh': Number(row.payroll),
    net: Number(row.net),
  }))
  const methods = (revenueQuery.data?.by_method ?? []).map((row) => ({
    name: METHOD_LABEL[row.method] ?? row.method,
    value: Number(row.total),
    count: row.count,
  }))
  const loadError =
    (plQuery.error ?? revenueQuery.error) instanceof ApiError
      ? ((plQuery.error ?? revenueQuery.error) as ApiError).message
      : null
  const refreshing = plQuery.isPlaceholderData || revenueQuery.isPlaceholderData

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Hisobotlar</h1>
          <p className="mt-1 text-sm text-slate-500">
            Kassa usuli: daromad — qabul qilingan pul, yozilgan hisob-faktura emas.
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

      <div className={cn('space-y-6 transition-opacity', refreshing && 'opacity-60')}>
        {/* KPI */}
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {[
            ['Tushum', pl?.revenue, 'text-emerald-600', `${revenueQuery.data?.payment_count ?? 0} ta to'lov`],
            ['Chiqimlar', pl?.expenses, 'text-slate-900', 'tasdiqlangan va to‘langan'],
            ['Oylik maosh', pl?.payroll, 'text-slate-900', payrollInChart ? 'yakunlangan davrlar' : 'oy kesimida hisoblanadi'],
            ['Sof natija', pl?.net, Number(pl?.net ?? 0) < 0 ? 'text-red-600' : 'text-emerald-600', 'tushum − chiqim − oylik'],
          ].map(([label, value, tone, hint]) => (
            <div key={label as string} className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
              <p className="text-sm font-medium text-slate-600">{label as string}</p>
              <p className={cn('mt-1.5 text-xl font-bold tracking-tight tabular-nums sm:text-2xl', tone as string)}>
                {value === undefined ? '…' : formatUZS(Number(value))}
              </p>
              <p className="mt-1 text-xs text-slate-400">{hint as string}</p>
            </div>
          ))}
        </div>

        {/* Grafiklar */}
        <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr] lg:gap-6">
          <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
            <h2 className="text-sm font-semibold text-slate-900">Tushum va chiqim</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {payrollInChart
                ? 'Chiqim ustuni: xarajat + oylik maosh (ustma-ust)'
                : 'Kun/hafta kesimida oylik maosh ustunlarga kirmaydi — u jami ko‘rsatkichda'}
            </p>
            <div className="mt-4 h-64 sm:h-72">
              {rows.length === 0 ? (
                <p className="grid h-full place-items-center text-sm text-slate-400">
                  Bu davrda ma'lumot yo'q.
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
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
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
                      contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="Tushum" fill={COLORS.revenue} radius={[6, 6, 0, 0]} maxBarSize={40} />
                    <Bar
                      dataKey="Chiqim"
                      stackId="cost"
                      fill={COLORS.expenses}
                      radius={payrollInChart ? [0, 0, 0, 0] : [6, 6, 0, 0]}
                      maxBarSize={40}
                    />
                    {payrollInChart && (
                      <Bar
                        dataKey="Oylik maosh"
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

          <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
            <h2 className="text-sm font-semibold text-slate-900">To'lov usullari</h2>
            <p className="mt-0.5 text-xs text-slate-500">Davr ichida qabul qilingan pul</p>
            <div className="mt-4 h-64 sm:h-72">
              {methods.length === 0 ? (
                <p className="grid h-full place-items-center text-sm text-slate-400">
                  Bu davrda to'lov yo'q.
                </p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={methods} dataKey="value" nameKey="name" innerRadius="52%" outerRadius="82%">
                      {methods.map((entry, index) => (
                        <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(v: number, _name, item) =>
                        `${formatUZS(v)} · ${(item?.payload as { count?: number })?.count ?? 0} ta`
                      }
                      contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
          </section>
        </div>

        {/* Davr jadvali — hisobotning o'zi: raqamlar qatorlarda, grafik esa
            faqat ko'z uchun. Telefonda grafik tor, jadval esa o'qiladi. */}
        {rows.length > 0 && (
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-900">Davr kesimi</h2>
              {!payrollInChart && (
                <p className="flex items-center gap-1.5 text-xs text-slate-500">
                  <Info className="h-3.5 w-3.5 text-slate-400" />
                  Oylik maosh faqat jami qatorda
                </p>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead className="bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Davr</th>
                    <th className="px-4 py-2.5 text-right font-medium">Tushum</th>
                    <th className="px-4 py-2.5 text-right font-medium">Chiqim</th>
                    {payrollInChart && <th className="px-4 py-2.5 text-right font-medium">Oylik</th>}
                    <th className="px-4 py-2.5 text-right font-medium">Sof</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((row) => (
                    <tr key={row.period} className="tabular-nums">
                      <td className="whitespace-nowrap px-4 py-2 text-slate-700">{row.title}</td>
                      <td className="px-4 py-2 text-right text-slate-700">{formatMoney(row.Tushum)}</td>
                      <td className="px-4 py-2 text-right text-slate-700">{formatMoney(row.Chiqim)}</td>
                      {payrollInChart && (
                        <td className="px-4 py-2 text-right text-slate-700">
                          {formatMoney(row['Oylik maosh'])}
                        </td>
                      )}
                      <td
                        className={cn(
                          'px-4 py-2 text-right font-medium',
                          row.net < 0 ? 'text-red-600' : 'text-slate-900',
                        )}
                      >
                        {formatMoney(row.net)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                {pl && (
                  <tfoot className="border-t border-slate-200 bg-slate-50/70 font-semibold tabular-nums">
                    <tr>
                      <td className="px-4 py-2.5 text-slate-800">Jami</td>
                      <td className="px-4 py-2.5 text-right text-slate-800">{formatMoney(Number(pl.revenue))}</td>
                      <td className="px-4 py-2.5 text-right text-slate-800">{formatMoney(Number(pl.expenses))}</td>
                      {payrollInChart && (
                        <td className="px-4 py-2.5 text-right text-slate-800">{formatMoney(Number(pl.payroll))}</td>
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
                            oylik {formatMoney(Number(pl.payroll))} bilan
                          </span>
                        )}
                      </td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </div>
          </section>
        )}
      </div>

      {can('reports.export') && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
          <h2 className="text-sm font-semibold text-slate-900">Eksport</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            CSV — Excel ham, Google Sheets ham ochadi. Tanlangan davr va kesim bilan, fayl fonda
            tayyorlanadi.
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {EXPORTABLE.map(([type, label]) => (
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
                      <p className="truncate text-sm font-medium text-slate-900">{job.report_type}</p>
                      <p className="text-xs text-slate-400">
                        {new Date(job.created_at).toLocaleString('uz-UZ', {
                          dateStyle: 'short',
                          timeStyle: 'short',
                        })}
                        {job.status === 'ready' && ` · ${job.row_count} qator`}
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
                            void reportsApi.downloadExport(job.id, `${job.report_type}.csv`)
                          }
                          className="inline-flex items-center gap-1 rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-brand-700"
                        >
                          <Download className="h-3 w-3" />
                          <span className="hidden sm:inline">Yuklab olish</span>
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
