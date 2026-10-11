/**
 * Self-signup — the e-mailed link (PLAN 6.7). Setting the password is
 * what creates the kindergarten; then the owner signs in as usual.
 */

import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle2, KeyRound } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'
import { PasswordInput } from '@/components/ui/PasswordInput'
import { signupApi } from '@/features/signup/api'
import { ApiError } from '@/lib/api/types'
import { MIN_PASSWORD_LENGTH, passwordTooShort } from '@/lib/password'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

export default function SignupConfirmPage() {
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
      await signupApi.confirm(token, password)
      setDone(true)
    } catch (err) {
      if (err instanceof ApiError) {
        const fields = err.fieldErrors()
        setError(fields.password ?? err.message)
      } else {
        setError(t('Xatolik yuz berdi.'))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-sut px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center">
          <Logo height={40} />
        </div>
        <div className="rounded-2xl border border-tosh-200 bg-white p-6 shadow-card">
          {done ? (
            <div className="space-y-4 text-center">
              <CheckCircle2 className="mx-auto h-9 w-9 text-nihol-600" />
              <p className="text-sm text-tosh-700">
                {t('Bogʻchangiz ochildi — 15 kunlik sinov boshlandi. Endi kiring.')}
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
            <p className="text-center text-sm text-tosh-700">
              {t('Havola toʻliq emas. Pochtadagi havolani toʻliq nusxalab oching.')}
            </p>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <h1 className="text-lg font-semibold text-tosh-900">{t('Parol oʻrnating')}</h1>
              {error && (
                <div role="alert" className="rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-900">
                  {error}
                </div>
              )}
              <div>
                <label
                  htmlFor="signup-password"
                  className="mb-1 block text-sm font-medium text-tosh-700"
                >
                  {t('Parol')}
                </label>
                <PasswordInput
                  id="signup-password"
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
                  htmlFor="signup-repeat"
                  className="mb-1 block text-sm font-medium text-tosh-700"
                >
                  {t('Parolni takrorlang')}
                </label>
                <PasswordInput
                  id="signup-repeat"
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
                disabled={busy || mismatch || tooShort || !password}
                className={cn(
                  'flex w-full items-center justify-center gap-2 rounded-lg bg-nihol-600 px-4 py-2.5 text-sm font-semibold text-white',
                  busy || mismatch || tooShort || !password ? 'opacity-60' : 'hover:bg-nihol-700',
                )}
              >
                <KeyRound className="h-4 w-4" />
                {busy ? t('Saqlanmoqda…') : t('Bogʻchani ochish')}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
