/**
 * Kelmagan kunlar uchun qayta hisob (ADR-19).
 *
 * Bu ro'yxat davomat jadvalidan ALOHIDA va bu ataylab: davomatda
 * "kelmadi" deb belgilangan kun pul qaytarmaydi. Pul faqat hujjat —
 * shifokor ma'lumotnomasi yoki ota-ona arizasi — asosida harakat
 * qiladi va tasdiqlashdan o'tadi.
 *
 * Tasdiqlangan qaytarish keyingi hisob-fakturaga minus qator bo'lib
 * tushadi, ya'ni ota-ona qo'lidagi qog'oz bilan balans bir xil raqamni
 * ko'rsatadi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarX2, Check, Plus, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { EmptyRow } from '@/components/ui/EmptyState'
import { absenceApi } from '@/features/attendance/api'
import { childrenApi } from '@/features/children/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type AbsenceClaim } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate } from '@/lib/utils'
import { t } from '@/lib/i18n'

// Yaxlitlanadi: kun narxi bo'linishdan chiqadi va "340 909,1 so'm"
// degan yarim tiyin ekranda ma'nosiz — ilovadagi qolgan pul
// maydonlari ham butun songa yaxlitlaydi.
const money = (value: string) => new Intl.NumberFormat('uz-UZ').format(Math.round(Number(value)))

const KIND_LABELS: Record<string, string> = {
  medical: t("Shifokor ma'lumotnomasi"),
  parental: t('Ota-ona arizasi'),
}

const STATUS: Record<AbsenceClaim['status'], [string, string]> = {
  pending: [t('Kutilmoqda'), 'bg-amber-50 text-amber-700'],
  approved: [t('Tasdiqlangan'), 'bg-emerald-50 text-emerald-700'],
  rejected: [t('Rad etilgan'), 'bg-slate-100 text-slate-500'],
  applied: [t('Hisob-fakturaga tushdi'), 'bg-sky-50 text-sky-700'],
}

const EMPTY = {
  child_id: '',
  kind: 'medical' as 'medical' | 'parental',
  date_from: '',
  date_to: '',
  document_no: '',
  note: '',
}

const fieldClass =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'

export function AbsenceClaimsPanel() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState<string | null>(null)

  const claimsQuery = useQuery({
    queryKey: queryKeys.absenceClaims(organizationId),
    queryFn: () => absenceApi.list(),
  })
  const childrenQuery = useQuery({
    queryKey: queryKeys.children(organizationId, { page_size: 500 }),
    queryFn: () => childrenApi.list({ page_size: 500 }),
    enabled: can('attendance.create'),
  })

  const invalidate = () => {
    // Qaytarish hisob-fakturaga, balansga va qarzdorlarga ta'sir qiladi.
    for (const key of ['absence-claims', 'invoices', 'children', 'debtors']) {
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, key] })
    }
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const create = useMutation({
    mutationFn: () =>
      absenceApi.create({
        child_id: form.child_id,
        kind: form.kind,
        date_from: form.date_from,
        date_to: form.date_to,
        ...(form.document_no ? { document_no: form.document_no } : {}),
        ...(form.note ? { note: form.note } : {}),
      }),
    onSuccess: () => {
      setForm(EMPTY)
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: string; approve: boolean }) =>
      approve ? absenceApi.approve(id) : absenceApi.reject(id),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const claims = claimsQuery.data?.items ?? []

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">
          {t('Kelmagan kunlar uchun qayta hisob')}
        </h2>
        <p className="mt-0.5 text-xs text-slate-500">
          {t(
            "Faqat hujjat asosida: shifokor ma'lumotnomasi yoki ota-ona arizasi. Tasdiqlangach keyingi hisob-fakturaga minus qator bo'lib tushadi.",
          )}
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {can('attendance.create') && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            create.mutate()
          }}
          className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2 xl:grid-cols-6"
        >
          <div className="xl:col-span-2">
            <label htmlFor="ac-child" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Bola')}
            </label>
            <select
              id="ac-child"
              required
              value={form.child_id}
              onChange={(e) => setForm((p) => ({ ...p, child_id: e.target.value }))}
              className={fieldClass}
            >
              <option value="">{t('Tanlang…')}</option>
              {childrenQuery.data?.items.map((child) => (
                <option key={child.id} value={child.id}>
                  {child.full_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="ac-kind" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Hujjat')}
            </label>
            <select
              id="ac-kind"
              value={form.kind}
              onChange={(e) =>
                setForm((p) => ({ ...p, kind: e.target.value as typeof EMPTY.kind }))
              }
              className={fieldClass}
            >
              {Object.entries(KIND_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="ac-from" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Boshlanishi')}
            </label>
            <input
              id="ac-from"
              type="date"
              required
              value={form.date_from}
              onChange={(e) => setForm((p) => ({ ...p, date_from: e.target.value }))}
              className={fieldClass}
            />
          </div>

          <div>
            <label htmlFor="ac-to" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Tugashi')}
            </label>
            <input
              id="ac-to"
              type="date"
              required
              value={form.date_to}
              onChange={(e) => setForm((p) => ({ ...p, date_to: e.target.value }))}
              className={fieldClass}
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={create.isPending}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <Plus className="h-4 w-4" /> {t("Qo'shish")}
            </button>
          </div>

          <div className="sm:col-span-2 xl:col-span-3">
            <label htmlFor="ac-doc" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Hujjat raqami (ixtiyoriy)')}
            </label>
            <input
              id="ac-doc"
              maxLength={60}
              value={form.document_no}
              placeholder={t('Masalan: № 145')}
              onChange={(e) => setForm((p) => ({ ...p, document_no: e.target.value }))}
              className={fieldClass}
            />
          </div>
          <div className="sm:col-span-2 xl:col-span-3">
            <label htmlFor="ac-note" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Izoh')}
            </label>
            <input
              id="ac-note"
              maxLength={255}
              value={form.note}
              onChange={(e) => setForm((p) => ({ ...p, note: e.target.value }))}
              className={fieldClass}
            />
          </div>
        </form>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">{t('Bola')}</th>
                <th className="px-4 py-3 font-medium">{t('Hujjat')}</th>
                <th className="px-4 py-3 font-medium">{t('Kunlar')}</th>
                <th className="px-4 py-3 text-right font-medium">{t('Qaytariladi')}</th>
                <th className="px-4 py-3 font-medium">{t('Holat')}</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {claims.map((claim) => (
                <tr key={claim.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-800">{claim.child_name}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {KIND_LABELS[claim.kind] ?? claim.kind}
                    {claim.document_no && (
                      <span className="ml-1.5 text-xs text-slate-400">{claim.document_no}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatDate(claim.date_from)} — {formatDate(claim.date_to)}
                    {claim.billable_days > 0 && (
                      <span className="ml-1.5 text-xs text-slate-400">
                        {t('{v} ish kuni', { v: claim.billable_days })}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                    {Number(claim.credit_amount) > 0
                      ? t("{money} so'm", { money: money(claim.credit_amount) })
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-medium',
                        STATUS[claim.status][1],
                      )}
                    >
                      {STATUS[claim.status][0]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {claim.status === 'pending' && can('attendance.approve') && (
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          title={t('Tasdiqlash')}
                          onClick={() => decide.mutate({ id: claim.id, approve: true })}
                          className="rounded-lg p-2 text-emerald-600 transition hover:bg-emerald-50"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          title={t('Rad etish')}
                          onClick={() => decide.mutate({ id: claim.id, approve: false })}
                          className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {claims.length === 0 && !claimsQuery.isPending && (
                <EmptyRow
                  colSpan={6}
                  icon={CalendarX2}
                  title={t("Hujjatli kelmaslik yo'q")}
                  hint={t(
                    "Spravka yoki ariza keltirilganda shu yerga yoziladi — va tasdiqlangach to'lovdan ayriladi.",
                  )}
                />
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
