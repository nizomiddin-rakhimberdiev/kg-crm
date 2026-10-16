/**
 * Tarmoq koʻrinishi — filiallar yonma-yon (Bosqich 13.6, brif §5.4).
 *
 * Har filial raqami oʻsha oylik hisobot paketidan. Eng yaxshi qiymat yashil,
 * eng yomoni qizil — rang yolgʻiz emas, yonida belgi ham bor. Konsolidatsiyada
 * filiallar orasidagi oʻtkazmalar chiqarib tashlanadi.
 */

import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { QueryError } from '@/components/ui/QueryError'
import { reportsApi, type NetworkRow } from '@/features/dashboard/api'
import { som } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

const COLUMNS: Array<{ key: keyof NetworkRow; label: string; kind: 'pct' | 'money' | 'count' }> = [
  { key: 'occupancy', label: t('Bandlik'), kind: 'pct' },
  { key: 'average_per_child', label: t('Bir boladan'), kind: 'money' },
  { key: 'collection_rate', label: t('Yigʻish'), kind: 'pct' },
  { key: 'payroll_share', label: t('Ish haqi ulushi'), kind: 'pct' },
  { key: 'margin', label: t('Marja'), kind: 'pct' },
  { key: 'food_per_child_day', label: t('Oziq-ovqat, bola-kun'), kind: 'money' },
  { key: 'attention', label: t('Diqqat'), kind: 'count' },
]

function value(row: NetworkRow, key: keyof NetworkRow, kind: string): string {
  const raw = row[key]
  if (raw === null || raw === undefined) return '—'
  if (kind === 'pct') return `${raw}%`
  if (kind === 'money') return som(String(raw))
  return String(raw)
}

export function NetworkTable({ year, month }: { year: number; month: number }) {
  const organizationId = useOrganizationId()
  const network = useQuery({
    queryKey: ['org', organizationId, 'reports', 'network', year, month],
    queryFn: () => reportsApi.network(year, month),
  })
  if (network.isError) {
    return <QueryError error={network.error} onRetry={() => void network.refetch()} />
  }
  const data = network.data
  if (!data) return null
  return (
    <section className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-slate-900">{t('Filiallar yonma-yon')}</h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="px-2 py-1 font-medium">{t('Filial')}</th>
              <th className="px-2 py-1 text-right font-medium">{t('Bolalar')}</th>
              {COLUMNS.map((column) => (
                <th key={column.key} className="px-2 py-1 text-right font-medium">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.rows.map((row) => (
              <tr key={row.branch_id}>
                <td className="px-2 py-1.5 font-medium text-slate-900">{row.branch}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{row.children}</td>
                {COLUMNS.map((column) => {
                  const best = data.best[column.key] === row.branch_id
                  const worst = data.worst[column.key] === row.branch_id
                  return (
                    <td
                      key={column.key}
                      className={cn(
                        'px-2 py-1.5 text-right tabular-nums',
                        best && 'font-semibold text-emerald-700',
                        worst && 'font-semibold text-red-700',
                      )}
                    >
                      {best && <span aria-label={t('eng yaxshi')}>▲ </span>}
                      {worst && <span aria-label={t('eng yomon')}>▼ </span>}
                      {value(row, column.key, column.kind)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        {t('Konsolidatsiyada chiqarib tashlangan filiallararo oʻtkazmalar: {money}', {
          money: som(data.eliminated_transfers),
        })}
      </p>
    </section>
  )
}
