/**
 * Yangi parol oʻrnatish — email havolasidan ochiladi (PLAN 5.2).
 *
 * Havolada `uid` va `token`. Ularni TEKSHIRMAY turib forma
 * koʻrsatiladi: tokenni oldindan tekshirish uchun alohida endpoint
 * kerak boʻlardi, va u "bu token haqiqiymi?" degan savolga javob
 * beradigan orakul boʻlib qolardi. Xato havola parol yuborilgandan
 * keyin bitta tushunarli xabar bilan rad etiladi.
 */

import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle2, KeyRound } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'
import { PasswordInput } from '@/components/ui/PasswordInput'
import { authApi } from '@/features/auth/api'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const uid = params.get('uid') ?? ''
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [repeat, setRepeat] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mismatch = repeat.length > 0 && password !== repeat

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (mismatch) return
    setBusy(true)
    setError(null)
    try {
      await authApi.confirmPasswordReset(uid, token, password)
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
          <p className="mt-3 text-sm text-tosh-500">{t('Yangi parol oʻrnatish')}</p>
        </div>

        <div className="rounded-2xl border border-tosh-200 bg-white p-6 shadow-card">
          {done ? (
            <div className="space-y-4 text-center">
              <CheckCircle2 className="mx-auto h-9 w-9 text-nihol-600" />
              <p className="text-sm text-tosh-700">
                {t('Parol oʻzgartirildi. Endi kirishingiz mumkin.')}
              </p>
              {/* Barcha sessiyalar YOPILDI — boshqa qurilmadagi
                  kirish ham tugadi, va bu ataylab: hisob
                  oʻgʻirlangan boʻlsa parolni almashtirishning butun
                  maʼnosi shu. */}
              <p className="text-xs text-tosh-500">
                {t('Barcha qurilmalardagi sessiyalar yopildi.')}
              </p>
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="w-full rounded-lg bg-nihol-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-nihol-700"
              >
                {t('Kirish')}
              </button>
            </div>
          ) : !uid || !token ? (
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

              <div>
                <label
                  htmlFor="new-password"
                  className="mb-1 block text-sm font-medium text-tosh-700"
                >
                  {t('Yangi parol')}
                </label>
                <PasswordInput
                  id="new-password"
                  required
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </div>

              <div>
                <label
                  htmlFor="repeat-password"
                  className="mb-1 block text-sm font-medium text-tosh-700"
                >
                  {t('Parolni takrorlang')}
                </label>
                <PasswordInput
                  id="repeat-password"
                  required
                  autoComplete="new-password"
                  value={repeat}
                  onChange={(event) => setRepeat(event.target.value)}
                />
                {/* Takrorlash maydoni — yangi parol uchun. Xato
                    terilgan parol hisobga kirish imkonini
                    YOʻQOTADI, va buni faqat keyingi kirishda
                    bilish juda qimmat. */}
                {mismatch && (
                  <p className="mt-1 text-xs text-orik-800">{t('Parollar mos kelmadi.')}</p>
                )}
              </div>

              <button
                type="submit"
                disabled={busy || mismatch || password.length === 0}
                className={cn(
                  'flex w-full items-center justify-center gap-2 rounded-lg bg-nihol-600 px-4 py-2.5 text-sm font-semibold text-white transition',
                  busy || mismatch || !password ? 'opacity-60' : 'hover:bg-nihol-700',
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
