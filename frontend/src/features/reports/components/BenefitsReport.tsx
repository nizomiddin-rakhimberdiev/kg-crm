/**
 * Imtiyozlar hisoboti (Bosqich 12.2, brif §1).
 *
 * Kim, qaysi bolaga, qancha va qaysi sabab bilan imtiyoz bergani — davr
 * boʻyicha jami bilan. Raqamlar hisob-fakturalarning imtiyoz qatorlaridan:
 * HAQIQATAN berilgan summa. Excel'da yigʻma qoʻlda sanalardi va xato
 * chiqardi; bu yerda sanash yoʻq.
 */

import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { reportsApi } from '@/features/dashboard/api'
import { som } from '@/lib/format'
import { t } from '@/lib/i18n'

export function BenefitsReport({ from, to }: { from: string; to: string }) {
  const organizationId = useOrganizationId()
  const report = useQuery({
    queryKey: ['org', organizationId, 'reports', 'benefits', from, to],
    queryFn: () => reportsApi.benefits(from, to),
  })
  const data = report.data
  if (!data) return null

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-4 sm:px-5">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{t('Imtiyozlar')}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('Hisob-fakturalarda haqiqatan berilgan chegirma — kim kiritgani va sababi bilan.')}
          </p>
        </div>
        <p className="num text-lg font-bold text-slate-900">{som(data.total)}</p>
      </div>

      {data.by_kind.length > 0 && (
        <ul className="flex flex-wrap gap-2 px-4 pt-3 sm:px-5">
          {data.by_kind.map((row) => (
            <li
              key={row.kind}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700"
            >
              {row.label}: <b className="num">{som(row.total)}</b>
            </li>
          ))}
        </ul>
      )}

      {data.rows.length === 0 ? (
        <p className="px-5 py-8 text-center text-sm text-slate-500">
          {t('Bu davrda imtiyoz berilmagan.')}
        </p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2.5 font-medium">{t('Bola')}</th>
                <th className="px-4 py-2.5 font-medium">{t('Turi')}</th>
                <th className="px-4 py-2.5 font-medium">{t('Sabab')}</th>
                <th className="px-4 py-2.5 font-medium">{t('Kim kiritgan')}</th>
                <th className="px-4 py-2.5 text-right font-medium">{t('Summa')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.rows.map((row) => (
                <tr key={`${row.child_id}-${row.kind}-${row.reason}`}>
                  <td className="px-4 py-2 text-slate-900">{row.child_name}</td>
                  <td className="px-4 py-2 text-slate-700">{row.kind_label}</td>
                  <td className="px-4 py-2 text-slate-600">{row.reason || '—'}</td>
                  <td className="px-4 py-2 text-slate-600">
                    {row.created_by ?? t('Avtomatik (oila)')}
                  </td>
                  <td className="num px-4 py-2 text-right font-medium text-slate-900">
                    {som(row.total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
