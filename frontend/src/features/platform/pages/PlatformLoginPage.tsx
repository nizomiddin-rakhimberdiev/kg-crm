/**
 * Vendor kirishi — email + parol + TOTP (ADR-10).
 *
 * Mijoz login sahifasidan ko'rinishi bilan ham farq qiladi: qorong'i
 * fon va boshqa sarlavha. Bu bezak emas — ikki tekislikni ADASHTIRISH
 * xavfli, va vizual farq buni bir qarashda hal qiladi.
 */

import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { ApiError } from '@/lib/api/types'
import { usePlatformAuth } from '../PlatformAuthProvider'

export default function PlatformLoginPage() {
  const navigate = useNavigate()
  const { login, isAuthenticated } = usePlatformAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (isAuthenticated) return <Navigate to="/platform" replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email.trim(), password, code.trim())
      navigate('/platform', { replace: true })
    } catch (err) {
      // Backend qaysi omil noto'g'ri ekanini AYTMAYDI va biz ham
      // aytmaymiz: bu farq hujumchiga qaysi bosqichda ekanini bildirardi.
      setError(err instanceof ApiError ? err.message : 'Kirish amalga oshmadi.')
    } finally {
      setBusy(false)
    }
  }

  const field =
    'w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-100 ' +
    'placeholder:text-slate-500 outline-none focus:border-brand-500'

  return (
    <div className="grid min-h-screen place-items-center bg-slate-900 px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4">
        <div className="mb-6 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-brand-600">
            <ShieldCheck className="h-6 w-6 text-white" />
          </div>
          <h1 className="mt-4 text-xl font-bold text-white">KG-CRM — Platforma konsoli</h1>
          <p className="mt-1 text-sm text-slate-400">
            Faqat vendor xodimlari uchun. Bog'cha hisobingiz bu yerda ishlamaydi.
          </p>
        </div>

        {error && (
          <div role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        <div>
          <label htmlFor="p-email" className="mb-1 block text-xs font-medium text-slate-400">
            Email
          </label>
          <input
            id="p-email"
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={field}
          />
        </div>

        <div>
          <label htmlFor="p-password" className="mb-1 block text-xs font-medium text-slate-400">
            Parol
          </label>
          <input
            id="p-password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={field}
          />
        </div>

        <div>
          <label htmlFor="p-code" className="mb-1 block text-xs font-medium text-slate-400">
            Authenticator kodi
          </label>
          <input
            id="p-code"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={6}
            required
            autoComplete="one-time-code"
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            className={`${field} text-center font-mono text-lg tracking-[0.4em]`}
          />
          <p className="mt-1 text-xs text-slate-500">
            Ikki bosqichli tasdiqlash majburiy — usiz kirish mumkin emas.
          </p>
        </div>

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {busy ? 'Tekshirilmoqda…' : 'Kirish'}
        </button>
      </form>
    </div>
  )
}
