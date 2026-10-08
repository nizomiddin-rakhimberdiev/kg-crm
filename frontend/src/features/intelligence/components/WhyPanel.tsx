/**
 * "Nega?" paneli (docs/07 §6).
 *
 * Raqamlar — snapshot'dan (signal chiqqan paytdagi holat). Ismlar —
 * JONLI, id bo'yicha bitta so'rov (`GET /children?ids=`): evidence'da ism
 * saqlanmaydi. O'chirilgan bola "o'chirilgan bola" bo'lib chiqadi,
 * raqamlari esa joyida.
 */

import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { childrenApi } from '@/features/children/api'
import { fill, getCopy } from '@/features/intelligence/content'
import { paymentDelayReason } from '@/features/intelligence/severity'
import { queryKeys } from '@/lib/api/queryKeys'
import type { Insight, PaymentDelayEvidence } from '@/lib/api/types'
import { formatUZS } from '@/lib/utils'

interface WhyPanelProps {
  insight: Insight
  evidence: PaymentDelayEvidence
  onClose: () => void
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-2.5">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-0.5 text-base font-bold tabular-nums text-slate-900">{value}</p>
    </div>
  )
}

export function WhyPanel({ insight, evidence, onClose }: WhyPanelProps) {
  const copy = getCopy()
  const organizationId = useOrganizationId()
  const ids = evidence.children.map((row) => row.child_id)

  const labels = useQuery({
    queryKey: queryKeys.childLabels(organizationId, ids),
    queryFn: () => childrenApi.list({ ids: ids.join(','), page_size: 100 }),
    enabled: ids.length > 0,
    staleTime: 60_000,
    select: (result) =>
      new Map(
        result.items.map((child) => [
          child.id,
          { name: child.full_name, group: child.current_group?.name ?? null },
        ]),
      ),
  })

  const reason = paymentDelayReason(evidence, insight.severity)
  const values: Record<string, unknown> = {
    ...evidence,
    severity: copy.severity[insight.severity].toLowerCase(),
    shown: evidence.children.length,
  }

  return (
    <Modal open onClose={onClose} className="max-w-2xl">
      <div className="p-5 sm:p-6">
        <div className="pr-10">
          <p className="text-xs font-semibold uppercase tracking-wider text-brand-600">
            {copy.brand}
          </p>
          <h2 className="mt-1 text-lg font-bold text-slate-900">{copy.why.title}</h2>
        </div>

        <section className="mt-5">
          <h3 className="text-sm font-semibold text-slate-900">{copy.why.rule}</h3>
          <p className="mt-1 text-sm leading-relaxed text-slate-600">
            {fill(copy.why.ruleBody, values)}
          </p>
        </section>

        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Fact
            label={copy.facts.children}
            value={`${evidence.children_count} / ${evidence.active_children}`}
          />
          <Fact label={copy.facts.totalOverdue} value={formatUZS(Number(evidence.total_overdue))} />
          <Fact
            label={copy.facts.maxDays}
            value={`${evidence.max_days_overdue} ${copy.facts.dayUnit}`}
          />
          <Fact
            label={copy.facts.avgDays}
            value={`${evidence.average_days_overdue} ${copy.facts.dayUnit}`}
          />
        </div>

        <section className="mt-4">
          <h3 className="text-sm font-semibold text-slate-900">
            {fill(copy.why.severityTitle, values)}
          </h3>
          <ul className="mt-1 space-y-1 text-sm text-slate-600">
            {(reason === 'days' || reason === 'both') && (
              <li>{fill(copy.why.criticalByDays, values)}</li>
            )}
            {(reason === 'count' || reason === 'both') && (
              <li>{fill(copy.why.criticalByCount, values)}</li>
            )}
            {reason === 'none' && <li>{fill(copy.why.warningReason, values)}</li>}
          </ul>
        </section>

        <section className="mt-5">
          <div className="overflow-x-auto rounded-xl border border-slate-200">
            <table className="w-full min-w-[520px] text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2 font-medium">{copy.why.childCol}</th>
                  <th className="px-3 py-2 font-medium">{copy.why.groupCol}</th>
                  <th className="px-3 py-2 text-right font-medium">{copy.why.daysCol}</th>
                  <th className="px-3 py-2 text-right font-medium">{copy.why.invoicesCol}</th>
                  <th className="px-3 py-2 text-right font-medium">{copy.why.amountCol}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {evidence.children.map((row) => {
                  const label = labels.data?.get(row.child_id)
                  return (
                    <tr key={row.child_id}>
                      <td className="px-3 py-2 font-medium text-slate-800">
                        {labels.isPending ? (
                          <span className="text-slate-300">…</span>
                        ) : (
                          (label?.name ?? (
                            <span className="italic text-slate-500">{copy.why.deletedChild}</span>
                          ))
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        {label?.group ?? <span className="text-slate-500">{copy.why.noGroup}</span>}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-800">
                        {row.days_overdue} {copy.facts.dayUnit}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-600">
                        {row.invoices}
                      </td>
                      <td className="px-3 py-2 text-right font-medium tabular-nums text-red-700">
                        {formatUZS(Number(row.overdue_amount))}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {evidence.children_count > evidence.children.length && (
            <p className="mt-2 text-xs text-slate-500">{fill(copy.why.capped, values)}</p>
          )}
        </section>

        <section className="mt-5 rounded-xl border border-amber-100 bg-amber-50 px-3 py-2.5">
          <p className="text-xs font-semibold text-amber-800">
            {fill(copy.why.snapshotTitle, values)}
          </p>
          <p className="mt-0.5 text-xs leading-relaxed text-amber-800/90">
            {copy.why.snapshotBody}
          </p>
        </section>
      </div>
    </Modal>
  )
}
