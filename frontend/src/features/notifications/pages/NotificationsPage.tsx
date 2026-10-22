/**
 * Bildirishnomalar (docs/04 §15).
 *
 * Bu sahifa avvalo JURNAL: "SMS kelmadi" degan shikoyatga javob shu
 * yerda — kimga, qaysi raqamga, qanday matn ketgani va nima bo'lgani.
 * Yuborish tugmalari ikkinchi darajali.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { BellRing, RefreshCw, Send } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { notificationsApi, templatesApi } from '@/features/notifications/api'
import { ReminderConfirmDialog } from '@/features/notifications/components/ReminderConfirmDialog'
import { SmsUsageCard } from '@/features/notifications/components/SmsUsageCard'
import { TemplateEditor } from '@/features/notifications/components/TemplateEditor'
import { TestModeBanner } from '@/features/notifications/components/TestModeBanner'
import { useSmsStatus } from '@/features/notifications/useSmsStatus'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { QueryError } from '@/components/ui/QueryError'
import { formatDateTime } from '@/lib/format'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const STATUS: Record<string, [string, string]> = {
  queued: [t('Navbatda'), 'bg-tosh-100 text-tosh-600'],
  sent: [t('Yuborildi'), 'bg-nihol-50 text-nihol-700'],
  delivered: [t('Yetkazildi'), 'bg-nihol-50 text-nihol-700'],
  // Test rejimi — "Yuborildi" EMAS (PLAN 3.2). Xabar hech qayerga
  // ketmagan va jurnal buni aytishi kerak.
  test_mode: [t('Test rejimi'), 'bg-orik-100 text-orik-900'],
  failed: [t('Xato'), 'bg-orik-50 text-orik-800'],
  cancelled: [t('Bekor qilingan'), 'bg-tosh-100 text-tosh-600'],
}

const when = (value: string | null) => (value ? formatDateTime(value) : '—')

type Tab = 'history' | 'send' | 'templates'

export default function NotificationsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const [searchParams, setSearchParams] = useSearchParams()

  const [status, setStatus] = useState('')
  const [error, setError] = useState<string | null>(null)
  // Ommaviy yuborish TASDIQ bilan (PLAN 3.5): tugma 200 ta SMS
  // yuborishi mumkin va uni qaytarib bo'lmaydi.
  const [confirming, setConfirming] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  // Uchta tab (audit, 2026-10-21): ilgari shablonlar, statistika va
  // jurnal bitta uzun sahifada turardi va "SMS kelmadi" degan savol
  // bilan kelgan odam jurnalga yetib borish uchun pastga surardi.
  //
  // Tartib ATAYLAB jurnaldan boshlanadi: bu sahifa avvalo jurnal
  // (yuqoridagi izoh), auditning taklif qilgan tartibi esa yuborishni
  // oldinga qoʻyardi.
  const tabs: Array<{ key: Tab; label: string }> = [
    { key: 'history', label: t('Tarix') },
    ...(can('notifications.create') ? [{ key: 'send' as Tab, label: t('Yuborish') }] : []),
    ...(can('notifications.update') ? [{ key: 'templates' as Tab, label: t('Shablonlar') }] : []),
  ]
  const requested = searchParams.get('tab') as Tab | null
  const tab: Tab = tabs.find((item) => item.key === requested)?.key ?? 'history'
  const selectTab = (next: Tab) => {
    const params = new URLSearchParams(searchParams)
    if (next === 'history') params.delete('tab')
    else params.set('tab', next)
    setSearchParams(params, { replace: true })
  }

  const params = status ? { status } : undefined
  const logQuery = useQuery({
    queryKey: queryKeys.notifications(organizationId, params),
    queryFn: () => notificationsApi.list(params),
  })
  const templatesQuery = useQuery({
    queryKey: queryKeys.notificationTemplates(organizationId),
    queryFn: templatesApi.list,
  })
  const statusQuery = useSmsStatus()

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'notifications'] })
  const fail = (err: unknown) => {
    setNotice(null)
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))
  }

  const remind = useMutation({
    mutationFn: () => notificationsApi.remindDebtors(),
    onSuccess: (result) => {
      setError(null)
      setConfirming(false)
      setNotice(
        result.queued === 0
          ? t('Qarzdor topilmadi — hech kimga eslatma yuborilmadi.')
          : t('{queued} ta eslatma yuborildi.', { queued: result.queued }),
      )
      invalidate()
    },
    onError: fail,
  })

  const retry = useMutation({
    mutationFn: (id: string) => notificationsApi.retry(id),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const rows = logQuery.data?.items ?? []

  return (
    <div className="space-y-6">
      <ReminderConfirmDialog
        open={confirming}
        filters={{}}
        busy={remind.isPending}
        onConfirm={() => remind.mutate()}
        onCancel={() => setConfirming(false)}
      />

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {t('Bildirishnomalar')}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('Yuborilgan har bir xabar shu yerda qoladi — holati va sababi bilan.')}
          </p>
        </div>
      </div>

      {/* Test rejimi — jurnal "Yuborildi" deb yolg'on gapirmasligi
          uchun eng tepada va HAR BIR tabda (PLAN 3.2). */}
      <TestModeBanner />

      {tabs.length > 1 && (
        <div className="-mx-3 overflow-x-auto px-3 sm:mx-0 sm:px-0">
          <div className="flex min-w-max gap-1 border-b border-slate-200">
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => selectTab(key)}
                className={cn(
                  '-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition sm:px-4',
                  tab === key
                    ? 'border-brand-600 text-brand-700'
                    : 'border-transparent text-slate-500 hover:text-slate-800',
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {tab === 'send' && (
        <div className="space-y-4">
          {statusQuery.data && <SmsUsageCard status={statusQuery.data} />}
          <section className="rounded-2xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-slate-900">{t('Qarzdorlarga eslatma')}</h2>
            <p className="mt-1 text-xs text-slate-500">
              {t(
                'Qarzi bor har bir oilaga bitta xabar. Yuborishdan oldin nechta xabar ketishi koʻrsatiladi.',
              )}
            </p>
            <button
              type="button"
              onClick={() => setConfirming(true)}
              disabled={remind.isPending}
              className="mt-3 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <BellRing className="h-4 w-4" />
              {remind.isPending ? t('Yuborilmoqda…') : t('Qarzdorlarga eslatma')}
            </button>
          </section>
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-900">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div>
      )}

      {tab === 'templates' && templatesQuery.data && (
        <TemplateEditor templates={templatesQuery.data.items} />
      )}

      {tab === 'history' && (
        <>
          <div className="flex items-center gap-2">
            {[
              ['', t('Hammasi')],
              ['sent', t('Yuborilgan')],
              ['failed', t('Xato')],
              ['queued', t('Navbatda')],
            ].map(([key, label]) => (
              <button
                key={key || 'all'}
                type="button"
                onClick={() => setStatus(key)}
                className={cn(
                  'rounded-lg px-3 py-1.5 text-sm font-medium',
                  status === key
                    ? 'bg-slate-900 text-white'
                    : 'bg-white text-slate-600 hover:bg-slate-50',
                )}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">{t('Qabul qiluvchi')}</th>
                    <th className="px-4 py-3">{t('Matn')}</th>
                    <th className="px-4 py-3">{t('Holat')}</th>
                    <th className="px-4 py-3">{t('Yuborilgan')}</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((row) => {
                    const [label, tone] = STATUS[row.status] ?? [
                      row.status,
                      'bg-slate-100 text-slate-600',
                    ]
                    return (
                      <tr key={row.id} className="align-top">
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-900">{row.guardian_name ?? '—'}</p>
                          <p className="text-xs text-slate-500">{row.recipient_address}</p>
                        </td>
                        <td className="max-w-md px-4 py-3 text-slate-600">
                          {row.rendered_body}
                          {row.error && <p className="mt-1 text-xs text-red-600">{row.error}</p>}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}
                          >
                            {label}
                          </span>
                          {row.retry_count > 0 && (
                            <p className="mt-1 text-xs text-slate-500">
                              {t('{retry_count} urinish', { retry_count: row.retry_count })}
                            </p>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-slate-500">
                          {when(row.sent_at)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {row.status === 'failed' && can('notifications.create') && (
                            <button
                              type="button"
                              onClick={() => retry.mutate(row.id)}
                              disabled={retry.isPending}
                              className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                            >
                              <RefreshCw className="h-3 w-3" />
                              {t('Qayta')}
                            </button>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                  {logQuery.isError && (
                    <tr>
                      <td colSpan={5} className="p-0">
                        <QueryError error={logQuery.error} onRetry={() => logQuery.refetch()} />
                      </td>
                    </tr>
                  )}
                  {rows.length === 0 && !logQuery.isError && (
                    <tr>
                      <td colSpan={5} className="px-4 py-10 text-center text-slate-500">
                        <Send className="mx-auto mb-2 h-6 w-6" />
                        {t('Hozircha xabar yuborilmagan.')}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
