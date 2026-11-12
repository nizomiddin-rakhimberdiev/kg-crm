/**
 * Self-signup — the form (PLAN 6.7, ADR-28).
 *
 * Nothing is created here but a request: the kindergarten appears only
 * when the owner opens the e-mailed link and sets a password. The answer
 * is the same whatever the server knows about the address, so the page
 * always says "check your e-mail".
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MailCheck } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'
import { LanguageSwitch } from '@/components/layout/LanguageSwitch'
import { POLICY_VERSION } from '@/features/marketing/legal'
import { signupApi } from '@/features/signup/api'
import { ApiError } from '@/lib/api/types'
import { locale, t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

const field =
  'w-full rounded-lg border border-tosh-200 px-3 py-2 text-sm outline-none focus:border-nihol-500'

export default function SignupPage() {
  const [form, setForm] = useState({
    kindergarten_name: '',
    name: '',
    email: '',
    phone: '',
    city: '',
    children_count: '',
    consent: false,
    website: '',
  })
  const [submissionId] = useState(() => crypto.randomUUID())
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Maydon xatosi — o'sha maydon ostida (audit 2026-11-12, J5): umumiy
  // xabar tepada turib, qaysi maydon ekanini aytmasdi.
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const set = (patch: Partial<typeof form>) => setForm((prev) => ({ ...prev, ...patch }))

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setFieldErrors({})
    try {
      await signupApi.request({
        ...form,
        children_count: Number(form.children_count) || 0,
        language: locale,
        privacy_policy_version: POLICY_VERSION,
        submission_id: submissionId,
      })
      setSent(true)
    } catch (err) {
      const fields = err instanceof ApiError ? err.fieldErrors() : {}
      const known = Object.keys(fields).filter((key) => key in form)
      setFieldErrors(Object.fromEntries(known.map((key) => [key, fields[key]])))
      // Umumiy xabar faqat maydonga bog'lanmagan xato uchun.
      if (known.length === 0) {
        setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))
      }
    } finally {
      setBusy(false)
    }
  }

  const input = (
    id: keyof typeof form,
    label: string,
    props: React.InputHTMLAttributes<HTMLInputElement> = {},
  ) => (
    <div>
      <label htmlFor={`signup-${id}`} className="mb-1 block text-sm font-medium text-tosh-700">
        {label}
      </label>
      <input
        id={`signup-${id}`}
        required
        value={String(form[id])}
        onChange={(event) => set({ [id]: event.target.value } as Partial<typeof form>)}
        aria-invalid={fieldErrors[id] ? true : undefined}
        aria-describedby={fieldErrors[id] ? `signup-${id}-error` : undefined}
        className={field}
        {...props}
      />
      {fieldErrors[id] && (
        <p id={`signup-${id}-error`} className="mt-1 text-sm text-orik-900">
          {fieldErrors[id]}
        </p>
      )}
    </div>
  )

  return (
    <div className="flex min-h-screen flex-col items-center bg-sut px-4 py-8">
      <div className="flex w-full max-w-md items-center justify-between">
        <Logo height={36} />
        <LanguageSwitch />
      </div>
      <main className="mt-8 w-full max-w-md rounded-2xl border border-tosh-200 bg-white p-6 shadow-card">
        {sent ? (
          <div className="space-y-3 text-center">
            <MailCheck className="mx-auto h-9 w-9 text-nihol-600" />
            <h1 className="text-lg font-semibold text-tosh-900">{t('Pochtangizni tekshiring')}</h1>
            <p className="text-sm text-tosh-600">
              {t(
                '{email} manziliga havola yubordik. Uni 24 soat ichida oching va parol oʻrnating — bogʻchangiz shundan keyin ochiladi.',
                { email: form.email },
              )}
            </p>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <div>
              <h1 className="text-xl font-bold text-tosh-900">
                {t('15 kunlik sinov — mos kelmasa, hech narsa toʻlamaysiz')}
              </h1>
              <p className="mt-1 text-sm text-tosh-500">
                {t(
                  'Karta soʻralmaydi. Davom ettirsangiz, birinchi toʻlangan oy sinov boshlangan kundan hisoblanadi. Davom ettirmasangiz — hech narsa toʻlamaysiz, maʼlumotlaringiz 30 kun yuklab olish uchun saqlanadi.',
                )}
              </p>
            </div>
            {error && (
              <div role="alert" className="rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-900">
                {error}
              </div>
            )}
            {input('kindergarten_name', t('Bogʻcha nomi'))}
            {input('name', t('Ismingiz'), { autoComplete: 'name' })}
            {input('email', t('Email'), { type: 'email', autoComplete: 'email' })}
            {input('phone', t('Telefon'), { type: 'tel', autoComplete: 'tel' })}
            <div className="grid grid-cols-2 gap-3">
              {input('city', t('Shahar'))}
              {input('children_count', t('Bolalar soni'), { inputMode: 'numeric' })}
            </div>
            {/* Honeypot: invisible to people, filled by bots. */}
            <input
              tabIndex={-1}
              aria-hidden="true"
              autoComplete="off"
              value={form.website}
              onChange={(event) => set({ website: event.target.value })}
              className="absolute -left-[9999px] h-0 w-0 opacity-0"
              name="website"
            />
            <label className="flex items-start gap-2 text-sm text-tosh-600">
              <input
                type="checkbox"
                required
                checked={form.consent}
                onChange={(event) => set({ consent: event.target.checked })}
                className="mt-0.5 h-5 w-5 shrink-0 accent-nihol-600"
              />
              <span>
                {t('Shaxsiy maʼlumotlarga ishlov berishga roziman')} (
                <Link to={`/${locale}/privacy`} className="underline">
                  {t('maxfiylik siyosati')}
                </Link>
                )
              </span>
            </label>
            <button
              type="submit"
              disabled={busy}
              className={cn(
                'w-full rounded-lg bg-nihol-600 px-4 py-2.5 text-sm font-semibold text-white',
                busy ? 'opacity-60' : 'hover:bg-nihol-700',
              )}
            >
              {busy ? t('Yuborilmoqda…') : t('Bogʻchani ochish')}
            </button>
            {/* Savol — matn, harakat — havola (PLAN 10.12). Ilgari butun
                gap bir xil kulrang edi va "Kirish" havolaga o'xshamasdi. */}
            <p className="text-center text-sm text-tosh-600">
              {t('Hisobingiz bormi?')}{' '}
              <Link
                to="/login"
                className="inline-flex min-h-11 items-center font-semibold text-nihol-700 underline underline-offset-2"
              >
                {t('Kirish')}
              </Link>
            </p>
          </form>
        )}
      </main>
    </div>
  )
}
