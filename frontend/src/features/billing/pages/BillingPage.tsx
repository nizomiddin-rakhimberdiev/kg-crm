/**
 * Obuna va hisob-kitob (docs/04 §18).
 *
 * Sahifaning asosiy vazifasi — **kutilmagan hisob bo'lmasligi**. Shuning
 * uchun joriy bolalar soni, keyingi chegara va prognoz qilingan summa
 * doim ko'rinib turadi, va prognoz ochiq "hali olinmagan" deb belgilanadi.
 *
 * Sinovni qabul qilish oynasida to'langan davr SINOV kunidan
 * boshlanishi ochiq yozilgan. Sxema bu siyosatni qo'llab-quvvatlaydi,
 * lekin uni halol qiladigan narsa faqat oldindan aytilgani (docs/01 §4.4).
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, FileText, TrendingUp, Users } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { billingApi } from '@/features/billing/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { cn, formatDate, formatUZS } from '@/lib/utils'

const STATUS: Record<string, [string, string]> = {
  trialing: ['Sinov davri', 'bg-brand-50 text-brand-700'],
  pending_payment: ["To'lov kutilmoqda", 'bg-amber-50 text-amber-700'],
  active: ['Faol', 'bg-emerald-50 text-emerald-700'],
  past_due: ["Muddati o'tgan", 'bg-amber-50 text-amber-800'],
  suspended: ["To'xtatilgan", 'bg-red-50 text-red-700'],
  cancelled: ['Bekor qilingan', 'bg-slate-100 text-slate-600'],
}

const INVOICE_STATUS: Record<string, [string, string]> = {
  issued: ['Yozilgan', 'bg-sky-50 text-sky-700'],
  paid: ["To'langan", 'bg-emerald-50 text-emerald-700'],
  overdue: ["Muddati o'tgan", 'bg-red-50 text-red-700'],
  cancelled: ['Bekor qilingan', 'bg-slate-100 text-slate-600'],
}

const TERMS: Array<{ code: string; label: string; hint: string }> = [
  { code: 'monthly', label: 'Oylik', hint: 'Chegirmasiz, 12 ta to‘lov' },
  { code: 'semiannual', label: 'Yarim yillik', hint: '15 % chegirma, 2 ta to‘lov' },
  { code: 'annual', label: 'Yillik', hint: '25 % chegirma, 1 ta to‘lov' },
]

const day = (iso: string | null) =>
  formatDate(iso)

const daysLeft = (iso: string | null) => {
  if (!iso) return null
  const ms = new Date(iso).getTime() - Date.now()
  return Math.max(0, Math.ceil(ms / 86_400_000))
}

export default function BillingPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()

  const [term, setTerm] = useState('monthly')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const subscriptionQuery = useQuery({
    queryKey: queryKeys.subscription(organizationId),
    queryFn: billingApi.subscription,
  })
  const usageQuery = useQuery({
    queryKey: queryKeys.billingUsage(organizationId),
    queryFn: billingApi.usage,
  })
  const invoicesQuery = useQuery({
    queryKey: queryKeys.billingInvoices(organizationId),
    queryFn: billingApi.invoices,
  })
  const historyQuery = useQuery({
    queryKey: queryKeys.billingUsageHistory(organizationId),
    queryFn: billingApi.usageHistory,
  })

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'billing'] })
  const fail = (err: unknown) => {
    setNotice(null)
    setError(err instanceof ApiError ? err.message : 'Amalni bajarib bo‘lmadi.')
  }

  const accept = useMutation({
    mutationFn: () => billingApi.acceptTrial(term),
    onSuccess: (invoice) => {
      setError(null)
      setNotice(`Hisob ${invoice.number} yozildi — ${formatUZS(Number(invoice.total_amount))}.`)
      invalidate()
    },
    onError: fail,
  })

  const subscription = subscriptionQuery.data
  const usage = usageQuery.data
  const isTrial = subscription?.status === 'trialing'
  const remaining = daysLeft(subscription?.trial_ends_at ?? null)
  const [statusLabel, statusTone] = STATUS[subscription?.status ?? ''] ?? ['—', 'bg-slate-100']

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Obuna va to'lov</h1>
        <p className="mt-1 text-sm text-slate-500">
          Bitta obuna — cheksiz filial va cheksiz xodim. To'lov faqat bolalar soniga.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">
                {subscription?.plan_name ?? 'Reja'}
              </h2>
              <p className="mt-0.5 text-xs text-slate-500">
                {subscription
                  ? `${formatUZS(Number(subscription.base_price))} / oy, ${subscription.included_children} bolagacha`
                  : '…'}
              </p>
            </div>
            <span className={cn('rounded-full px-2.5 py-1 text-xs font-medium', statusTone)}>
              {statusLabel}
            </span>
          </div>

          {subscription && (
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-slate-500">To'lov muddati</dt>
                <dd className="font-medium text-slate-900">
                  {TERMS.find((t) => t.code === subscription.payment_term)?.label ??
                    subscription.payment_term}
                  {Number(subscription.discount_percent) > 0 &&
                    ` (−${Number(subscription.discount_percent)} %)`}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Joriy davr</dt>
                <dd className="font-medium text-slate-900">
                  {day(subscription.current_period_start)} — {day(subscription.current_period_end)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Har qo'shimcha 10 bola</dt>
                <dd className="font-medium text-slate-900">
                  +{formatUZS(Number(subscription.overage_step_price))}
                </dd>
              </div>
              {isTrial && (
                <div>
                  <dt className="text-xs text-slate-500">Sinov tugaydi</dt>
                  <dd className="font-medium text-slate-900">
                    {day(subscription.trial_ends_at)}
                    {remaining !== null && ` (${remaining} kun)`}
                  </dd>
                </div>
              )}
            </dl>
          )}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-brand-600" />
            <h2 className="text-sm font-semibold text-slate-900">Joriy davr prognozi</h2>
          </div>

          {usage ? (
            <>
              <p className="mt-3 text-3xl font-bold tracking-tight text-slate-900">
                {formatUZS(Number(usage.projected.total_amount))}
              </p>
              {/* Bu raqam hali OLINMAGAN — haqiqiy hisob yopilgan dalildan chiqadi. */}
              <p className="text-xs text-amber-700">Prognoz — hali hisoblanmagan</p>

              <dl className="mt-4 space-y-1.5 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Hozirgi bolalar</dt>
                  <dd className="font-medium text-slate-900">{usage.current_children}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Hisoblanadi</dt>
                  <dd className="font-medium text-slate-900">{usage.billable_children}</dd>
                </div>
                {usage.overage_steps > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Qo'shimcha qadam</dt>
                    <dd className="font-medium text-slate-900">
                      {usage.overage_steps} × {formatUZS(Number(usage.projected.overage_amount) / usage.overage_steps)}
                    </dd>
                  </div>
                )}
                {usage.prepaid_base && (
                  <p className="pt-1 text-xs text-emerald-700">
                    Baza oldindan to'langan — faqat o'sish hisoblanadi.
                  </p>
                )}
              </dl>
            </>
          ) : (
            <p className="mt-4 text-sm text-slate-400">…</p>
          )}
        </section>
      </div>

      {isTrial && (
        <section className="rounded-2xl border border-brand-200 bg-brand-50/50 p-5">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-brand-600" />
            <h2 className="text-sm font-semibold text-slate-900">To'lovli rejimga o'tish</h2>
          </div>

          {/* Bu jumla siyosatning halolligi uchun MAJBURIY (docs/01 §4.4). */}
          <p className="mt-2 text-sm text-slate-600">
            Birinchi to'langan oy <strong>sinov boshlangan kundan</strong> hisoblanadi — ya'ni
            sinov kunlari shu oyning ichiga kiradi. Sinov yoqmasa, hech qanday to'lov olinmaydi.
          </p>

          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            {TERMS.map((option) => (
              <button
                key={option.code}
                type="button"
                onClick={() => setTerm(option.code)}
                className={cn(
                  'rounded-xl border p-3 text-left transition-colors',
                  term === option.code
                    ? 'border-brand-500 bg-white ring-1 ring-brand-500'
                    : 'border-slate-200 bg-white hover:border-slate-300',
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-900">{option.label}</span>
                  {term === option.code && <Check className="h-4 w-4 text-brand-600" />}
                </div>
                <p className="mt-0.5 text-xs text-slate-500">{option.hint}</p>
              </button>
            ))}
          </div>

          <button
            type="button"
            disabled={accept.isPending}
            onClick={() => accept.mutate()}
            className="mt-4 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            Qabul qilaman va hisobni olaman
          </button>
        </section>
      )}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <h2 className="border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-900">
          Hisob-fakturalar
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Raqam</th>
                <th className="px-4 py-2">Davr</th>
                <th className="px-4 py-2">Bolalar</th>
                <th className="px-4 py-2 text-right">Summa</th>
                <th className="px-4 py-2">Muddat</th>
                <th className="px-4 py-2">Holat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(invoicesQuery.data ?? []).map((invoice) => {
                const [label, tone] = INVOICE_STATUS[invoice.status] ?? [invoice.status, 'bg-slate-100']
                return (
                  <tr key={invoice.id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{invoice.number}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {day(invoice.period_start)} — {day(invoice.period_end)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{invoice.billable_children}</td>
                    <td className="px-4 py-3 text-right font-semibold text-slate-900">
                      {formatUZS(Number(invoice.total_amount))}
                      {Number(invoice.discount_amount) > 0 && (
                        <span className="block text-xs font-normal text-emerald-600">
                          −{formatUZS(Number(invoice.discount_amount))} chegirma
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{day(invoice.due_at)}</td>
                    <td className="px-4 py-3">
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                        {label}
                      </span>
                    </td>
                  </tr>
                )
              })}
              {(invoicesQuery.data ?? []).length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                    <FileText className="mx-auto mb-2 h-6 w-6" />
                    Hozircha hisob yozilmagan.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {(historyQuery.data ?? []).length > 0 && (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">Hisoblash dalili</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Har bir hisob ortidagi asos — o'zgartirilmaydigan yozuv.
          </p>
          <ul className="mt-3 divide-y divide-slate-100 border-t border-slate-100">
            {(historyQuery.data ?? []).map((row) => (
              <li key={row.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-slate-600">
                  {row.period_year}-{String(row.period_month).padStart(2, '0')}
                  {row.measurement_method === 'manual_adjustment' && (
                    <span className="ml-2 rounded bg-amber-50 px-1.5 py-0.5 text-xs text-amber-700">
                      qo'lda tuzatilgan
                    </span>
                  )}
                  {row.note && <span className="ml-2 text-xs text-slate-400">{row.note}</span>}
                </span>
                <span className="text-slate-900">
                  eng yuqori {row.peak_children} → hisoblangan{' '}
                  <strong>{row.billable_children}</strong>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
