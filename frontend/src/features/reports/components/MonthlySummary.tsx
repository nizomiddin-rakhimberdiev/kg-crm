/**
 * Oylik yigʻma va oyni yopish (Bosqich 12.6, brif §6).
 *
 * Ikki koʻrinish ataylab yonma-yon: "kassa tushumi" — pul QAYSI OYDA
 * kelgan, "oy uchun yigʻilgan" — pul QAYSI OY fakturasini yopgan. Bitta
 * toʻlov ikkalasida bittadan; Excel'da avans ikki marta sanalardi.
 *
 * Tenglik serverda turli manbalardan tekshiriladi va bu yerda faqat
 * yashil/qizil boʻlib koʻrinadi; qizil oy yopilmaydi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Download, Lock, XCircle } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { reportsApi } from '@/features/dashboard/api'
import { paymentMethodLabel } from '@/features/payments/methods'
import { useExcelExport } from '@/features/reports/useExcelExport'
import { ApiError } from '@/lib/api/types'
import { formatDate, som } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

/** Oldingi oy — odatda aynan u yopiladi. */
function previousMonth(): string {
  const now = new Date()
  const date = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function Amount({ value, strong = false }: { value: string; strong?: boolean }) {
  return (
    <span
      className={cn('num tabular-nums', strong ? 'font-bold text-slate-900' : 'text-slate-700')}
    >
      {som(value)}
    </span>
  )
}

export function MonthlySummary() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const [period, setPeriod] = useState(previousMonth)
  const [year, month] = period.split('-').map(Number)
  const key = ['org', organizationId, 'reports', 'monthly-summary', period]
  const summary = useQuery({
    queryKey: key,
    queryFn: () => reportsApi.monthlySummary(year, month),
    enabled: Boolean(year && month),
  })
  const excel = useExcelExport('monthly')
  const [error, setError] = useState<string | null>(null)
  const close = useMutation({
    mutationFn: () => reportsApi.closeMonth(year, month),
    onSuccess: () => {
      setError(null)
      void queryClient.invalidateQueries({ queryKey: key })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const data = summary.data

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{t('Oylik yigʻma')}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('Toifalar, imtiyozlar, qayta hisoblar va yigʻilgan pul — oy boʻyicha.')}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label
              htmlFor="summary-month"
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {t('Oy')}
            </label>
            <input
              id="summary-month"
              type="month"
              value={period}
              onChange={(event) => event.target.value && setPeriod(event.target.value)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
          </div>
          {can('reports.export') && (
            <button
              type="button"
              disabled={excel.busy}
              onClick={() => void excel.start({ year, month })}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
            >
              <Download className="h-4 w-4" />
              {excel.busy ? t('Tayyorlanmoqda…') : t('Oylik toʻlov jadvali')}
            </button>
          )}
        </div>
      </div>

      {(error || excel.error) && (
        <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error || excel.error}
        </p>
      )}

      {data && (
        <div className="mt-4 space-y-4">
          {/* Tenglik — birinchi qarashda */}
          <div
            className={cn(
              'flex flex-wrap items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-sm',
              data.check.ok ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800',
            )}
          >
            <span className="flex items-center gap-2 font-medium">
              {data.check.ok ? (
                <CheckCircle2 className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              {data.check.ok
                ? t('Tenglik toʻgʻri: hisoblangan = yigʻilgan + qarz')
                : t('Tenglik buzilgan — raqamlardan biri siljigan')}
            </span>
            {data.closed ? (
              <span className="flex items-center gap-1.5 text-xs">
                <Lock className="h-3.5 w-3.5" />
                {t('Yopilgan: {date}, {name}', {
                  date: formatDate(data.closed.closed_at),
                  name: data.closed.closed_by,
                })}
              </span>
            ) : (
              can('reports.approve') && (
                <button
                  type="button"
                  disabled={close.isPending || !data.check.ok}
                  onClick={() => {
                    if (
                      window.confirm(
                        t(
                          'Oy yopilgach u faqat keyingi oyga tuzatish qatori orqali oʻzgaradi. Yopasizmi?',
                        ),
                      )
                    )
                      close.mutate()
                  }}
                  className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
                >
                  <Lock className="h-3.5 w-3.5" />
                  {t('Oyni yopish')}
                </button>
              )
            )}
          </div>
          {!data.check.ok && <p className="num text-xs text-red-700">{data.check.equation}</p>}

          <div className="grid gap-4 lg:grid-cols-2">
            {/* Toifalar */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {t('Toifalar — {n} bola', { n: data.roster })}
              </h3>
              <div className="mt-1 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500">
                      <th className="py-1.5 font-medium">{t('Toifa')}</th>
                      <th className="py-1.5 text-right font-medium">{t('Bolalar')}</th>
                      <th className="py-1.5 text-right font-medium">{t('Kutilgan')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data.categories.map((row) => (
                      <tr key={row.category}>
                        <td className="py-1.5 text-slate-700">{row.label}</td>
                        <td className="py-1.5 text-right tabular-nums">{row.children}</td>
                        <td className="py-1.5 text-right">
                          <Amount value={row.due} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <dl className="mt-2 space-y-1 border-t border-slate-100 pt-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">{t('Toʻliq narx boʻyicha')}</dt>
                  <dd>
                    <Amount value={data.invoiced.charged} />
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">{t('Imtiyozlar')}</dt>
                  <dd>
                    <Amount value={data.invoiced.benefits} />
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">{t('Qayta hisoblar')}</dt>
                  <dd>
                    <Amount value={data.invoiced.recalculations} />
                  </dd>
                </div>
                <div className="flex justify-between font-medium">
                  <dt className="text-slate-700">{t('Hisoblangan')}</dt>
                  <dd>
                    <Amount value={data.invoiced.amount_due} strong />
                  </dd>
                </div>
              </dl>
              {data.recalculations.length > 0 && (
                <ul className="mt-2 space-y-1 text-xs text-slate-600">
                  {data.recalculations.map((row) => (
                    <li key={row.kind} className="flex justify-between gap-2">
                      <span>
                        {row.label} · {row.count}
                      </span>
                      <Amount value={row.amount} />
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Pul: ikki koʻrinish */}
            <div className="space-y-3">
              <div className="rounded-xl bg-slate-50 p-3">
                <h3 className="flex justify-between text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('Oy uchun yigʻilgan')}
                  <Amount value={data.collected_for_month.total} strong />
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  {t('Shu oy fakturalarini yopgan pul — qachon kelganidan qatʼi nazar.')}
                </p>
                <ul className="mt-2 space-y-1 text-sm">
                  {data.collected_for_month.by_method.map((row) => (
                    <li key={row.method} className="flex justify-between">
                      <span className="text-slate-600">{paymentMethodLabel(row.method)}</span>
                      <Amount value={row.total} />
                    </li>
                  ))}
                </ul>
                <dl className="mt-2 space-y-0.5 border-t border-slate-200 pt-2 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <dt>{t('Oldindan (avans)')}</dt>
                    <dd>
                      <Amount value={data.collected_for_month.before_month} />
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>{t('Shu oyda')}</dt>
                    <dd>
                      <Amount value={data.collected_for_month.in_month} />
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt>{t('Keyingi oylarda')}</dt>
                    <dd>
                      <Amount value={data.collected_for_month.after_month} />
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="rounded-xl bg-slate-50 p-3">
                <h3 className="flex justify-between text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('Kassa tushumi')}
                  <Amount value={data.cash_received.total} strong />
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  {t('Shu oyda kelgan pul — qaysi oy uchunligidan qatʼi nazar.')}
                </p>
                <ul className="mt-2 space-y-1 text-sm">
                  {data.cash_received.by_method.map((row) => (
                    <li key={row.method} className="flex justify-between">
                      <span className="text-slate-600">{paymentMethodLabel(row.method)}</span>
                      <Amount value={row.total} />
                    </li>
                  ))}
                </ul>
                <p className="mt-2 flex justify-between border-t border-slate-200 pt-2 text-xs text-slate-600">
                  <span>{t('Keyingi oylar uchun avans')}</span>
                  <Amount value={data.cash_received.advances_for_later} />
                </p>
              </div>

              <div>
                <h3 className="flex justify-between text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {t('Qolgan qarz')}
                  <Amount value={data.outstanding} strong />
                </h3>
                {data.aging.length > 0 && (
                  <ul className="mt-1 space-y-1 text-xs text-slate-600">
                    {data.aging.map((row) => (
                      <li key={row.period} className="flex justify-between gap-2">
                        <span>
                          {row.period} · {t('{n} bola', { n: row.children })}
                        </span>
                        <Amount value={row.outstanding} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
