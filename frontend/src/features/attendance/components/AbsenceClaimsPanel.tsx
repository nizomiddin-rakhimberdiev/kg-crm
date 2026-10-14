/**
 * Kelmagan kunlar uchun qayta hisob (ADR-19).
 *
 * Bu ro'yxat davomat jadvalidan ALOHIDA va bu ataylab: davomatda
 * "kelmadi" deb belgilangan kun pul qaytarmaydi. Pul faqat hujjat —
 * shifokor ma'lumotnomasi yoki ota-ona arizasi — asosida harakat
 * qiladi va tasdiqlashdan o'tadi.
 *
 * Tasdiqlangan qaytarish shu oyning hisob-fakturasi hali to'lanmagan
 * bo'lsa O'SHA fakturadan ayriladi; to'langan bo'lsa keyingi oyga minus
 * qator bo'lib o'tadi (PLAN 7.7). Ikkala holatda ham ota-ona qo'lidagi
 * qog'oz bilan balans bir xil raqamni ko'rsatadi.
 *
 * Spravka yoki arizaning O'ZI ham shu yerga biriktiriladi: bir yildan
 * keyin "bu kunlar nega bekor qilingan?" degan savolga javob qog'oz
 * papkada emas, da'voning yonida turadi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarX2, Check, Download, Paperclip, Plus, X } from 'lucide-react'
import { DateInput } from '@/components/ui/DateInput'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { EmptyRow } from '@/components/ui/EmptyState'
import { absenceApi } from '@/features/attendance/api'
import { childrenApi } from '@/features/children/api'
import { invalidateAttendance } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type AbsenceClaim } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate } from '@/lib/utils'
import { money } from '@/lib/format'
import { t } from '@/lib/i18n'

// Yaxlitlanadi: kun narxi bo'linishdan chiqadi va "340 909,1 so'm"
// degan yarim tiyin ekranda ma'nosiz — ilovadagi qolgan pul
// maydonlari ham butun songa yaxlitlaydi.
const KIND_LABELS: Record<string, string> = {
  medical: t('Shifokor maʼlumotnomasi'),
  parental: t('Ota-ona arizasi'),
}

const STATUS: Record<AbsenceClaim['status'], [string, string]> = {
  pending: [t('Kutilmoqda'), 'bg-amber-50 text-amber-700'],
  approved: [t('Tasdiqlangan'), 'bg-emerald-50 text-emerald-700'],
  rejected: [t('Rad etilgan'), 'bg-slate-100 text-slate-600'],
  applied: [t('Hisob-fakturaga tushdi'), 'border border-ildiz-300 bg-ildiz-50 text-ildiz-800'],
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

export function AbsenceClaimsPanel({
  initial,
}: {
  /**
   * Davomatdagi "Sababli" qatoridan kelinganda — bola va sana oldindan
   * tanlangan bo'ladi (2026-10-14): qayta hisob kerak bo'lgan joyda
   * paydo bo'ladi, har kuni ko'z oldida turmaydi.
   */
  initial?: { childId: string; date: string }
} = {}) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [form, setForm] = useState(() =>
    initial
      ? { ...EMPTY, child_id: initial.childId, date_from: initial.date, date_to: initial.date }
      : EMPTY,
  )
  const [file, setFile] = useState<File | null>(null)
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
    invalidateAttendance(queryClient, organizationId)
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const create = useMutation({
    mutationFn: async () => {
      const claim = await absenceApi.create({
        child_id: form.child_id,
        kind: form.kind,
        date_from: form.date_from,
        date_to: form.date_to,
        ...(form.document_no ? { document_no: form.document_no } : {}),
        ...(form.note ? { note: form.note } : {}),
      })
      // Fayl ALOHIDA so'rov bilan ketadi: da'vo yaratilgan bo'lsa-yu
      // yuklash uzilib qolsa, kiritilgan kunlar yo'qolmaydi — hujjatni
      // keyin biriktirsa bo'ladi.
      if (file) await absenceApi.attachDocument(claim.id, file)
      return claim
    },
    onSuccess: () => {
      setForm(EMPTY)
      setFile(null)
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const attach = useMutation({
    mutationFn: ({ id, picked }: { id: string; picked: File }) =>
      absenceApi.attachDocument(id, picked),
    onSuccess: () => {
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
            'Faqat hujjat asosida: shifokor maʼlumotnomasi yoki ota-ona arizasi. Qoʻshilishi bilan hisob-fakturadan ayriladi — alohida tasdiqlash shart emas.',
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
            <DateInput
              id="ac-from"
              required
              value={form.date_from}
              onChange={(iso) => setForm((p) => ({ ...p, date_from: iso }))}
            />
          </div>

          <div>
            <label htmlFor="ac-to" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Tugashi')}
            </label>
            <DateInput
              id="ac-to"
              required
              value={form.date_to}
              onChange={(iso) => setForm((p) => ({ ...p, date_to: iso }))}
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={create.isPending}
              className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              <Plus className="h-4 w-4" /> {t('Qoʻshish')}
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
            <label htmlFor="ac-file" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Spravka yoki ariza (ixtiyoriy)')}
            </label>
            <input
              id="ac-file"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp,.heic"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-slate-700"
            />
            <p className="mt-1 text-xs text-slate-500">{t('PDF yoki rasm, 10 MB gacha')}</p>
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
                      <span className="ml-1.5 text-xs text-slate-500">{claim.document_no}</span>
                    )}
                    {claim.has_document ? (
                      <button
                        type="button"
                        onClick={() =>
                          absenceApi
                            .downloadDocument(claim.id, claim.document_name || 'hujjat')
                            .catch(fail)
                        }
                        title={t('Hujjatni yuklab olish')}
                        aria-label={t('Hujjatni yuklab olish')}
                        className="ml-1.5 inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs text-brand-700 transition hover:bg-brand-50"
                      >
                        <Download className="h-3.5 w-3.5" /> {t('Hujjat')}
                      </button>
                    ) : (
                      // Hujjati yo'q da'voga birinchi fayl qo'shiladi —
                      // tasdiqlangan bo'lsa ham (qog'oz ko'pincha keyin
                      // keladi). Almashtirish esa yopiq: tasdiqlovchi
                      // ko'rgan dalil keyin o'zgarmasligi kerak.
                      claim.status !== 'rejected' &&
                      can('attendance.create') && (
                        <label className="ml-1.5 inline-flex cursor-pointer items-center gap-1 rounded-md px-1.5 py-0.5 text-xs text-slate-500 transition hover:bg-slate-100">
                          <Paperclip className="h-3.5 w-3.5" /> {t('Biriktirish')}
                          <input
                            type="file"
                            className="sr-only"
                            accept=".pdf,.png,.jpg,.jpeg,.webp,.heic"
                            aria-label={t('Hujjat biriktirish')}
                            onChange={(e) => {
                              const picked = e.target.files?.[0]
                              if (picked) attach.mutate({ id: claim.id, picked })
                              e.target.value = ''
                            }}
                          />
                        </label>
                      )
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatDate(claim.date_from)} — {formatDate(claim.date_to)}
                    {claim.billable_days > 0 && (
                      <span className="ml-1.5 text-xs text-slate-500">
                        {t('{v} ish kuni', { v: claim.billable_days })}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                    {Number(claim.credit_amount) > 0
                      ? t('{money} soʻm', { money: money(claim.credit_amount) })
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
                          aria-label={t('Tasdiqlash')}
                          onClick={() => decide.mutate({ id: claim.id, approve: true })}
                          className="rounded-lg p-2 text-emerald-600 transition hover:bg-emerald-50"
                        >
                          <Check className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          title={t('Rad etish')}
                          aria-label={t('Rad etish')}
                          onClick={() => decide.mutate({ id: claim.id, approve: false })}
                          className="rounded-lg p-2 text-slate-500 transition hover:bg-red-50 hover:text-red-600"
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
                  title={t('Hujjatli kelmaslik yoʻq')}
                  hint={t(
                    'Maʼlumotnoma yoki ariza keltirilganda shu yerga yoziladi — va tasdiqlangach toʻlovdan ayriladi.',
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
