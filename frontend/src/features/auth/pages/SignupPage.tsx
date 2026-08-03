/**
 * Ro'yxatdan o'tish — 15 kunlik sinov (docs/01 §4.4).
 *
 * Shart taklifning O'ZIDA yozilgan, sinov oxirida emas: konvertatsiyada
 * birinchi oylik to'lov sinov boshlangan kundan hisoblanadi. Boshida
 * aytilsa — bu halol shart; keyin aytilsa — aldov.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Sparkles } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { authApi } from '@/features/auth/api'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'

export default function SignupPage() {
  const navigate = useNavigate()
  const { applySession } = useAuth()

  const [form, setForm] = useState({
    organization_name: '',
    full_name: '',
    contact_email: '',
    contact_phone: '',
    password: '',
  })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }))

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setFieldErrors({})
    setBusy(true)
    try {
      const session = await authApi.signup(form)
      applySession(session)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
        setFieldErrors(err.fieldErrors())
      } else {
        setError('Kutilmagan xatolik. Qaytadan urinib ko\'ring.')
      }
    } finally {
      setBusy(false)
    }
  }

  const field = (
    key: keyof typeof form,
    label: string,
    type = 'text',
    required = true,
    autoComplete?: string,
  ) => (
    <div>
      <label htmlFor={key} className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={key}
        type={type}
        required={required}
        autoComplete={autoComplete}
        value={form[key]}
        onChange={update(key)}
        className={cn(
          'w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2',
          fieldErrors[key]
            ? 'border-red-300 focus:border-red-400 focus:ring-red-100'
            : 'border-slate-200 focus:border-brand-500 focus:ring-brand-100',
        )}
      />
      {fieldErrors[key] && <p className="mt-1 text-xs text-red-600">{fieldErrors[key]}</p>}
    </div>
  )

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-white">
            <Building2 className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            15 kunlik risksiz sinov
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Karta kerak emas. Yoqmasa — bir so'm ham to'lamaysiz.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          {error && (
            <div role="alert" className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={submit} className="space-y-4">
            {field('organization_name', "Bog'cha nomi")}
            {field('full_name', 'Ism familiyangiz', 'text', true, 'name')}
            {field('contact_email', 'Email', 'email', true, 'username')}
            {field('contact_phone', 'Telefon', 'tel', false, 'tel')}
            {field('password', 'Parol', 'password', true, 'new-password')}

            <button
              type="submit"
              disabled={busy}
              className={cn(
                'flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition',
                busy ? 'opacity-60' : 'hover:bg-brand-700',
              )}
            >
              <Sparkles className="h-4 w-4" />
              {busy ? 'Yaratilmoqda…' : 'Sinovni boshlash'}
            </button>
          </form>

          {/* Shart BOSHIDA aytiladi — docs/01 §4.4. */}
          <p className="mt-4 border-t border-slate-100 pt-4 text-xs leading-relaxed text-slate-500">
            Sinov 15 kun davom etadi. Davom ettirishga qaror qilsangiz, birinchi oylik
            to'lov <strong className="font-semibold text-slate-600">sinov boshlangan
            kundan</strong> hisoblanadi. Davom ettirmasangiz, hech qanday to'lov olinmaydi.
          </p>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          Hisobingiz bormi?{' '}
          <a href="/login" className="font-medium text-brand-600 hover:underline">
            Kirish
          </a>
        </p>
      </div>
    </div>
  )
}
