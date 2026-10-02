/**
 * Bitta hisob-faktura bo'yicha to'lovlar tafsiloti.
 *
 * Nega kerak bo'ldi: bir bolaga 1 400 000 naqd va 100 000 karta bilan
 * to'langanda jadvalda faqat "1 500 000 — to'langan" ko'rinardi. Pul
 * qaysi usuldan kelgani yo'qolmagan edi (har bir to'lov alohida qator),
 * lekin uni faqat to'lovlar jurnalidan qidirib topish mumkin edi.
 * Endi summani yoki ismni bosish yetarli.
 */

import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { paymentsApi } from '@/features/payments/api'
import {
  paymentMethodColor,
  paymentMethodIcon,
  paymentMethodLabel,
} from '@/features/payments/methods'
import { queryKeys } from '@/lib/api/queryKeys'
import type { Invoice } from '@/lib/api/types'
import { cn, formatDate } from '@/lib/utils'
import { Modal } from '@/components/ui/Modal'
import { som } from '@/lib/format'
import { t } from '@/lib/i18n'

const money = som

/** Rangli nishon — diagramma va jurnal bir xil rang tilida gapirsin. */
function MethodMark({ method }: { method: string }) {
  const Icon = paymentMethodIcon(method)
  const color = paymentMethodColor(method)
  return (
    <span
      className="grid h-9 w-9 shrink-0 place-items-center rounded-xl"
      style={{ backgroundColor: `${color}1a`, color }}
    >
      <Icon className="h-4 w-4" />
    </span>
  )
}

export function InvoicePaymentsModal({
  invoice,
  onClose,
}: {
  invoice: Invoice | null
  onClose: () => void
}) {
  const organizationId = useOrganizationId()

  const { data, isPending } = useQuery({
    queryKey: queryKeys.payments(organizationId, { invoice: invoice?.id }),
    queryFn: () => paymentsApi.list({ invoice: invoice!.id, page_size: 100 }),
    enabled: Boolean(invoice),
  })

  const payments = data?.items ?? []
  // Qaytarilgan to'lov taqsimotga KIRMAYDI: u qaytarib berilgan pul.
  // Ro'yxatda esa qoladi — nima bo'lganini yashirish tarixni buzardi.
  const live = payments.filter((payment) => !payment.is_reversed)

  const byMethod = new Map<string, { total: number; count: number }>()
  for (const payment of live) {
    const row = byMethod.get(payment.method) ?? { total: 0, count: 0 }
    row.total += Number(payment.amount)
    row.count += 1
    byMethod.set(payment.method, row)
  }
  const breakdown = [...byMethod.entries()].sort((a, b) => b[1].total - a[1].total)

  const paid = live.reduce((sum, payment) => sum + Number(payment.amount), 0)
  const due = Number(invoice?.amount_due ?? 0)
  const outstanding = Number(invoice?.amount_outstanding ?? 0)
  const pct = due > 0 ? Math.min(100, Math.round((paid / due) * 100)) : paid > 0 ? 100 : 0

  return (
    <Modal open={Boolean(invoice)} onClose={onClose} className="max-w-lg">
      <div className="p-6">
        {/* `pr-10` — sarlavha yopish tugmasining ostiga kirib ketmasin. */}
        <div className="pr-10">
          <h2 className="text-lg font-bold text-slate-900">{t('Toʻlovlar tafsiloti')}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {invoice?.child_name}
            <span className="text-slate-300"> · </span>
            <span className="font-mono text-xs">{invoice?.number}</span>
          </p>
        </div>

        {/* Holat: qancha to'langan, qanchadan va qancha qolgan. */}
        <div className="mt-5 rounded-xl border border-slate-200 p-4">
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {t('Toʻlangan')}
              </p>
              <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900">{money(paid)}</p>
            </div>
            <p
              className={cn(
                'text-sm font-semibold tabular-nums',
                outstanding > 0 ? 'text-amber-600' : 'text-emerald-600',
              )}
            >
              {pct}%
            </p>
          </div>

          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className={cn(
                'h-full rounded-full',
                outstanding > 0 ? 'bg-amber-400' : 'bg-emerald-500',
              )}
              style={{ width: `${pct}%` }}
            />
          </div>

          <dl className="mt-3 flex items-baseline justify-between gap-3 text-xs">
            <div className="flex gap-1.5">
              <dt className="text-slate-500">{t('Hisoblangan')}</dt>
              <dd className="font-semibold tabular-nums text-slate-700">{money(due)}</dd>
            </div>
            <div className="flex gap-1.5">
              <dt className="text-slate-500">{t('Qoldiq')}</dt>
              <dd
                className={cn(
                  'font-semibold tabular-nums',
                  outstanding > 0 ? 'text-amber-700' : 'text-slate-700',
                )}
              >
                {money(outstanding)}
              </dd>
            </div>
          </dl>
        </div>

        {/* Usul kesimi FAQAT bir nechta to'lov bo'lganda.
            Bitta to'lovda u quyidagi ro'yxatning aynan nusxasi bo'lardi —
            bir xil qatorni ikki marta ko'rsatish odamni chalg'itadi. */}
        {live.length > 1 && (
          <>
            <h3 className="mt-6 text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('Usul boʻyicha')}
            </h3>
            <ul className="mt-2 space-y-2">
              {breakdown.map(([method, row]) => (
                <li
                  key={method}
                  className="flex items-center gap-3 rounded-xl border border-slate-200 px-3 py-2.5"
                >
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: paymentMethodColor(method) }}
                  />
                  <span className="min-w-0 flex-1 text-sm font-medium text-slate-700">
                    {paymentMethodLabel(method)}
                  </span>
                  {row.count > 1 && (
                    <span className="shrink-0 text-xs tabular-nums text-slate-400">
                      {t('{v} ta', { v: row.count })}
                    </span>
                  )}
                  <span className="shrink-0 text-sm font-semibold tabular-nums text-slate-900">
                    {money(row.total)}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        <h3 className="mt-6 text-xs font-medium uppercase tracking-wide text-slate-500">
          {t('Toʻlovlar')}
        </h3>
        <ul className="mt-1 divide-y divide-slate-100">
          {payments.map((payment) => (
            <li key={payment.id} className="flex items-center gap-3 py-3">
              <MethodMark method={payment.method} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-800">
                  {paymentMethodLabel(payment.method)}
                </p>
                <p className="truncate text-xs text-slate-400">
                  {formatDate(payment.paid_at)}
                  {payment.reference && ` · ${payment.reference}`}
                  {payment.is_reversed && ` · ${t('qaytarilgan')}`}
                </p>
              </div>
              <span
                className={cn(
                  'shrink-0 text-sm font-semibold tabular-nums',
                  payment.is_reversed ? 'text-slate-400 line-through' : 'text-slate-900',
                )}
              >
                {money(Number(payment.amount))}
              </span>
            </li>
          ))}
          {!isPending && payments.length === 0 && (
            <li className="py-8 text-center text-sm text-slate-400">
              {t('Bu hisob-faktura boʻyicha toʻlov yoʻq.')}
            </li>
          )}
          {isPending && (
            <li className="py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</li>
          )}
        </ul>
      </div>
    </Modal>
  )
}
