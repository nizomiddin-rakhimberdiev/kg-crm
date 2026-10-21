/**
 * Soliq va buxgalteriya (Bosqich 13.8, brif §9).
 *
 * Soliq taqvimi: har majburiyat qaysi oy uchun, qancha, qachongacha va
 * holati. "Toʻlash" — haqiqiy pul harakati (qop tanlanadi). Pastda —
 * buxgalterga hisob kodlari bilan jurnal (Excel yoki CSV).
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { QueryError } from '@/components/ui/QueryError'
import { cashApi } from '@/features/cash/api'
import { reportsApi, type TaxItem } from '@/features/dashboard/api'
import { httpClient } from '@/lib/api/client'
import { ApiError } from '@/lib/api/types'
import { formatDate, periodLabel, som, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { MonthInput } from '@/components/ui/MonthInput'

const card = 'rounded-2xl border border-slate-200 bg-white p-4'

const STATUS: Record<TaxItem['status'], { label: string; tone: string }> = {
  paid: { label: t('Toʻlandi'), tone: 'bg-emerald-50 text-emerald-800' },
  upcoming: { label: t('Kutilmoqda'), tone: 'bg-slate-100 text-slate-700' },
  due: { label: t('Muddati yaqin'), tone: 'bg-orik-50 text-orik-800' },
  overdue: { label: t('Muddati oʻtdi'), tone: 'bg-red-50 text-red-700' },
}

function Calendar() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const [year, setYear] = useState(() => new Date(today()).getFullYear())
  const query = useQuery({
    queryKey: ['org', organizationId, 'reports', 'tax-calendar', year],
    queryFn: () => reportsApi.taxCalendar(year),
  })
  const accounts = useQuery({
    queryKey: ['org', organizationId, 'cash', 'accounts'],
    queryFn: cashApi.accounts,
    enabled: can('reports.approve'),
  })
  const pots = (accounts.data?.items ?? []).filter((row) => row.is_active)
  const [potId, setPotId] = useState('')
  const pot = potId || pots.find((row) => row.kind === 'bank')?.id || ''
  const [error, setError] = useState<string | null>(null)
  const pay = useMutation({
    mutationFn: (id: string) => reportsApi.payTax(id, pot),
    onSuccess: () => {
      setError(null)
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId] })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  if (query.isError) return <QueryError error={query.error} onRetry={() => void query.refetch()} />
  const data = query.data
  return (
    <section className={card} aria-labelledby="tax-title">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h3 id="tax-title" className="text-sm font-semibold text-slate-900">
          {t('Soliq taqvimi')}
        </h3>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label htmlFor="tax-year" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Yil')}
            </label>
            <input
              id="tax-year"
              type="number"
              min={2020}
              max={2100}
              value={year}
              onChange={(event) => setYear(Number(event.target.value) || year)}
              className="w-24 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
          </div>
          {can('reports.approve') && pots.length > 0 && (
            <div>
              <label htmlFor="tax-pot" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Qaysi hisobdan')}
              </label>
              <select
                id="tax-pot"
                value={pot}
                onChange={(event) => setPotId(event.target.value)}
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              >
                {pots.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>
      {data && (
        <p className="mt-1 text-sm text-slate-600">
          {t('Toʻlanmagan: {money}', { money: som(data.unpaid) })}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <div className="mt-2 overflow-x-auto">
        <table className="w-full min-w-[34rem] text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="px-2 py-1 font-medium">{t('Soliq')}</th>
              <th className="px-2 py-1 font-medium">{t('Oy')}</th>
              <th className="px-2 py-1 font-medium">{t('Muddat')}</th>
              <th className="px-2 py-1 text-right font-medium">{t('Summa')}</th>
              <th className="px-2 py-1 font-medium">{t('Holat')}</th>
              <th className="px-2 py-1" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(data?.items ?? []).map((item) => (
              <tr key={item.id}>
                <td className="px-2 py-1.5 text-slate-800">{item.title}</td>
                <td className="px-2 py-1.5 text-slate-600">{periodLabel(item.period)}</td>
                <td className="px-2 py-1.5 text-slate-600">{formatDate(item.due_date)}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{som(item.amount)}</td>
                <td className="px-2 py-1.5">
                  <span
                    className={cn(
                      'rounded-full px-2 py-0.5 text-xs font-medium',
                      STATUS[item.status].tone,
                    )}
                  >
                    {STATUS[item.status].label}
                  </span>
                </td>
                <td className="px-2 py-1.5 text-right">
                  {item.status !== 'paid' && can('reports.approve') && pot && (
                    <button
                      type="button"
                      disabled={pay.isPending}
                      onClick={() => pay.mutate(item.id)}
                      className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      {t('Toʻlash')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-2 py-3 text-center text-sm text-slate-500">
                  {t('Bu yil uchun soliq majburiyati yoʻq.')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function Journal() {
  const { selectedBranchId } = useBranchScope()
  const [period, setPeriod] = useState(() => today().slice(0, 7))
  const [year, month] = period.split('-').map(Number)
  const download = async (file: 'xlsx' | 'csv') => {
    const response = await httpClient.get('/reports/journal', {
      params: { year, month, file, ...(selectedBranchId ? { branch: selectedBranchId } : {}) },
      responseType: 'blob',
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(response.data as Blob)
    link.download = `jurnal-${period}.${file}`
    link.click()
    URL.revokeObjectURL(link.href)
  }
  return (
    <section className={card} aria-labelledby="journal-title">
      <h3 id="journal-title" className="text-sm font-semibold text-slate-900">
        {t('Buxgalter uchun jurnal')}
      </h3>
      <p className="mt-1 text-xs text-slate-500">
        {t('Har pul harakati va hisoblash Dt/Kt hisob kodlari bilan. Kodlar — Sozlamalarda.')}
      </p>
      <div className="mt-2 flex flex-wrap items-end gap-2">
        <MonthInput id="journal-month" label={t('Oy')} value={period} onChange={setPeriod} />
        {(['xlsx', 'csv'] as const).map((file) => (
          <button
            key={file}
            type="button"
            onClick={() => void download(file)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-4 w-4" aria-hidden />
            {file === 'xlsx' ? 'Excel' : 'CSV'}
          </button>
        ))}
      </div>
    </section>
  )
}

export function TaxTab() {
  return (
    <div className="space-y-4">
      <Calendar />
      <Journal />
    </div>
  )
}
