/**
 * Profil — foydalanuvchining o'zi haqidagi sahifa (docs/04 §5).
 *
 * Bu yerda ruxsat tekshiruvi yo'q va bo'lmasligi ham kerak: har bir
 * autentifikatsiyalangan foydalanuvchi o'z ma'lumotini ko'radi va o'z parolini
 * almashtiradi. `/auth/me` va `/auth/password/change` — ikkalasi ham faqat
 * so'rov egasining o'ziga tegishli.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Camera, KeyRound, ShieldCheck } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { Avatar } from '@/components/ui/Avatar'
import { authApi } from '@/features/auth/api'
import { PasswordInput } from '@/components/ui/PasswordInput'
import { TwoFactorCard } from '@/features/auth/components/TwoFactorCard'
import { subscriptionStatusLabel } from '@/features/billing/status'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const MIN_PASSWORD_LENGTH = 10

export default function ProfilePage() {
  const { user, subscription, refreshUser } = useAuth()

  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [phone, setPhone] = useState(user?.phone ?? '')
  const [profileErrors, setProfileErrors] = useState<Record<string, string>>({})
  const [profileSaved, setProfileSaved] = useState(false)

  const saveProfile = useMutation({
    mutationFn: () => authApi.updateProfile({ full_name: fullName, phone }),
    onSuccess: async () => {
      setProfileErrors({})
      setProfileSaved(true)
      // Ism yuqori panelda ham turadi — kontekstni yangilaymiz.
      await refreshUser()
    },
    onError: (err) => {
      setProfileSaved(false)
      setProfileErrors(err instanceof ApiError ? err.fieldErrors() : {})
    },
  })

  const [photoError, setPhotoError] = useState<string | null>(null)

  const photo = useMutation({
    mutationFn: (file: File) => authApi.uploadPhoto(file),
    onSuccess: async () => {
      setPhotoError(null)
      await refreshUser()
    },
    onError: (err) =>
      setPhotoError(
        err instanceof ApiError
          ? (err.fieldErrors().photo ?? err.message)
          : t('Rasmni yuklab boʻlmadi.'),
      ),
  })

  const removePhoto = useMutation({
    mutationFn: () => authApi.removePhoto(),
    onSuccess: async () => {
      setPhotoError(null)
      await refreshUser()
    },
    onError: () => setPhotoError(t('Rasmni oʻchirib boʻlmadi.')),
  })

  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [repeat, setRepeat] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [done, setDone] = useState(false)

  const changePassword = useMutation({
    mutationFn: () => authApi.changePassword(current, next),
    onSuccess: () => {
      setCurrent('')
      setNext('')
      setRepeat('')
      setError(null)
      setFieldErrors({})
      setDone(true)
    },
    onError: (err) => {
      setDone(false)
      if (err instanceof ApiError) {
        setError(err.message)
        setFieldErrors(err.fieldErrors())
      } else {
        setError(t('Parolni almashtirib boʻlmadi.'))
      }
    },
  })

  if (!user) return null

  const mismatch = repeat.length > 0 && next !== repeat
  const tooShort = next.length > 0 && next.length < MIN_PASSWORD_LENGTH
  const canSubmit = current.length > 0 && next.length >= MIN_PASSWORD_LENGTH && next === repeat

  const rows: [string, string][] = [
    [t('Email'), user.email],
    [t('Rol'), user.role?.name ?? '—'],
    [t('Filial'), user.branch?.name ?? t('Barcha filiallar')],
    [t('Tashkilot'), user.organization?.name ?? '—'],
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Profil')}</h1>
        <p className="mt-1 text-sm text-slate-500">{t('Hisobingiz maʼlumotlari va xavfsizlik.')}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* --- Ma'lumotlar --- */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Avatar
                name={user.full_name}
                photoUrl={user.photo_url}
                className="h-16 w-16"
                textClassName="text-lg"
              />
              <label
                title={t('Rasm yuklash')}
                className="absolute -bottom-1 -right-1 grid h-7 w-7 cursor-pointer place-items-center rounded-full border-2 border-white bg-brand-600 text-white shadow transition hover:bg-brand-700"
              >
                <Camera className="h-3.5 w-3.5" />
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="hidden"
                  disabled={photo.isPending}
                  onChange={(event) => {
                    const file = event.target.files?.[0]
                    // Input qiymati tozalanadi: bir xil faylni ikkinchi marta
                    // tanlaganda ham `change` hodisasi ishlashi kerak.
                    event.target.value = ''
                    if (file) photo.mutate(file)
                  }}
                />
              </label>
            </div>

            <div className="min-w-0">
              <p className="truncate font-semibold text-slate-900">{user.full_name}</p>
              <p className="text-sm text-slate-500">{user.role?.name ?? '—'}</p>
              <div className="mt-1 flex items-center gap-2 text-xs">
                {photo.isPending && <span className="text-slate-400">{t('Yuklanmoqda…')}</span>}
                {!photo.isPending && user.photo_url && (
                  <button
                    type="button"
                    onClick={() => removePhoto.mutate()}
                    className="text-slate-400 transition hover:text-red-600"
                  >
                    {t('Rasmni olib tashlash')}
                  </button>
                )}
                {!photo.isPending && !user.photo_url && (
                  <span className="text-slate-400">{t('JPG, PNG yoki WEBP — 2 MB gacha')}</span>
                )}
              </div>
              {photoError && <p className="mt-1 text-xs text-red-600">{photoError}</p>}
            </div>
          </div>

          <form
            className="mt-5 space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              saveProfile.mutate()
            }}
          >
            {(
              [
                ['full_name', t('Ism familiya'), fullName, setFullName],
                ['phone', t('Telefon'), phone, setPhone],
              ] as const
            ).map(([key, label, value, setValue]) => (
              <div key={key}>
                <label htmlFor={key} className="mb-1 block text-xs font-medium text-slate-600">
                  {label}
                </label>
                <input
                  id={key}
                  type={key === 'phone' ? 'tel' : 'text'}
                  value={value}
                  onChange={(e) => {
                    setValue(e.target.value)
                    setProfileSaved(false)
                  }}
                  className={cn(
                    'w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2',
                    profileErrors[key]
                      ? 'border-red-300 focus:ring-red-100'
                      : 'border-slate-200 focus:border-brand-500 focus:ring-brand-100',
                  )}
                />
                {profileErrors[key] && (
                  <p className="mt-1 text-xs text-red-600">{profileErrors[key]}</p>
                )}
              </div>
            ))}

            {profileSaved && (
              <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                {t('Saqlandi.')}
              </div>
            )}

            <button
              type="submit"
              disabled={!fullName.trim() || saveProfile.isPending}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              {saveProfile.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
            </button>
          </form>

          <dl className="mt-5 space-y-2 text-sm">
            {rows.map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between gap-4 border-t border-slate-100 pt-2"
              >
                <dt className="text-slate-500">{label}</dt>
                <dd className="text-right font-medium text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-5 flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-500">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
            <p>
              {t('Email, rol va filialni tashkilot egasi')} <strong>{t('Xodimlar')}</strong>{' '}
              {t(
                'boʻlimida oʻzgartiradi — ular imtiyoz chegarasi, shuning uchun oʻz-oʻzini tahrirlash yoʻlidan oʻtmaydi.',
              )}
            </p>
          </div>
        </div>

        {/* --- Ikki bosqichli tasdiqlash (PLAN 5.4) --- */}
        <TwoFactorCard />

        {/* --- Parol --- */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-slate-400" />
            <h2 className="text-sm font-semibold text-slate-900">{t('Parolni almashtirish')}</h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t('Parol almashgach, boshqa qurilmalardagi seanslar bekor qilinadi.')}
          </p>

          <form
            className="mt-4 space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              changePassword.mutate()
            }}
          >
            {(
              [
                ['current', t('Joriy parol'), current, setCurrent],
                [
                  'new',
                  t('Yangi parol (kamida {MIN_PASSWORD_LENGTH} belgi)', { MIN_PASSWORD_LENGTH }),
                  next,
                  setNext,
                ],
                ['repeat', t('Yangi parolni takrorlang'), repeat, setRepeat],
              ] as const
            ).map(([key, label, value, setValue]) => (
              <div key={key}>
                <label htmlFor={key} className="mb-1 block text-xs font-medium text-slate-600">
                  {label}
                </label>
                {/* Koʻrsatish tugmasi bilan (PLAN 5.2): kuchli
                    parol uzun va aralash belgili, mobil
                    klaviaturada uni xato terish oson. */}
                <PasswordInput
                  id={key}
                  autoComplete={key === 'current' ? 'current-password' : 'new-password'}
                  value={value}
                  onChange={(e) => {
                    setValue(e.target.value)
                    setDone(false)
                  }}
                  className={cn(
                    fieldErrors[key === 'current' ? 'current_password' : 'new_password'] &&
                      'border-orik-400',
                  )}
                />
              </div>
            ))}

            {fieldErrors.current_password && (
              <p className="text-xs text-red-600">{fieldErrors.current_password}</p>
            )}
            {fieldErrors.new_password && (
              <p className="text-xs text-red-600">{fieldErrors.new_password}</p>
            )}
            {tooShort && (
              <p className="text-xs text-amber-600">
                {t('Yangi parol kamida {MIN_PASSWORD_LENGTH} belgidan iborat boʻlsin.', {
                  MIN_PASSWORD_LENGTH,
                })}
              </p>
            )}
            {mismatch && <p className="text-xs text-amber-600">{t('Parollar mos kelmadi.')}</p>}
            {error && (
              <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}
            {done && (
              <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                {t('Parol almashtirildi.')}
              </div>
            )}

            <button
              type="submit"
              disabled={!canSubmit || changePassword.isPending}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              {changePassword.isPending ? t('Saqlanmoqda…') : t('Almashtirish')}
            </button>
          </form>

          {subscription && (
            <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">
              {/* XOM holat emas (PLAN 4.3): "past_due" foydalanuvchiga
                  na tushunarli, na nima qilish kerakligini aytadi. */}
              {subscriptionStatusLabel(subscription.status)}
              {subscription.read_only && t(' — hozircha faqat oʻqish rejimi')}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
