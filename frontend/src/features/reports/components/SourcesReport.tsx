/**
 * "Bizni qayerdan eshitishgan?" (Bosqich 14).
 *
 * Davrda qoʻshilgan bolalar — oila bogʻcha haqida qayerdan eshitgani
 * boʻyicha: soni, ulushi va hozir ham bogʻchadami. Javob berilmaganlar
 * alohida qator — taxmin qilinmaydi, shuning uchun qatorlar jamiga teng.
 */

import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { reportsApi } from '@/features/dashboard/api'
import { number } from '@/lib/format'
import { t } from '@/lib/i18n'

export function SourcesReport({ from, to }: { from: string; to: string }) {
  const organizationId = useOrganizationId()
  const report = useQuery({
    queryKey: ['org', organizationId, 'reports', 'sources', from, to],
    queryFn: () => reportsApi.sources(from, to),
  })
  const data = report.data
  if (!data) return null
  const top = Math.max(1, ...data.rows.map((row) => row.count), data.unanswered)

  return (
    <section
      aria-labelledby="sources-title"
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 sm:p-5"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 id="sources-title" className="text-sm font-semibold text-slate-900">
            {t('Bizni qayerdan eshitishgan?')}
          </h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('Davrda qoʻshilgan bolalar — oila bogʻcha haqida qayerdan bilgani boʻyicha.')}
          </p>
        </div>
        <p className="num text-lg font-bold text-slate-900">
          {t('{n} bola', { n: number(data.total) })}
        </p>
      </div>

      {data.total === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{t('Bu davrda yangi bola qoʻshilmagan.')}</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[26rem] text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500">
                <th className="px-2 py-1 font-medium">{t('Manba')}</th>
                <th className="w-2/5 px-2 py-1 font-medium" aria-hidden />
                <th className="px-2 py-1 text-right font-medium">{t('Bolalar')}</th>
                <th className="px-2 py-1 text-right font-medium">{t('Ulush')}</th>
                <th className="px-2 py-1 text-right font-medium">{t('Hozir ham bogʻchada')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.rows.map((row) => (
                <tr key={row.source}>
                  <td className="px-2 py-1.5 text-slate-800">{row.label}</td>
                  <td className="px-2 py-1.5" aria-hidden>
                    <div className="h-2 rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full bg-brand-500"
                        style={{ width: `${(row.count / top) * 100}%` }}
                      />
                    </div>
                  </td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{number(row.count)}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{row.share}%</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{number(row.active)}</td>
                </tr>
              ))}
              {data.unanswered > 0 && (
                <tr className="text-slate-500">
                  <td className="px-2 py-1.5">{t('Koʻrsatilmagan')}</td>
                  <td className="px-2 py-1.5" aria-hidden>
                    <div className="h-2 rounded-full bg-slate-100">
                      <div
                        className="h-2 rounded-full bg-slate-300"
                        style={{ width: `${(data.unanswered / top) * 100}%` }}
                      />
                    </div>
                  </td>
                  <td className="px-2 py-1.5 text-right tabular-nums">{number(data.unanswered)}</td>
                  <td className="px-2 py-1.5 text-right tabular-nums">
                    {((data.unanswered * 100) / data.total).toFixed(1)}%
                  </td>
                  <td className="px-2 py-1.5" />
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
