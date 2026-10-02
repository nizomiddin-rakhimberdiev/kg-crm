/**
 * Bola kartasining tablari (PLAN 2.1).
 *
 * Auditda kartada faqat guruh, tarif va "vasiy qo'shish" bor edi.
 * Mudiraning savollari esa boshqa: "bu oila qachon to'lagan?",
 * "qancha kun kelmadi?", "kim o'zgartirgan?". Har biriga javob
 * boshqa ekranda yotardi va ularni bir-biriga bog'lash odamning
 * yodida qolardi.
 *
 * Tablar ALOHIDA so'rov qiladi va faqat ochilganda: bola kartasi
 * ochilishi bilan beshta so'rov yuborish ro'yxatni sekinlashtirardi.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { auditApi } from '@/features/dashboard/api'
import { invoicesApi, paymentsApi } from '@/features/payments/api'
import { paymentMethodLabel } from '@/features/payments/methods'
import { EmptyRow } from '@/components/ui/EmptyState'
import { cn, formatDate, formatDateTime } from '@/lib/utils'
import { money } from '@/lib/format'
import { t } from '@/lib/i18n'

type TabKey = 'invoices' | 'payments' | 'history'

const TABS: Array<[TabKey, string]> = [
  ['invoices', t('Hisob-fakturalar')],
  ['payments', t("To'lovlar")],
  ['history', t('Tarix')],
]

export function ChildTabs({ childId }: { childId: string }) {
  const organizationId = useOrganizationId()
  const [tab, setTab] = useState<TabKey>('invoices')

  const invoices = useQuery({
    queryKey: ['org', organizationId, 'invoices', { child: childId }],
    queryFn: () => invoicesApi.list({ child: childId, page_size: 100 }),
    enabled: tab === 'invoices',
  })

  const payments = useQuery({
    queryKey: ['org', organizationId, 'payments', { child: childId }],
    queryFn: () => paymentsApi.list({ child: childId, page_size: 100 }),
    enabled: tab === 'payments',
  })

  const history = useQuery({
    queryKey: ['org', organizationId, 'audit', { entity: childId }],
    queryFn: () => auditApi.list({ entity_type: 'child', entity_id: childId, page_size: 50 }),
    enabled: tab === 'history',
  })

  return (
    <div className="rounded-2xl border border-slate-200 bg-white">
      <div className="flex gap-1 border-b border-slate-200 px-2 pt-2">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              'rounded-t-lg px-3 py-2 text-sm font-medium transition',
              tab === key
                ? 'bg-white text-brand-700 shadow-[inset_0_-2px_0_0_theme(colors.brand.600)]'
                : 'text-slate-500 hover:text-slate-800',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          {tab === 'invoices' && (
            <>
              <thead className="bg-slate-50/70 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5 font-medium">{t('Davr')}</th>
                  <th className="px-4 py-2.5 font-medium">{t('Raqam')}</th>
                  <th className="px-4 py-2.5 font-medium">{t('Muddat')}</th>
                  <th className="px-4 py-2.5 text-right font-medium">{t('Hisoblangan')}</th>
                  <th className="px-4 py-2.5 text-right font-medium">{t("To'langan")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.data?.items.map((invoice) => (
                  <tr key={invoice.id}>
                    <td className="px-4 py-2.5 text-slate-700">
                      {invoice.period_year}-{String(invoice.period_month).padStart(2, '0')}
                    </td>
                    <td className="num px-4 py-2.5 text-xs text-slate-500">{invoice.number}</td>
                    <td className="num px-4 py-2.5 text-slate-600">
                      {formatDate(invoice.due_date)}
                    </td>
                    <td className="num px-4 py-2.5 text-right text-slate-800">
                      {money(invoice.amount_due)}
                    </td>
                    <td className="num px-4 py-2.5 text-right font-medium text-nihol-700">
                      {money(invoice.amount_paid)}
                    </td>
                  </tr>
                ))}
                {invoices.data?.items.length === 0 && (
                  <EmptyRow colSpan={5} title={t('Hisob-faktura yoʻq')} />
                )}
              </tbody>
            </>
          )}

          {tab === 'payments' && (
            <>
              <thead className="bg-slate-50/70 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5 font-medium">{t('Sana')}</th>
                  <th className="px-4 py-2.5 font-medium">{t("To'lov usuli")}</th>
                  <th className="px-4 py-2.5 text-right font-medium">{t('Summa')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {payments.data?.items.map((payment) => (
                  <tr key={payment.id}>
                    <td className="num px-4 py-2.5 text-slate-600">
                      {formatDateTime(payment.paid_at)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-700">
                      {paymentMethodLabel(payment.method)}
                      {payment.is_reversed && (
                        <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
                          {t('Qaytarilgan')}
                        </span>
                      )}
                    </td>
                    <td
                      className={cn(
                        'num px-4 py-2.5 text-right font-medium',
                        payment.is_reversed ? 'text-slate-400 line-through' : 'text-nihol-700',
                      )}
                    >
                      {money(payment.amount)}
                    </td>
                  </tr>
                ))}
                {payments.data?.items.length === 0 && (
                  <EmptyRow colSpan={3} title={t("To'lov yoʻq")} />
                )}
              </tbody>
            </>
          )}

          {tab === 'history' && (
            <>
              <thead className="bg-slate-50/70 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5 font-medium">{t('Sana')}</th>
                  <th className="px-4 py-2.5 font-medium">{t('Kim')}</th>
                  <th className="px-4 py-2.5 font-medium">{t('Nima')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {history.data?.items.map((row) => (
                  <tr key={row.id}>
                    <td className="num px-4 py-2.5 text-slate-600">
                      {formatDateTime(row.created_at)}
                    </td>
                    <td className="px-4 py-2.5 text-slate-700">{row.actor_name || '—'}</td>
                    <td className="px-4 py-2.5 text-slate-600">{row.action}</td>
                  </tr>
                ))}
                {history.data?.items.length === 0 && (
                  <EmptyRow colSpan={3} title={t('Tarix boʻsh')} />
                )}
              </tbody>
            </>
          )}
        </table>
      </div>
    </div>
  )
}
