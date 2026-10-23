/**
 * Reja va prognoz (Bosqich 13.7, brif §5.3-12, §6).
 *
 * Birinchi savol — "qancha pul olsam boʻladi?": xavfsiz olish summasi va
 * uning formulasi. Keyin 30/60/90 kunlik prognoz (har qatori asosi bilan),
 * oylik reja va fakt, koʻrsatkichlar taʼrifi bilan, 12 oylik trend va
 * yillik hisobot. Fakt serverda modul selektorlaridan — bu yerda hech
 * narsa qayta hisoblanmaydi.
 */

import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, Download, FileText, Info, Plus } from 'lucide-react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { QueryError } from '@/components/ui/QueryError'
import { reportsApi, type KpiItem, type PackUnit } from '@/features/dashboard/api'
import { expensesApi } from '@/features/expenses/api'
import { httpClient } from '@/lib/api/client'
import { ApiError } from '@/lib/api/types'
import { BRAND, CHART } from '@/lib/brand'
import { axisMoney, formatDate, periodLabel, som, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { MonthInput } from '@/components/ui/MonthInput'
import { Select } from '@/components/ui/Select'

const FLOW_LABELS: Record<string, string> = {
  tuition: t('Ota-ona toʻlovlari'),
  payroll: t('Ish haqi'),
  taxes: t('Soliqlar'),
  suppliers: t('Nasiya (yetkazib beruvchilar)'),
  expenses: t('Doimiy chiqimlar'),
}

const card = 'rounded-2xl border border-slate-200 bg-white p-4'
function SafeWithdrawal({ branch }: { branch: string | null }) {
  const organizationId = useOrganizationId()
  const query = useQuery({
    queryKey: ['org', organizationId, 'reports', 'forecast', branch],
    queryFn: () => reportsApi.forecast(branch),
  })
  if (query.isError) return <QueryError error={query.error} onRetry={() => void query.refetch()} />
  const data = query.data
  if (!data) return null
  const safe = data.safe_withdrawal
  const short = Number(safe.shortfall) > 0
  return (
    <>
      <section className={card} aria-labelledby="safe-title">
        <h3 id="safe-title" className="text-sm font-semibold text-slate-900">
          {t('Qancha pul olsa boʻladi?')}
        </h3>
        <p
          className={cn(
            'mt-1 text-3xl font-bold tabular-nums',
            short ? 'text-red-700' : 'text-slate-900',
          )}
        >
          {som(safe.amount)}
        </p>
        <dl className="mt-3 space-y-1 text-sm">
          <div className="flex justify-between gap-3">
            <dt className="text-slate-600">{t('Kassa + bank + yoʻldagi pul')}</dt>
            <dd className="tabular-nums">{som(safe.money)}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-slate-600">{t('− kelgusi 30 kun majburiyatlari')}</dt>
            <dd className="tabular-nums">{som(safe.obligations_30)}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-slate-600">
              {t('− zaxira')} <span className="text-xs text-slate-500">({safe.reserve_basis})</span>
            </dt>
            <dd className="tabular-nums">{som(safe.reserve)}</dd>
          </div>
        </dl>
        {short && (
          <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {t('Pul yetmaydi: 30 kun ichida {money} soʻm kam.', { money: som(safe.shortfall) })}
          </p>
        )}
      </section>

      <section className={card} aria-labelledby="forecast-title">
        <h3 id="forecast-title" className="text-sm font-semibold text-slate-900">
          {t('Pul prognozi — {date} dan', { date: formatDate(data.as_of) })}
        </h3>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[28rem] text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th className="px-2 py-1 font-medium" />
                {data.buckets.map((bucket) => (
                  <th key={bucket.days} className="px-2 py-1 text-right font-medium">
                    {t('{n} kun', { n: bucket.days })}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr>
                <td className="px-2 py-1 text-slate-600">{t('Hozir bor')}</td>
                {data.buckets.map((bucket) => (
                  <td key={bucket.days} className="px-2 py-1 text-right tabular-nums">
                    {som(data.opening)}
                  </td>
                ))}
              </tr>
              {Object.keys(data.buckets[0]?.inflows ?? {})
                .filter((key) => key !== 'total')
                .map((key) => (
                  <tr key={`in-${key}`}>
                    <td className="px-2 py-1 text-slate-600">+ {FLOW_LABELS[key] ?? key}</td>
                    {data.buckets.map((bucket) => (
                      <td key={bucket.days} className="px-2 py-1 text-right tabular-nums">
                        {som(bucket.inflows[key])}
                      </td>
                    ))}
                  </tr>
                ))}
              {Object.keys(data.buckets[0]?.outflows ?? {})
                .filter((key) => key !== 'total')
                .map((key) => (
                  <tr key={`out-${key}`}>
                    <td className="px-2 py-1 text-slate-600">− {FLOW_LABELS[key] ?? key}</td>
                    {data.buckets.map((bucket) => (
                      <td key={bucket.days} className="px-2 py-1 text-right tabular-nums">
                        {som(bucket.outflows[key])}
                      </td>
                    ))}
                  </tr>
                ))}
              <tr className="font-semibold">
                <td className="px-2 py-1">{t('Qoladi')}</td>
                {data.buckets.map((bucket) => (
                  <td
                    key={bucket.days}
                    className={cn(
                      'px-2 py-1 text-right tabular-nums',
                      Number(bucket.closing) < 0 && 'text-red-700',
                    )}
                  >
                    {som(bucket.closing)}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-slate-500">{data.basis.excluded}</p>
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer font-medium text-slate-700">
            {t('Har qatorning asosi — {n}', { n: data.lines.length })}
          </summary>
          <ul className="mt-2 space-y-1">
            {data.lines.map((line, index) => (
              <li key={index} className="flex flex-wrap justify-between gap-2">
                <span className="text-slate-600">
                  {formatDate(line.date)} · {line.basis}
                </span>
                <span
                  className={cn(
                    'tabular-nums',
                    line.direction === 'in' ? 'text-emerald-700' : 'text-slate-900',
                  )}
                >
                  {line.direction === 'in' ? '+' : '−'}
                  {som(line.amount)}
                </span>
              </li>
            ))}
          </ul>
        </details>
      </section>
    </>
  )
}

function Budget({ at }: { at: PackUnit }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const editable = can('reports.update')
  const key = ['org', organizationId, 'reports', 'budget', at.year, at.month, at.branch ?? null]
  const query = useQuery({ queryKey: key, queryFn: () => reportsApi.budget(at) })
  const categories = useQuery({
    queryKey: ['org', organizationId, 'expense-categories', 'recent'],
    queryFn: expensesApi.recentCategories,
    enabled: editable,
  })
  const [plans, setPlans] = useState<Record<string, string>>({})
  const [extra, setExtra] = useState<Array<{ id: string; name: string }>>([])
  const [adding, setAdding] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const next: Record<string, string> = {}
    for (const row of query.data?.lines ?? []) {
      next[`${row.kind}:${row.category_id ?? ''}`] = String(Number(row.plan))
    }
    setPlans(next)
    setExtra([])
  }, [query.data])

  const onDone = {
    onSuccess: () => {
      setError(null)
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'reports'] })
    },
    onError: (err: unknown) =>
      setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  }
  const save = useMutation({
    mutationFn: () =>
      reportsApi.saveBudget(
        at,
        Object.entries(plans)
          .filter(([, amount]) => amount !== '')
          .map(([rowKey, amount]) => {
            const [kind, category] = rowKey.split(':')
            return { kind, ...(category ? { category_id: category } : {}), amount }
          }),
      ),
    ...onDone,
  })
  const previous = new Date(at.year, at.month - 2, 1)
  const copy = useMutation({
    mutationFn: () => reportsApi.copyBudget(at, previous.getFullYear(), previous.getMonth() + 1),
    ...onDone,
  })

  if (query.isError) return <QueryError error={query.error} onRetry={() => void query.refetch()} />
  const data = query.data
  if (!data) return null
  const rows = [
    ...data.lines,
    ...extra.map((item) => ({
      kind: 'category' as const,
      label: item.name,
      plan: '0',
      actual: '0',
      difference: '0',
      percent: null,
      category_id: item.id,
    })),
  ]
  const used = new Set(rows.map((row) => row.category_id).filter(Boolean))

  return (
    <section className={card} aria-labelledby="budget-title">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="budget-title" className="text-sm font-semibold text-slate-900">
          {t('Reja va fakt')}
        </h3>
        {editable && (
          <button
            type="button"
            onClick={() => copy.mutate()}
            disabled={copy.isPending}
            className="flex items-center gap-1.5 text-xs font-medium text-brand-700 disabled:opacity-50"
          >
            <Copy className="h-3.5 w-3.5" aria-hidden />
            {t('Oʻtgan oy rejasini koʻchirish')}
          </button>
        )}
      </div>
      {!data.has_plan && (
        <p className="mt-1 text-xs text-slate-500">{t('Bu oyga reja kiritilmagan.')}</p>
      )}
      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[32rem] text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="px-2 py-1 font-medium">{t('Qator')}</th>
              <th className="px-2 py-1 text-right font-medium">{t('Reja')}</th>
              <th className="px-2 py-1 text-right font-medium">{t('Fakt')}</th>
              <th className="px-2 py-1 text-right font-medium">{t('Farq')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => {
              const rowKey = `${row.kind}:${row.category_id ?? ''}`
              const id = `plan-${rowKey}`
              return (
                <tr key={rowKey}>
                  <td className="px-2 py-1.5">
                    <label htmlFor={id} className="text-slate-700">
                      {row.label}
                    </label>
                  </td>
                  <td className="px-2 py-1.5 text-right">
                    {editable ? (
                      <input
                        id={id}
                        inputMode="numeric"
                        value={plans[rowKey] ?? ''}
                        onChange={(event) =>
                          setPlans((current) => ({
                            ...current,
                            [rowKey]: event.target.value.replace(/[^\d]/g, ''),
                          }))
                        }
                        className="w-32 rounded-lg border border-slate-200 px-2 py-1 text-right text-sm tabular-nums outline-none focus:border-brand-500"
                      />
                    ) : (
                      <span id={id} className="tabular-nums">
                        {som(row.plan)}
                      </span>
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{som(row.actual)}</td>
                  <td
                    className={cn(
                      'px-2 py-1.5 text-right tabular-nums',
                      Number(row.difference) < 0 ? 'text-red-700' : 'text-slate-700',
                    )}
                  >
                    {som(row.difference)}
                    {row.percent && (
                      <span className="ml-1 text-xs text-slate-500">({row.percent}%)</span>
                    )}
                  </td>
                </tr>
              )
            })}
            {(['income', 'expenses', 'result'] as const).map((totalKey) => (
              <tr key={totalKey} className="font-semibold">
                <td className="px-2 py-1.5">
                  {
                    {
                      income: t('Jami daromad'),
                      expenses: t('Jami chiqim'),
                      result: t('Natija'),
                    }[totalKey]
                  }
                </td>
                <td className="px-2 py-1.5 text-right tabular-nums">
                  {som(data.totals[totalKey].plan)}
                </td>
                <td className="px-2 py-1.5 text-right tabular-nums">
                  {som(data.totals[totalKey].actual)}
                </td>
                <td />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editable && (
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label
              htmlFor="budget-category"
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {t('Chiqim toifasini qoʻshish')}
            </label>
            <Select
              id="budget-category"
              value={adding}
              onChange={(event) => setAdding(event.target.value)}
            >
              <option value="">—</option>
              {(categories.data?.items ?? [])
                .filter((item) => !used.has(item.id))
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
            </Select>
          </div>
          <button
            type="button"
            disabled={!adding}
            onClick={() => {
              const found = categories.data?.items.find((item) => item.id === adding)
              if (found) {
                setExtra((current) => [...current, { id: found.id, name: found.name }])
                setPlans((current) => ({ ...current, [`category:${found.id}`]: '' }))
              }
              setAdding('')
            }}
            className="flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            <Plus className="h-4 w-4" aria-hidden />
            {t('Qoʻshish')}
          </button>
          <button
            type="button"
            disabled={save.isPending}
            onClick={() => save.mutate()}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {t('Rejani saqlash')}
          </button>
        </div>
      )}
    </section>
  )
}

function kpiValue(item: KpiItem): string {
  if (item.value === null || item.value === undefined || item.value === '') return '—'
  if (item.unit === '%') return `${item.value}%`
  if (item.unit === 'som') return som(String(item.value))
  if (item.unit === 'months') return t('{n} oy', { n: item.value })
  return String(item.value)
}

function Kpis({ at }: { at: PackUnit }) {
  const organizationId = useOrganizationId()
  const query = useQuery({
    queryKey: ['org', organizationId, 'reports', 'kpi', at.year, at.month, at.branch ?? null],
    queryFn: () => reportsApi.kpi(at),
  })
  const [open, setOpen] = useState<string | null>(null)
  if (query.isError) return <QueryError error={query.error} onRetry={() => void query.refetch()} />
  return (
    <section className={card} aria-labelledby="kpi-title">
      <h3 id="kpi-title" className="text-sm font-semibold text-slate-900">
        {t('Koʻrsatkichlar')}
      </h3>
      <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {(query.data?.items ?? []).map((item) => (
          <div key={item.id} className="rounded-xl bg-slate-50 px-3 py-2">
            <div className="flex items-start justify-between gap-2">
              <p className="text-xs text-slate-600">{item.title}</p>
              <button
                type="button"
                aria-label={t('{name} — taʼrif', { name: item.title })}
                aria-expanded={open === item.id}
                onClick={() => setOpen(open === item.id ? null : item.id)}
                className="rounded text-slate-500 hover:text-slate-800"
              >
                <Info className="h-4 w-4" aria-hidden />
              </button>
            </div>
            <p className="text-lg font-bold tabular-nums text-slate-900">{kpiValue(item)}</p>
            {open === item.id && <p className="mt-1 text-xs text-slate-600">{item.definition}</p>}
          </div>
        ))}
      </div>
    </section>
  )
}

function Trends({ at }: { at: PackUnit }) {
  const organizationId = useOrganizationId()
  const query = useQuery({
    queryKey: ['org', organizationId, 'reports', 'trends', at.year, at.month, at.branch ?? null],
    queryFn: () => reportsApi.trends(at),
  })
  if (query.isError) return <QueryError error={query.error} onRetry={() => void query.refetch()} />
  const rows = (query.data?.months ?? []).map((row) => ({
    label: periodLabel(row.period),
    [t('Daromad')]: Number(row.revenue),
    [t('Tushum')]: Number(row.receipts),
    [t('Operatsion foyda')]: Number(row.operating_profit),
  }))
  const series: Array<[string, string]> = [
    [t('Daromad'), BRAND.nihol],
    [t('Tushum'), CHART.ildizMid],
    [t('Operatsion foyda'), BRAND.orik],
  ]
  return (
    <section className={card} aria-labelledby="trend-title">
      <h3 id="trend-title" className="text-sm font-semibold text-slate-900">
        {t('12 oylik trend')}
      </h3>
      <div className="mt-2 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={CHART.grid} />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              fontSize={12}
              tick={{ fill: CHART.label }}
              interval="preserveStartEnd"
              minTickGap={16}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              fontSize={12}
              tick={{ fill: CHART.label }}
              width={56}
              tickFormatter={(value: number) => axisMoney(value)}
            />
            <Tooltip
              formatter={(value: number) => som(value)}
              contentStyle={{ borderRadius: 12, border: `1px solid ${CHART.grid}`, fontSize: 13 }}
            />
            <Legend
              iconType="circle"
              wrapperStyle={{ fontSize: 12 }}
              formatter={(value: string) => <span style={{ color: CHART.label }}>{value}</span>}
            />
            {series.map(([name, color]) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={color}
                strokeWidth={2}
                dot={{ r: 2 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

async function download(url: string, params: Record<string, unknown>, name: string) {
  const response = await httpClient.get(url, { params, responseType: 'blob' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(response.data as Blob)
  link.download = name
  link.click()
  URL.revokeObjectURL(link.href)
}

function Annual({ branch }: { branch: string | null }) {
  const [year, setYear] = useState(() => new Date(today()).getFullYear())
  const params = { year, ...(branch ? { branch } : {}) }
  return (
    <section className={card} aria-labelledby="annual-title">
      <h3 id="annual-title" className="text-sm font-semibold text-slate-900">
        {t('Yillik hisobot')}
      </h3>
      <div className="mt-2 flex flex-wrap items-end gap-2">
        <div>
          <label htmlFor="annual-year" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Yil')}
          </label>
          <input
            id="annual-year"
            type="number"
            min={2020}
            max={2100}
            value={year}
            onChange={(event) => setYear(Number(event.target.value) || year)}
            className="w-28 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </div>
        <button
          type="button"
          onClick={() => void download('/reports/annual/pdf', params, `yillik-${year}.pdf`)}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <FileText className="h-4 w-4" aria-hidden />
          PDF
        </button>
        <button
          type="button"
          onClick={() => void download('/reports/annual/xlsx', params, `yillik-${year}.xlsx`)}
          className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <Download className="h-4 w-4" aria-hidden />
          Excel
        </button>
      </div>
    </section>
  )
}

export function PlanTab() {
  const { selectedBranchId } = useBranchScope()
  const [period, setPeriod] = useState(() => today().slice(0, 7))
  const [year, month] = period.split('-').map(Number)
  const at: PackUnit = { year, month, branch: selectedBranchId }
  return (
    <div className="space-y-4">
      <SafeWithdrawal branch={selectedBranchId} />
      <MonthInput id="plan-month" label={t('Oy')} value={period} onChange={setPeriod} />
      <Budget at={at} />
      <Kpis at={at} />
      <Trends at={at} />
      <Annual branch={selectedBranchId} />
    </div>
  )
}
