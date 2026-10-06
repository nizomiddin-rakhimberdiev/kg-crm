/**
 * Vasiyni tahrirlash (PLAN 7.4).
 *
 * Ilgari bola kartasida vasiyning faqat ROLINI ("kim bo'ladi") va
 * "asosiy" belgisini o'zgartirish mumkin edi — ismi va telefoni esa
 * umuman tahrirlanmasdi. Raqam o'zgarsa yoki familiya xato yozilgan
 * bo'lsa, yagona yo'l vasiyni uzib, yangisini qo'shish edi; o'shanda
 * Telegram ulanishi ham, tarixi ham yo'qolardi.
 *
 * Telefon — vasiyning KIMLIGI (filial ichida unikal) va botga ulanish
 * kaliti, shuning uchun uni o'zgartirish ogohlantirish bilan boradi.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Modal } from '@/components/ui/Modal'
import { guardiansApi } from '@/features/children/api'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

interface GuardianShape {
  id: string
  first_name: string
  last_name: string
  phone: string
  phone_alt: string
  language: string
}

const field =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

export function GuardianEditDialog({
  guardian,
  onClose,
  onSaved,
}: {
  guardian: GuardianShape
  onClose: () => void
  onSaved: () => void
}) {
  const [form, setForm] = useState({
    last_name: guardian.last_name,
    first_name: guardian.first_name,
    phone: guardian.phone,
    phone_alt: guardian.phone_alt ?? '',
    language: guardian.language ?? '',
  })
  // Ikkinchi raqam maydoni faqat KERAK bo'lganda ochiladi: bo'sh input
  // formada turib olishi kerak emas (egasining so'zi).
  const [showAlt, setShowAlt] = useState(Boolean(guardian.phone_alt))
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const save = useMutation({
    mutationFn: () => guardiansApi.update(guardian.id, form),
    onSuccess: () => {
      onSaved()
      onClose()
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors())
        setError(err.message)
      } else {
        setError(t('Xatolik yuz berdi.'))
      }
    },
  })

  const phoneChanged = form.phone !== guardian.phone

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
        className="space-y-3 p-6"
      >
        <h2 className="pr-10 text-lg font-bold text-slate-900">{t('Vasiyni tahrirlash')}</h2>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label htmlFor="g-last" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Familiya')}
            </label>
            <input
              id="g-last"
              value={form.last_name}
              onChange={(e) => setForm((p) => ({ ...p, last_name: e.target.value }))}
              className={field}
            />
          </div>
          <div>
            <label htmlFor="g-first" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Ism')}
            </label>
            <input
              id="g-first"
              value={form.first_name}
              onChange={(e) => setForm((p) => ({ ...p, first_name: e.target.value }))}
              className={field}
            />
          </div>
        </div>

        <div>
          <label htmlFor="g-phone" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Telefon')}
          </label>
          <input
            id="g-phone"
            required
            type="tel"
            value={form.phone}
            onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))}
            className={field}
          />
          {fieldErrors.phone && <p className="mt-1 text-xs text-red-600">{fieldErrors.phone}</p>}
          {phoneChanged && (
            <p className="mt-1 text-xs text-orik-700">
              {t('Raqam oʻzgarsa, Telegram ulanishi va xabarlar shu yangi raqamga bogʻlanadi.')}
            </p>
          )}
        </div>

        {showAlt ? (
          <div>
            <label htmlFor="g-phone-alt" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Ikkinchi raqam')}
            </label>
            <input
              id="g-phone-alt"
              type="tel"
              placeholder="+998 90 123 45 67"
              value={form.phone_alt}
              onChange={(e) => setForm((p) => ({ ...p, phone_alt: e.target.value }))}
              className={field}
            />
            {fieldErrors.phone_alt && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.phone_alt}</p>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowAlt(true)}
            className="text-sm font-medium text-brand-600 hover:underline"
          >
            {t('+ Ikkinchi raqam')}
          </button>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="submit"
            disabled={save.isPending}
            className={cn(
              'rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white',
              save.isPending ? 'opacity-60' : 'hover:bg-brand-700',
            )}
          >
            {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
