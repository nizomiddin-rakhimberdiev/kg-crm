/**
 * Bildirishnomalar (docs/04 §15).
 *
 * Bu sahifa avvalo JURNAL: "SMS kelmadi" degan shikoyatga javob shu
 * yerda — kimga, qaysi raqamga, qanday matn ketgani va nima bo'lgani.
 * Yuborish tugmalari ikkinchi darajali.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BellRing, RefreshCw, Send } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { notificationsApi, templatesApi } from '@/features/notifications/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const STATUS: Record<string, [string, string]> = {
  queued: ['Navbatda', 'bg-slate-100 text-slate-600'],
  sent: ['Yuborildi', 'bg-emerald-50 text-emerald-700'],
  failed: ['Xato', 'bg-red-50 text-red-700'],
  cancelled: ['Bekor qilingan', 'bg-amber-50 text-amber-700'],
}

const TEMPLATE_LABEL: Record<string, string> = {
  payment_received: "To'lov qabul qilindi",
  debt_reminder: 'Qarzdorlik eslatmasi',
  absence_notice: 'Kelmagani haqida',
}

const when = (value: string | null) =>
  value ? new Date(value).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' }) : '—'

export default function NotificationsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [status, setStatus] = useState('')
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const params = status ? { status } : undefined
  const logQuery = useQuery({
    queryKey: queryKeys.notifications(organizationId, params),
    queryFn: () => notificationsApi.list(params),
  })
  const templatesQuery = useQuery({
    queryKey: queryKeys.notificationTemplates(organizationId),
    queryFn: templatesApi.list,
  })

  const invalidate = () =>
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'notifications'] })
  const fail = (err: unknown) => {
    setNotice(null)
    setError(err instanceof ApiError ? err.message : 'Xatolik yuz berdi.')
  }

  const remind = useMutation({
    mutationFn: notificationsApi.remindDebtors,
    onSuccess: (result) => {
      setError(null)
      setNotice(
        result.queued === 0
          ? 'Qarzdor topilmadi — hech kimga eslatma yuborilmadi.'
          : `${result.queued} ta eslatma yuborildi.`,
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

  const saveTemplate = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) => templatesApi.update(id, { body }),
    onSuccess: (template) => {
      setError(null)
      setNotice('Shablon saqlandi.')
      setDraft((prev) => {
        const next = { ...prev }
        delete next[template.id]
        return next
      })
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notificationTemplates(organizationId),
      })
    },
    onError: fail,
  })

  const rows = logQuery.data?.items ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Bildirishnomalar</h1>
          <p className="mt-1 text-sm text-slate-500">
            Yuborilgan har bir xabar shu yerda qoladi — holati va sababi bilan.
          </p>
        </div>
        {can('notifications.create') && (
          <button
            type="button"
            onClick={() => remind.mutate()}
            disabled={remind.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            <BellRing className="h-4 w-4" />
            Qarzdorlarga eslatma
          </button>
        )}
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div>
      )}

      {/* Shablonlar — matnni bog'cha o'zi tahrirlaydi, bu mahsulot qarori emas. */}
      {can('notifications.update') && templatesQuery.data && (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">Xabar shablonlari</h2>
          <p className="mt-1 text-xs text-slate-500">
            <code className="rounded bg-slate-100 px-1">${'{guardian}'}</code>,{' '}
            <code className="rounded bg-slate-100 px-1">${'{child}'}</code>,{' '}
            <code className="rounded bg-slate-100 px-1">${'{amount}'}</code>,{' '}
            <code className="rounded bg-slate-100 px-1">${'{organization}'}</code> o'rinbosarlari
            yuborishda to'ldiriladi.
          </p>
          <div className="mt-3 space-y-3">
            {templatesQuery.data.items.map((template) => {
              const value = draft[template.id] ?? template.body
              const dirty = value !== template.body
              return (
                <div key={template.id} className="space-y-1">
                  <label
                    htmlFor={`tpl-${template.id}`}
                    className="text-xs font-medium text-slate-600"
                  >
                    {TEMPLATE_LABEL[template.code] ?? template.code}
                  </label>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <textarea
                      id={`tpl-${template.id}`}
                      rows={2}
                      value={value}
                      onChange={(e) =>
                        setDraft((prev) => ({ ...prev, [template.id]: e.target.value }))
                      }
                      className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                    />
                    <button
                      type="button"
                      disabled={!dirty || saveTemplate.isPending}
                      onClick={() => saveTemplate.mutate({ id: template.id, body: value })}
                      className="h-fit rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
                    >
                      Saqlash
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}

      <div className="flex items-center gap-2">
        {[
          ['', 'Hammasi'],
          ['sent', 'Yuborilgan'],
          ['failed', 'Xato'],
          ['queued', 'Navbatda'],
        ].map(([key, label]) => (
          <button
            key={key || 'all'}
            type="button"
            onClick={() => setStatus(key)}
            className={cn(
              'rounded-lg px-3 py-1.5 text-sm font-medium',
              status === key ? 'bg-slate-900 text-white' : 'bg-white text-slate-600 hover:bg-slate-50',
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
                <th className="px-4 py-3">Qabul qiluvchi</th>
                <th className="px-4 py-3">Matn</th>
                <th className="px-4 py-3">Holat</th>
                <th className="px-4 py-3">Yuborilgan</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => {
                const [label, tone] = STATUS[row.status] ?? [row.status, 'bg-slate-100 text-slate-600']
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
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                        {label}
                      </span>
                      {row.retry_count > 0 && (
                        <p className="mt-1 text-xs text-slate-400">{row.retry_count} urinish</p>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-slate-500">{when(row.sent_at)}</td>
                    <td className="px-4 py-3 text-right">
                      {row.status === 'failed' && can('notifications.create') && (
                        <button
                          type="button"
                          onClick={() => retry.mutate(row.id)}
                          disabled={retry.isPending}
                          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                        >
                          <RefreshCw className="h-3 w-3" />
                          Qayta
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-slate-400">
                    <Send className="mx-auto mb-2 h-6 w-6" />
                    Hozircha xabar yuborilmagan.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
