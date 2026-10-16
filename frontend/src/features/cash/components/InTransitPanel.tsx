/**
 * Yoʻldagi pul (Bosqich 13.2c): terminal, Click va Payme puli bankka
 * tushguncha. Kutilgan summa = toʻlov − komissiya. Kechikkani birinchi.
 * Bank koʻchirmasi importi (13.3) ularni oʻzi yopadi; hozircha — qoʻlda.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Truck } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { cashApi } from '@/features/cash/api'
import { paymentMethodLabel } from '@/features/payments/methods'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { formatDate, som, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

export function InTransitPanel({ canSettle }: { canSettle: boolean }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const transit = useQuery({
    queryKey: ['org', organizationId, 'cash', 'in-transit'],
    queryFn: cashApi.inTransit,
  })
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const settle = useMutation({
    mutationFn: () => cashApi.settle({ payment_ids: [...picked], settled_on: today() }),
    onSuccess: () => {
      setPicked(new Set())
      setError(null)
      invalidateMoney(queryClient, organizationId)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const data = transit.data
  if (!data || data.items.length === 0) return null
  const rows = [...data.items].sort((a, b) => Number(b.overdue) - Number(a.overdue))
  const toggle = (id: string) =>
    setPicked((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <Truck className="h-4 w-4 text-slate-500" />
          {t('Yoʻldagi pul — bankka tushishi kutilmoqda')}
        </h2>
        <span className="text-sm font-semibold tabular-nums text-slate-900">
          {som(data.expected_total)}
        </span>
      </div>
      {data.overdue_count > 0 && (
        <p className="mt-2 flex items-center gap-1.5 text-xs font-medium text-red-700">
          <AlertTriangle className="h-3.5 w-3.5" />
          {t('{n} ta toʻlov oʻz vaqtida tushmagan — bank koʻchirmasini tekshiring.', {
            n: data.overdue_count,
          })}
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <ul className="mt-2 divide-y divide-slate-100 text-sm">
        {rows.map((row) => (
          <li key={row.payment_id} className="flex items-center gap-3 py-2">
            {canSettle && (
              <input
                type="checkbox"
                aria-label={t('Bankka tushdi: {name}', { name: row.child })}
                checked={picked.has(row.payment_id)}
                onChange={() => toggle(row.payment_id)}
              />
            )}
            <span className="min-w-0 flex-1">
              <span className="block truncate text-slate-700">
                {row.child} · {paymentMethodLabel(row.method)}
              </span>
              <span className={cn('text-xs', row.overdue ? 'text-red-700' : 'text-slate-500')}>
                {t('Toʻlandi {paid}, kutilgan {expected}', {
                  paid: formatDate(row.paid_on),
                  expected: formatDate(row.expected_on),
                })}
              </span>
            </span>
            <span className="text-right">
              <span className="block font-semibold tabular-nums text-slate-900">
                {som(row.expected_amount)}
              </span>
              {Number(row.commission) > 0 && (
                <span className="text-xs text-slate-500">
                  {t('komissiya {money}', { money: som(row.commission) })}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
      {canSettle && picked.size > 0 && (
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            disabled={settle.isPending}
            onClick={() => settle.mutate()}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {t('{n} ta toʻlov bankka tushdi', { n: picked.size })}
          </button>
        </div>
      )}
    </section>
  )
}
