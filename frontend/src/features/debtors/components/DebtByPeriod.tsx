/**
 * Qarzdorlik tarixi — oy boʻyicha (PLAN 9.2).
 *
 * Egasining savoli: "sentabrda 15 boladan 28 mln qolgan edi, oktabrda
 * 24 mln yopildi, 4 mln qoldi — buni qayerdan koʻraman?". Qarzdorlar
 * roʻyxati bu savolga javob bera olmaydi: u BUGUNGI qoldiqni
 * koʻrsatadi va qaysi oydan qolganini bilmaydi.
 *
 * Javob hisob-faktura davri va toʻlov taqsimotida (ADR-20): oktabrda
 * kelgan pul sentabr fakturasini yopgan boʻlsa, u sentabr qatorida
 * koʻrinadi. Qatorni ochganda — kim, qancha, qachon va nima orqali.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, History } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { EmptyRow } from '@/components/ui/EmptyState'
import { groupsApi } from '@/features/children/api'
import { debtorsApi } from '@/features/payments/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { formatDate, monthLabel, som } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

/** Toʻlov usullari — odam tilida (hisobotda kod turishi yaramaydi). */
const METHOD: Record<string, string> = {
  cash: t('Naqd'),
  terminal: t('Terminal'),
  bank_transfer: t('Oʻtkazma'),
  online: t('Payme / Click'),
}

/** Oxirgi 12 oy — "qachonniki?" savoli odatda shu oraliqda. */
const defaultRange = () => {
  const now = new Date()
  const to = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  const start = new Date(now.getFullYear(), now.getMonth() - 11, 1)
  const from = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}`
  return { from, to }
}

export function DebtByPeriod() {
  const organizationId = useOrganizationId()
  const [range, setRange] = useState(defaultRange)
  const [groupId, setGroupId] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const [debtorsOnly, setDebtorsOnly] = useState(true)

  const params = { ...range, ...(groupId ? { group_id: groupId } : {}) }
  const periodsQuery = useQuery({
    queryKey: ['org', organizationId, 'debt-periods', params],
    queryFn: () => debtorsApi.byPeriod(params),
  })
  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: () => groupsApi.list(),
  })

  const detailQuery = useQuery({
    queryKey: ['org', organizationId, 'debt-period', open, groupId, debtorsOnly],
    queryFn: () =>
      debtorsApi.periodChildren({
        period: open as string,
        ...(groupId ? { group_id: groupId } : {}),
        ...(debtorsOnly ? { debtors_only: 'true' } : {}),
      }),
    enabled: Boolean(open),
  })

  const rows = periodsQuery.data?.results ?? []
  const totals = periodsQuery.data?.totals

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="dp-from" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Davr boshi')}
          </label>
          <input
            id="dp-from"
            type="month"
            value={range.from}
            onChange={(e) => setRange((prev) => ({ ...prev, from: e.target.value }))}
            className="h-11 rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-brand-500"
          />
        </div>
        <div>
          <label htmlFor="dp-to" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Davr oxiri')}
          </label>
          <input
            id="dp-to"
            type="month"
            value={range.to}
            onChange={(e) => setRange((prev) => ({ ...prev, to: e.target.value }))}
            className="h-11 rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-brand-500"
          />
        </div>
        <div>
          <label htmlFor="dp-group" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Guruh')}
          </label>
          <select
            id="dp-group"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value)}
            className="h-11 rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-brand-500"
          >
            <option value="">{t('Hammasi')}</option>
            {(groupsQuery.data?.items ?? []).map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
        </div>
        <label className="inline-flex min-h-[44px] cursor-pointer items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={debtorsOnly}
            onChange={(e) => setDebtorsOnly(e.target.checked)}
            className="h-[18px] w-[18px] rounded border-slate-300 accent-brand-600"
          />
          {t('Faqat qarzi borlar')}
        </label>
      </div>

      {totals && (
        <div className="grid gap-3 sm:grid-cols-3">
          {(
            [
              [t('Hisoblangan'), totals.invoiced, 'text-slate-900'],
              [t('Toʻlangan'), totals.paid, 'text-emerald-700'],
              [t('Qoldiq'), totals.outstanding, 'text-orik-800'],
            ] as const
          ).map(([label, value, tone]) => (
            <div key={label} className="rounded-xl border border-slate-200 bg-white p-4">
              <p className="text-xs font-medium text-slate-600">{label}</p>
              <p className={cn('mt-1 text-lg font-bold tabular-nums', tone)}>{som(value)}</p>
            </div>
          ))}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-600">
              <tr>
                <th className="px-4 py-3 font-medium">{t('Oy')}</th>
                <th className="px-4 py-3 text-right font-medium">{t('Hisoblangan')}</th>
                <th className="px-4 py-3 text-right font-medium">{t('Toʻlangan')}</th>
                <th className="px-4 py-3 text-right font-medium">{t('Qoldiq')}</th>
                <th className="px-4 py-3 text-right font-medium">{t('Qarzdorlar')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => {
                const isOpen = open === row.period
                return (
                  <>
                    <tr
                      key={row.period}
                      className={cn('cursor-pointer hover:bg-slate-50', isOpen && 'bg-slate-50')}
                      onClick={() => setOpen(isOpen ? null : row.period)}
                    >
                      <td className="px-4 py-3 font-medium text-slate-800">
                        <span className="inline-flex items-center gap-1.5">
                          {isOpen ? (
                            <ChevronDown className="h-4 w-4 text-slate-500" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-slate-500" />
                          )}
                          {monthLabel(row.period_year, row.period_month)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                        {som(row.invoiced)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-emerald-700">
                        {som(row.paid)}
                        {Number(row.paid_late) > 0 && (
                          <span className="ml-1 text-xs text-slate-500">
                            {t('shundan kech: {v}', { v: som(row.paid_late) })}
                          </span>
                        )}
                      </td>
                      <td
                        className={cn(
                          'px-4 py-3 text-right font-semibold tabular-nums',
                          Number(row.outstanding) > 0 ? 'text-orik-800' : 'text-slate-500',
                        )}
                      >
                        {som(row.outstanding)}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                        {row.debtors} / {row.children}
                      </td>
                    </tr>

                    {isOpen && (
                      <tr key={`${row.period}-detail`}>
                        <td colSpan={5} className="bg-slate-50/60 px-4 py-3">
                          {detailQuery.isPending ? (
                            <p className="text-sm text-slate-500">{t('Yuklanmoqda…')}</p>
                          ) : (detailQuery.data?.results ?? []).length === 0 ? (
                            <p className="text-sm text-slate-500">
                              {t('Bu oyda qarzi bor bola yoʻq.')}
                            </p>
                          ) : (
                            <div className="grid gap-2">
                              {(detailQuery.data?.results ?? []).map((child) => (
                                <div
                                  key={child.invoice_id}
                                  className="rounded-xl border border-slate-200 bg-white p-3"
                                >
                                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                                    <p className="font-semibold text-slate-900">
                                      {child.child_name}
                                      <span className="ml-2 text-xs font-normal text-slate-500">
                                        {child.invoice_number}
                                      </span>
                                    </p>
                                    <p className="text-sm tabular-nums text-slate-600">
                                      {t('Hisoblangan')}: {som(child.invoiced)} · {t('Toʻlangan')}:{' '}
                                      {som(child.paid)} ·{' '}
                                      <span
                                        className={cn(
                                          'font-semibold',
                                          Number(child.outstanding) > 0
                                            ? 'text-orik-800'
                                            : 'text-emerald-700',
                                        )}
                                      >
                                        {t('Qoldiq')}: {som(child.outstanding)}
                                      </span>
                                    </p>
                                  </div>

                                  {child.payments.length > 0 ? (
                                    <ul className="mt-2 grid gap-1">
                                      {child.payments.map((payment) => (
                                        <li
                                          key={payment.payment_id + payment.paid_at}
                                          className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[13px] text-slate-600"
                                        >
                                          <span className="tabular-nums">
                                            {formatDate(payment.paid_at)}
                                          </span>
                                          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                                            {METHOD[payment.method] ?? payment.method}
                                          </span>
                                          <span className="font-semibold tabular-nums text-slate-800">
                                            {som(payment.amount)}
                                          </span>
                                        </li>
                                      ))}
                                    </ul>
                                  ) : (
                                    <p className="mt-2 text-[13px] text-slate-500">
                                      {t('Bu oy uchun hali toʻlov boʻlmagan.')}
                                    </p>
                                  )}

                                  {child.days_overdue > 0 && (
                                    <p className="mt-2 text-xs text-orik-800">
                                      {t('Muddati: {date} · {days} kun kechikkan', {
                                        date: formatDate(child.due_date),
                                        days: child.days_overdue,
                                      })}
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}

              {rows.length === 0 && !periodsQuery.isPending && (
                <EmptyRow
                  colSpan={5}
                  icon={History}
                  title={t('Bu davrda hisob-faktura yoʻq')}
                  hint={t('Davrni kengaytiring yoki boshqa guruhni tanlang.')}
                />
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
