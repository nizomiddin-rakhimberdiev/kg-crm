/**
 * Hisobotlar (docs/04 §14.2).
 *
 * Sahifada `basis` ochiq yozilgan: "daromad" so'zi ikki xil ma'noga ega —
 * yozilgan hisob-faktura va qabul qilingan pul. Ekranda qaysi biri
 * ekanini o'qiyotgan odam taxmin qilmasligi kerak.
 *
 * Eksport darhol fayl bermaydi: u ish yaratadi va fon ishchisi tayyorlaydi.
 * Katta davrni so'rov ichida hisoblash brauzerni kutdirib qo'yardi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, FileDown, RefreshCw } from 'lucide-react'
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
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatUZS } from '@/lib/utils'

const MONTHS = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']
const shortMonth = (iso: string) => MONTHS[Number(iso.slice(5, 7)) - 1] ?? iso

const METHOD_LABEL: Record<string, string> = {
  cash: 'Naqd pul',
  card: 'Plastik karta',
  transfer: "Bank o'tkazmasi",
  online: 'Onlayn',
}
const PIE_COLORS = ['#6366f1', '#14b8a6', '#f59e0b', '#ef4444']

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

const defaultRange = () => {
  const now = new Date()
  const from = new Date(now.getFullYear(), now.getMonth() - 5, 1)
  return {
    from: from.toISOString().slice(0, 10),
    to: now.toISOString().slice(0, 10),
  }
}

export default function ReportsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [range, setRange] = useState(defaultRange)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const plQuery = useQuery({
    queryKey: queryKeys.reportProfitLoss(organizationId, range.from, range.to),
    queryFn: () => reportsApi.profitLoss(range.from, range.to),
  })
  const revenueQuery = useQuery({
    queryKey: queryKeys.reportRevenue(organizationId, range.from, range.to),
    queryFn: () => reportsApi.revenue(range.from, range.to),
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
      reportsApi.requestExport(reportType, { date_from: range.from, date_to: range.to }),
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
  const chart = (pl?.by_month ?? []).map((row) => ({
    month: shortMonth(row.month),
    Tushum: Number(row.revenue),
    Chiqim: Number(row.expenses) + Number(row.payroll),
  }))
  const methods = (revenueQuery.data?.by_method ?? []).map((row) => ({
    name: METHOD_LABEL[row.method] ?? row.method,
    value: Number(row.total),
  }))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Hisobotlar</h1>
          <p className="mt-1 text-sm text-slate-500">
            Kassa usuli: daromad — qabul qilingan pul, yozilgan hisob-faktura emas.
          </p>
        </div>
        <div className="flex items-end gap-2">
          <label className="text-xs font-medium text-slate-600">
            Dan
            <input
              type="date"
              value={range.from}
              onChange={(e) => setRange((prev) => ({ ...prev, from: e.target.value }))}
              className="mt-1 block rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </label>
          <label className="text-xs font-medium text-slate-600">
            Gacha
            <input
              type="date"
              value={range.to}
              onChange={(e) => setRange((prev) => ({ ...prev, to: e.target.value }))}
              className="mt-1 block rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </label>
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['Tushum', pl?.revenue, 'text-emerald-600'],
          ['Chiqimlar', pl?.expenses, 'text-slate-900'],
          ['Oylik maosh', pl?.payroll, 'text-slate-900'],
          ['Sof natija', pl?.net, Number(pl?.net ?? 0) < 0 ? 'text-red-600' : 'text-emerald-600'],
        ].map(([label, value, tone]) => (
          <div key={label as string} className="rounded-2xl border border-slate-200 bg-white p-5">
            <p className="text-sm font-medium text-slate-600">{label as string}</p>
            <p className={cn('mt-2 text-2xl font-bold tracking-tight', tone as string)}>
              {value === undefined ? '…' : formatUZS(Number(value))}
            </p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Tushum va chiqim</h2>
          <p className="mt-0.5 text-xs text-slate-500">Chiqimga oylik maosh ham qo'shilgan</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="month" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                  tickFormatter={(v: number) => `${Math.round(v / 1_000_000)}mln`}
                />
                <Tooltip
                  formatter={(v: number) => formatUZS(v)}
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Tushum" fill="#6366f1" radius={[6, 6, 0, 0]} />
                <Bar dataKey="Chiqim" fill="#f59e0b" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">To'lov usullari</h2>
          <div className="mt-4 h-72">
            {methods.length === 0 ? (
              <p className="grid h-full place-items-center text-sm text-slate-400">
                Bu davrda to'lov yo'q.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={methods} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90}>
                    {methods.map((entry, index) => (
                      <Cell key={entry.name} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: number) => formatUZS(v)}
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 13 }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </section>
      </div>

      {can('reports.export') && (
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Eksport</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            CSV — Excel ham, Google Sheets ham ochadi. Fayl fonda tayyorlanadi.
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
                      <p className="text-sm font-medium text-slate-900">{job.report_type}</p>
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
                          Yuklab olish
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
