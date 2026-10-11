/**
 * Taklif havolasi — yangi bogʻcha egasi parolini OʻZI oʻrnatadi
 * (PLAN 5.5).
 *
 * Tiklash sahifasidan farqi kichik, lekin maʼnosi boshqa: bu odam
 * tizimni birinchi marta ochadi. Shuning uchun matn ham boshqa —
 * "yangi parol" emas, "parol yarating", va muvaffaqiyatdan keyin
 * uni darhol kirishga olib boradi.
 *
 * Token oldindan TEKSHIRILMAYDI: tekshirish uchun alohida endpoint
 * "bu token haqiqiymi?" degan savolga javob beradigan orakul boʻlib
 * qolardi. Eskirgan havola parol yuborilgandan keyin bitta tushunarli
 * xabar bilan rad etiladi.
 */

import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle2, KeyRound } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'
import { PasswordInput } from '@/components/ui/PasswordInput'
import { authApi } from '@/features/auth/api'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { MIN_PASSWORD_LENGTH, passwordTooShort } from '@/lib/password'
import { t } from '@/lib/i18n'

export default function InvitePage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mismatch = repeat.length > 0 && password !== repeat
  // Server 12 belgini talab qiladi. Buni EKRANDA aytmaslik —
  // odamni tushunarsiz server xatosiga yuborish degani.
  const tooShort = passwordTooShort(password)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (mismatch) return
    setBusy(true)
    setError(null)
    try {
      await authApi.acceptInvite(token, password)
      setDone(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-sut px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo height={40} />
          <p className="mt-3 text-sm text-tosh-500">{t('Bogʻchangiz tayyor')}</p>
        </div>

        <div className="rounded-2xl border border-tosh-200 bg-white p-6 shadow-card">
          {done ? (
            <div className="space-y-4 text-center">
              <CheckCircle2 className="mx-auto h-9 w-9 text-nihol-600" />
              <p className="text-sm text-tosh-700">
                {t('Parol oʻrnatildi. Endi kirishingiz mumkin.')}
              </p>
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="w-full rounded-lg bg-nihol-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-nihol-700"
              >
                {t('Kirish')}
              </button>
            </div>
          ) : !token ? (
            <div className="space-y-3 text-center">
              <p className="text-sm text-tosh-700">
                {t('Havola toʻliq emas. Pochtadagi havolani toʻliq nusxalab oching.')}
              </p>
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="text-sm text-tosh-500 hover:text-tosh-700"
              >
                {t('Kirishga qaytish')}
              </button>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              {error && (
                <div role="alert" className="rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-900">
                  {error}
                </div>
              )}

              {/* Parolni BIZ bermaganimiz — ataylab, va buni aytib
                  qoʻyish kerak: mijoz "parolni qayerdan olaman?"
                  degan savol bilan qoʻngʻiroq qilmasligi uchun. */}
              <p className="text-sm text-tosh-600">
                {t('Parolni oʻzingiz yaratasiz — biz uni bilmaymiz va hech qachon soʻramaymiz.')}
              </p>

              <div>
                <label
                  htmlFor="invite-password"
                  className="mb-1 block text-sm font-medium text-tosh-700"
                >
                  {t('Parol')}
                </label>
                <PasswordInput
                  id="invite-password"
                  required
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>

              <p className={tooShort ? 'text-xs text-orik-700' : 'text-xs text-tosh-500'}>
                {t('Kamida {MIN_PASSWORD_LENGTH} belgi.', { MIN_PASSWORD_LENGTH })}
              </p>
              <div>
                <label
                  htmlFor="invite-repeat"
                  className="mb-1 block text-sm font-medium text-tosh-700"
                >
                  {t('Parolni takrorlang')}
                </label>
                <PasswordInput
                  id="invite-repeat"
                  required
                  autoComplete="new-password"
                  value={repeat}
                  onChange={(event) => setRepeat(event.target.value)}
                />
                {mismatch && (
                  <p className="mt-1 text-xs text-orik-800">{t('Parollar mos kelmadi.')}</p>
                )}
              </div>

              <button
                type="submit"
                disabled={busy || mismatch || tooShort || password.length === 0}
                className={cn(
                  'flex w-full items-center justify-center gap-2 rounded-lg bg-nihol-600 px-4 py-2.5 text-sm font-semibold text-white transition',
                  busy || mismatch || tooShort || !password ? 'opacity-60' : 'hover:bg-nihol-700',
                )}
              >
                <KeyRound className="h-4 w-4" />
                {busy ? t('Saqlanmoqda…') : t('Parolni oʻrnatish')}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
