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

import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { auditApi } from '@/features/dashboard/api'
import { invoicesApi, paymentsApi } from '@/features/payments/api'
import { paymentMethodLabel } from '@/features/payments/methods'
import { EmptyRow } from '@/components/ui/EmptyState'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError, type Invoice } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate, formatDateTime } from '@/lib/utils'
import { money, monthLabel } from '@/lib/format'
import { t } from '@/lib/i18n'

type TabKey = 'invoices' | 'payments' | 'history'

const TABS: Array<[TabKey, string]> = [
  ['invoices', t('Hisob-fakturalar')],
  ['payments', t('Toʻlovlar')],
  ['history', t('Tarix')],
]

export function ChildTabs({ childId }: { childId: string }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const [tab, setTab] = useState<TabKey>('invoices')
  // "Nega?" — ochilgan faktura qatorlari formulasi bilan (Bosqich 12.3).
  const [explained, setExplained] = useState<string | null>(null)
  // Hisobdan chiqarish oynasi — ochiq fakturada.
  const [writing, setWriting] = useState<{
    invoice: Invoice
    amount: string
    reason: string
  } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const writeOff = useMutation({
    mutationFn: (draft: { invoice: Invoice; amount: string; reason: string }) =>
      invoicesApi.writeOff(draft.invoice.id, draft.amount, draft.reason),
    onSuccess: () => {
      setWriting(null)
      setError(null)
      invalidateMoney(queryClient, organizationId)
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'invoices'] })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

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
                  <th className="px-4 py-2.5 text-right font-medium">{t('Toʻlangan')}</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.data?.items.map((invoice) => (
                  <Fragment key={invoice.id}>
                    <tr>
                      <td className="px-4 py-2.5 text-slate-700">
                        {monthLabel(invoice.period_year, invoice.period_month)}
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
                      <td className="whitespace-nowrap px-4 py-2.5 text-right">
                        <button
                          type="button"
                          aria-expanded={explained === invoice.id}
                          onClick={() => setExplained(explained === invoice.id ? null : invoice.id)}
                          className="rounded-lg px-2 py-1 text-xs font-medium text-brand-700 hover:bg-brand-50"
                        >
                          {t('Nega?')}
                        </button>
                        {can('debtors.approve') &&
                          ['issued', 'partially_paid', 'overdue'].includes(invoice.status) && (
                            <button
                              type="button"
                              onClick={() =>
                                setWriting({
                                  invoice,
                                  amount: String(
                                    Number(invoice.amount_due) - Number(invoice.amount_paid),
                                  ),
                                  reason: '',
                                })
                              }
                              className="ml-1 rounded-lg px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                            >
                              {t('Hisobdan chiqarish')}
                            </button>
                          )}
                      </td>
                    </tr>
                    {/* Har bir qator — summasi va FORMULASI bilan: raqam sababsiz turmaydi. */}
                    {explained === invoice.id && (
                      <tr className="bg-slate-50/60">
                        <td colSpan={6} className="px-4 py-3">
                          <ul className="space-y-1.5">
                            {invoice.lines.map((line) => (
                              <li
                                key={line.id}
                                className="flex flex-wrap items-baseline justify-between gap-2"
                              >
                                <span className="text-slate-700">
                                  {line.description}
                                  {line.formula && (
                                    <span className="num block text-xs text-slate-500">
                                      {line.formula}
                                    </span>
                                  )}
                                </span>
                                <span
                                  className={cn(
                                    'num font-medium',
                                    Number(line.line_total) < 0
                                      ? 'text-nihol-700'
                                      : 'text-slate-900',
                                  )}
                                >
                                  {money(line.line_total)}
                                </span>
                              </li>
                            ))}
                            <li className="flex justify-between border-t border-slate-200 pt-1.5 font-semibold text-slate-900">
                              <span>{t('Jami')}</span>
                              <span className="num">{money(invoice.amount_due)}</span>
                            </li>
                          </ul>
                        </td>
                      </tr>
                    )}
                    {writing?.invoice.id === invoice.id && (
                      <tr className="bg-orik-50/40">
                        <td colSpan={6} className="px-4 py-3">
                          <form
                            onSubmit={(event) => {
                              event.preventDefault()
                              writeOff.mutate(writing)
                            }}
                            className="grid gap-2 sm:grid-cols-[160px_1fr_auto]"
                          >
                            <div>
                              <label
                                htmlFor="wo-amount"
                                className="mb-1 block text-xs font-medium text-slate-600"
                              >
                                {t('Summa')}
                              </label>
                              <input
                                id="wo-amount"
                                required
                                inputMode="numeric"
                                value={writing.amount}
                                onChange={(e) =>
                                  setWriting((p) => (p ? { ...p, amount: e.target.value } : p))
                                }
                                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                              />
                            </div>
                            <div>
                              <label
                                htmlFor="wo-reason"
                                className="mb-1 block text-xs font-medium text-slate-600"
                              >
                                {t('Sabab (majburiy)')}
                              </label>
                              <input
                                id="wo-reason"
                                required
                                maxLength={255}
                                value={writing.reason}
                                onChange={(e) =>
                                  setWriting((p) => (p ? { ...p, reason: e.target.value } : p))
                                }
                                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                              />
                            </div>
                            <div className="flex items-end gap-2">
                              <button
                                type="button"
                                onClick={() => setWriting(null)}
                                className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
                              >
                                {t('Bekor qilish')}
                              </button>
                              <button
                                type="submit"
                                disabled={writeOff.isPending || !writing.reason.trim()}
                                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                              >
                                {t('Hisobdan chiqarish')}
                              </button>
                            </div>
                            {error && (
                              <p role="alert" className="text-sm text-red-700 sm:col-span-3">
                                {error}
                              </p>
                            )}
                          </form>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
                {invoices.data?.items.length === 0 && (
                  <EmptyRow colSpan={6} title={t('Hisob-faktura yoʻq')} />
                )}
              </tbody>
            </>
          )}

          {tab === 'payments' && (
            <>
              <thead className="bg-slate-50/70 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5 font-medium">{t('Sana')}</th>
                  <th className="px-4 py-2.5 font-medium">{t('Toʻlov usuli')}</th>
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
                        <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                          {t('Qaytarilgan')}
                        </span>
                      )}
                    </td>
                    <td
                      className={cn(
                        'num px-4 py-2.5 text-right font-medium',
                        payment.is_reversed ? 'text-slate-500 line-through' : 'text-nihol-700',
                      )}
                    >
                      {money(payment.amount)}
                    </td>
                  </tr>
                ))}
                {payments.data?.items.length === 0 && (
                  <EmptyRow colSpan={3} title={t('Toʻlov yoʻq')} />
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
