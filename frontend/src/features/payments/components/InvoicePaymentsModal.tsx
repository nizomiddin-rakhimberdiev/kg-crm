/**
 * Bitta hisob-faktura bo'yicha to'lovlar taqsimoti.
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
import { paymentMethodLabel } from '@/features/payments/methods'
import { queryKeys } from '@/lib/api/queryKeys'
import type { Invoice } from '@/lib/api/types'
import { cn, formatDate } from '@/lib/utils'
import { Modal } from '@/components/ui/Modal'
import { t } from '@/lib/i18n'

const money = (value: number) => new Intl.NumberFormat('uz-UZ').format(value) + t(" so'm")

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

  return (
    <Modal open={Boolean(invoice)} onClose={onClose} className="max-w-lg">
      <h2 className="text-lg font-semibold text-slate-900">{t("To'lovlar tafsiloti")}</h2>
      <p className="mt-1 text-sm text-slate-500">
        {invoice?.child_name} · {invoice?.number}
      </p>

      <dl className="mt-4 grid grid-cols-3 gap-3 rounded-xl bg-slate-50 p-3 text-center">
        <div>
          <dt className="text-xs text-slate-500">{t('Hisoblangan')}</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-slate-900">
            {money(Number(invoice?.amount_due ?? 0))}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">{t("To'langan")}</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-emerald-700">
            {money(paid)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">{t('Qoldiq')}</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-slate-900">
            {money(Number(invoice?.amount_outstanding ?? 0))}
          </dd>
        </div>
      </dl>

      {breakdown.length > 0 && (
        <>
          <h3 className="mt-5 text-sm font-semibold text-slate-900">{t("Usul bo'yicha")}</h3>
          <ul className="mt-2 space-y-2">
            {breakdown.map(([method, row]) => (
              <li
                key={method}
                className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2"
              >
                <span className="text-sm text-slate-700">
                  {paymentMethodLabel(method)}
                  {row.count > 1 && (
                    <span className="ml-2 text-xs text-slate-400">
                      {t('{v} ta', { v: row.count })}
                    </span>
                  )}
                </span>
                <span className="text-sm font-semibold tabular-nums text-slate-900">
                  {money(row.total)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      <h3 className="mt-5 text-sm font-semibold text-slate-900">{t("Har bir to'lov")}</h3>
      <ul className="mt-2 divide-y divide-slate-100">
        {payments.map((payment) => (
          <li key={payment.id} className="flex items-center justify-between gap-3 py-2">
            <div className="min-w-0">
              <p className="text-sm text-slate-700">
                {paymentMethodLabel(payment.method)}
                {payment.reference && (
                  <span className="ml-2 text-xs text-slate-400">{payment.reference}</span>
                )}
              </p>
              <p className="text-xs text-slate-400">
                {formatDate(payment.paid_at)}
                {payment.is_reversed && ` · ${t('qaytarilgan')}`}
              </p>
            </div>
            <span
              className={cn(
                'shrink-0 text-sm font-semibold tabular-nums',
                payment.is_reversed ? 'text-slate-400 line-through' : 'text-emerald-700',
              )}
            >
              {money(Number(payment.amount))}
            </span>
          </li>
        ))}
        {!isPending && payments.length === 0 && (
          <li className="py-6 text-center text-sm text-slate-400">
            {t("Bu hisob-faktura bo'yicha to'lov yo'q.")}
          </li>
        )}
        {isPending && (
          <li className="py-6 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</li>
        )}
      </ul>
    </Modal>
  )
}
