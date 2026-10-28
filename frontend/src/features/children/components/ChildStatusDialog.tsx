/**
 * Holatni o'zgartirish — sana va sabab bilan (Q5, PLAN 2.1).
 *
 * Ikkalasi ham majburiy va bu ataylab: "Chiqib ketgan" degan holat
 * o'zi hech narsa demaydi. Savol har doim pul bilan birga keladi —
 * "qachondan buyon?" — chunki o'sha sanadan keyin hisob-faktura
 * yozilmaydi.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { DateInput } from '@/components/ui/DateInput'
import { Modal } from '@/components/ui/Modal'
import { childrenApi } from '@/features/children/api'
import { ApiError, type Child } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'
import { STATUS_LABELS, STATUS_ORDER, WITHDRAW_REASONS } from '@/features/children/status'

export function ChildStatusDialog({
  child,
  onClose,
  onDone,
}: {
  child: Child
  onClose: () => void
  onDone: () => void
}) {
  const [form, setForm] = useState({
    enrollment_status: child.enrollment_status,
    status_changed_on: new Date().toISOString().slice(0, 10),
    status_reason: '',
    status_reason_code: '',
  })

  // Sabab roʻyxati faqat KETISHDA soʻraladi: "faol" yoki "sinovda"
  // uchun "nega ketdi?" degan savolning maʼnosi yoʻq.
  const leaving = form.enrollment_status === 'withdrawn'
  const trial = form.enrollment_status === 'trial'
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () => childrenApi.changeStatus(child.id, form),
    onSuccess: () => {
      onDone()
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const field =
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <form
        className="p-6"
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        <h2 className="pr-10 text-lg font-bold text-slate-900">{t('Holatni oʻzgartirish')}</h2>
        <p className="mt-0.5 text-sm text-slate-500">{child.full_name}</p>

        {error && (
          <div role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-4 space-y-3">
          <div>
            <label htmlFor="cs-status" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Holat')} <span className="text-red-500">*</span>
            </label>
            <Select
              id="cs-status"
              value={form.enrollment_status}
              onChange={(e) =>
                setForm((p) => ({
                  ...p,
                  enrollment_status: e.target.value as Child['enrollment_status'],
                }))
              }
              className="mt-1"
            >
              {STATUS_ORDER.map((value) => (
                <option key={value} value={value}>
                  {STATUS_LABELS[value]}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label htmlFor="cs-date" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Qaysi sanadan')} <span className="text-red-500">*</span>
            </label>
            <DateInput
              id="cs-date"
              required
              max={new Date().toISOString().slice(0, 10)}
              value={form.status_changed_on}
              onChange={(iso) => setForm((p) => ({ ...p, status_changed_on: iso }))}
            />
            <p className="mt-1 text-xs text-slate-500">
              {trial
                ? t('Sinov shu kundan 3 kun davom etadi; bu kunlar uchun pul hisoblanmaydi.')
                : t('Shu sanadan keyin hisob-faktura yozilmaydi.')}
            </p>
          </div>

          {leaving && (
            <div>
              <label
                htmlFor="cs-reason-code"
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t('Nega ketdi')} <span className="text-red-500">*</span>
              </label>
              <Select
                id="cs-reason-code"
                required
                value={form.status_reason_code}
                onChange={(e) => setForm((p) => ({ ...p, status_reason_code: e.target.value }))}
                className="mt-1"
              >
                <option value="">{t('— tanlang —')}</option>
                {WITHDRAW_REASONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
              <p className="mt-1 text-xs text-slate-500">
                {t('Roʻyxat oylar boʻyicha solishtiriladi — shuning uchun u qatʼiy.')}
              </p>
            </div>
          )}

          <div>
            <label htmlFor="cs-reason" className="mb-1 block text-xs font-medium text-slate-600">
              {leaving ? t('Izoh') : t('Sabab')} <span className="text-red-500">*</span>
            </label>
            <input
              id="cs-reason"
              required
              maxLength={255}
              placeholder={
                leaving
                  ? t('Masalan: oila Samarqandga koʻchdi')
                  : t('Masalan: ota-ona bilan kelishildi')
              }
              value={form.status_reason}
              onChange={(e) => setForm((p) => ({ ...p, status_reason: e.target.value }))}
              className={field}
            />
          </div>
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="submit"
            disabled={save.isPending}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
