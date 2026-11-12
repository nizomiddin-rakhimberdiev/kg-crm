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
 *
 * To'liq tahrirlash (mijoz so'rovi, 2026-10-14): oyna endi vasiyning
 * O'ZINI (ism, raqamlar, email, xabar tili) ham, uning SHU BOLA bilan
 * bog'lanishini (kim bo'ladi, asosiy vasiymi, bolani olib keta oladimi)
 * ham o'zgartiradi, va bog'lanishni uzish ham shu yerda. Ikki xil
 * yozuv, ikki xil endpoint: vasiy bir necha bolaga bog'langan bo'lishi
 * mumkin, "otasi" esa faqat shu bola uchun.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Modal } from '@/components/ui/Modal'
import { childrenApi, guardiansApi } from '@/features/children/api'
import { RELATIONS } from '@/features/children/relations'
import { ApiError, type GuardianLink } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

const LANGUAGES: Array<[string, string]> = [
  ['', t('Bogʻcha tili (sukut)')],
  ['uz', 'Oʻzbekcha'],
  ['ru', 'Русский'],
  ['en', 'English'],
]

const field =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100'

export function GuardianEditDialog({
  childId,
  link,
  onClose,
  onSaved,
}: {
  childId: string
  link: GuardianLink
  onClose: () => void
  onSaved: () => void
}) {
  const guardian = link.guardian
  const [form, setForm] = useState({
    last_name: guardian.last_name,
    first_name: guardian.first_name,
    phone: guardian.phone,
    phone_alt: guardian.phone_alt ?? '',
    email: guardian.email ?? '',
    language: guardian.language ?? '',
  })
  const [relation, setRelation] = useState({
    relation: link.relation,
    is_primary: link.is_primary,
    can_pickup: link.can_pickup,
  })
  // Ikkinchi raqam maydoni faqat KERAK bo'lganda ochiladi: bo'sh input
  // formada turib olishi kerak emas (egasining so'zi).
  const [showAlt, setShowAlt] = useState(Boolean(guardian.phone_alt))
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const save = useMutation({
    // Avval vasiyning o'zi, keyin bog'lanish: telefon xato bo'lsa
    // (PhoneField) bog'lanish yarim saqlangan holda qolmaydi.
    mutationFn: async () => {
      await guardiansApi.update(guardian.id, form)
      const linkChanged =
        relation.relation !== link.relation ||
        relation.is_primary !== link.is_primary ||
        relation.can_pickup !== link.can_pickup
      if (linkChanged) await childrenApi.updateGuardianLink(childId, link.id, relation)
    },
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

  const [askUnlink, setAskUnlink] = useState(false)
  const unlink = useMutation({
    mutationFn: () => childrenApi.unlinkGuardian(childId, link.id),
    onSuccess: () => {
      onSaved()
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
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

        <div>
          <label htmlFor="g-relation" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Bolaga kim boʻladi')}
          </label>
          <Select
            id="g-relation"
            value={relation.relation}
            onChange={(e) => setRelation((p) => ({ ...p, relation: e.target.value }))}
            className="mt-1"
          >
            {RELATIONS.map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </Select>
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

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label htmlFor="g-email" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Email')}
            </label>
            <input
              id="g-email"
              type="email"
              value={form.email}
              onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
              className={field}
            />
            {fieldErrors.email && <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>}
          </div>
          <div>
            <label htmlFor="g-lang" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Xabar tili')}
            </label>
            <Select
              id="g-lang"
              value={form.language}
              onChange={(e) => setForm((p) => ({ ...p, language: e.target.value }))}
              className="mt-1"
            >
              {LANGUAGES.map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="space-y-2 rounded-lg bg-slate-50 px-3 py-2.5">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={relation.is_primary}
              onChange={(e) => setRelation((p) => ({ ...p, is_primary: e.target.checked }))}
              className="h-4 w-4 rounded border-slate-300 focus-visible:ring-2 focus-visible:ring-brand-500"
            />
            {t('Asosiy vasiy — qoʻngʻiroq va xabarlar shunga')}
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={relation.can_pickup}
              onChange={(e) => setRelation((p) => ({ ...p, can_pickup: e.target.checked }))}
              className="h-4 w-4 rounded border-slate-300 focus-visible:ring-2 focus-visible:ring-brand-500"
            />
            {t('Bolani olib keta oladi')}
          </label>
        </div>

        <div className="flex items-center justify-between gap-2 pt-1">
          <button
            type="button"
            disabled={unlink.isPending}
            onClick={() => setAskUnlink(true)}
            className="rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-60"
          >
            {t('Bogʻlanishni uzish')}
          </button>
          <div className="flex gap-2">
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
        </div>
      </form>
      <ConfirmDialog
        open={askUnlink}
        title={t('Bogʻlanishni uzish')}
        body={t('{name} bu boladan uzilsinmi?', { name: guardian.full_name })}
        confirmLabel={t('Uzish')}
        tone="danger"
        busy={unlink.isPending}
        onConfirm={() => {
          setAskUnlink(false)
          unlink.mutate()
        }}
        onCancel={() => setAskUnlink(false)}
      />
    </Modal>
  )
}
