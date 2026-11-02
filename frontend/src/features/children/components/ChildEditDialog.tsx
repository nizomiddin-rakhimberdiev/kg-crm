/**
 * Bola ma'lumotini tahrirlash (PLAN 2.1).
 *
 * Auditda bola kartasida tahrirlash umuman yo'q edi: noto'g'ri yozilgan
 * ismni tuzatishning yagona yo'li bolani qaytadan kiritish bo'lardi —
 * va o'shanda uning balansi, davomati va tarixi eski yozuvda qolardi.
 *
 * Tibbiy ma'lumot shu yerda, umumiy izohdan ALOHIDA: allergiya
 * oshxonaga va tarbiyachiga kerak bo'ladigan ma'lumot, va uni erkin
 * matn ichidan qidirish — xato qilish uchun eng qulay joy.
 */

import { useState } from 'react'
import { today } from '@/lib/format'
import { HEARD_FROM } from '@/features/children/heardFrom'
import { useMutation } from '@tanstack/react-query'
import { DateInput } from '@/components/ui/DateInput'
import { Modal } from '@/components/ui/Modal'
import { childrenApi } from '@/features/children/api'
import { ApiError, type Child } from '@/lib/api/types'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'

export function ChildEditDialog({
  child,
  onClose,
  onDone,
}: {
  child: Child
  onClose: () => void
  onDone: () => void
}) {
  const [form, setForm] = useState({
    last_name: child.last_name,
    first_name: child.first_name,
    middle_name: child.middle_name,
    date_of_birth: child.date_of_birth,
    gender: child.gender,
    enrolled_on: child.enrolled_on ?? '',
    allergies: child.allergies ?? '',
    medical_notes: child.medical_notes ?? '',
    notes: child.notes ?? '',
    heard_from: child.heard_from ?? '',
    heard_from_note: child.heard_from_note ?? '',
  })
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () =>
      childrenApi.update(child.id, {
        ...form,
        enrolled_on: form.enrolled_on || null,
      }),
    onSuccess: () => {
      onDone()
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const field =
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'
  const label = 'mb-1 block text-xs font-medium text-slate-600'
  const required = <span className="text-red-500">*</span>

  return (
    <Modal open onClose={onClose} className="max-w-lg">
      <form
        className="p-6"
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        <h2 className="pr-10 text-lg font-bold text-slate-900">{t('Maʼlumotni tahrirlash')}</h2>

        {error && (
          <div role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="ce-last" className={label}>
              {t('Familiya')} {required}
            </label>
            <input
              id="ce-last"
              required
              value={form.last_name}
              onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="ce-first" className={label}>
              {t('Ism')} {required}
            </label>
            <input
              id="ce-first"
              required
              value={form.first_name}
              onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))}
              className={field}
            />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="ce-middle" className={label}>
              {t('Otasining ismi')}
            </label>
            <input
              id="ce-middle"
              value={form.middle_name}
              onChange={(e) => setForm((p) => ({ ...p, middle_name: e.target.value }))}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="ce-dob" className={label}>
              {t('Tugʻilgan sana')} {required}
            </label>
            <DateInput
              id="ce-dob"
              required
              max={today()}
              value={form.date_of_birth}
              onChange={(iso) => setForm((p) => ({ ...p, date_of_birth: iso }))}
            />
          </div>
          <div>
            <label htmlFor="ce-gender" className={label}>
              {t('Jinsi')} {required}
            </label>
            <Select
              id="ce-gender"
              value={form.gender}
              onChange={(e) =>
                setForm((p) => ({ ...p, gender: e.target.value as Child['gender'] }))
              }
              className="mt-1"
            >
              <option value="male">{t('Oʻgʻil bola')}</option>
              <option value="female">{t('Qiz bola')}</option>
            </Select>
          </div>
          <div>
            <label htmlFor="ce-heard" className={label}>
              {t('Bizni qayerdan eshitgan?')}
            </label>
            <Select
              id="ce-heard"
              value={form.heard_from}
              onChange={(e) => setForm((p) => ({ ...p, heard_from: e.target.value }))}
              className="mt-1"
            >
              <option value="">{t('Koʻrsatilmagan')}</option>
              {HEARD_FROM.map(([value, text]) => (
                <option key={value} value={value}>
                  {text}
                </option>
              ))}
            </Select>
          </div>
          {form.heard_from === 'other' && (
            <div>
              <label htmlFor="ce-heard-note" className={label}>
                {t('Qayerdan — aniqroq')}
              </label>
              <input
                id="ce-heard-note"
                maxLength={120}
                value={form.heard_from_note}
                onChange={(e) => setForm((p) => ({ ...p, heard_from_note: e.target.value }))}
                className={field}
              />
            </div>
          )}
          <div className="sm:col-span-2">
            <label htmlFor="ce-enrolled" className={label}>
              {t('Qabul sanasi')}
            </label>
            <DateInput
              id="ce-enrolled"
              value={form.enrolled_on}
              onChange={(iso) => setForm((p) => ({ ...p, enrolled_on: iso }))}
            />
            <p className="mt-1 text-xs text-slate-500">
              {t('Birinchi hisob-faktura shu sanadan proporsional hisoblanadi.')}
            </p>
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="ce-allergies" className={label}>
              {t('Allergiya')}
            </label>
            <input
              id="ce-allergies"
              maxLength={255}
              placeholder={t('Masalan: yongʻoq, asal')}
              value={form.allergies}
              onChange={(e) => setForm((p) => ({ ...p, allergies: e.target.value }))}
              className={field}
            />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="ce-medical" className={label}>
              {t('Tibbiy izoh')}
            </label>
            <textarea
              id="ce-medical"
              rows={2}
              value={form.medical_notes}
              onChange={(e) => setForm((p) => ({ ...p, medical_notes: e.target.value }))}
              className={field}
            />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="ce-notes" className={label}>
              {t('Izoh')}
            </label>
            <textarea
              id="ce-notes"
              rows={2}
              value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
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
