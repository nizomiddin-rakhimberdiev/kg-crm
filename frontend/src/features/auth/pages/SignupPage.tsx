/**
 * Sinov uchun ariza sahifasi (`/signup`).
 *
 * Akkauntni faqat vendor ochadi (ADR-10), shuning uchun bu sahifa o'zi
 * akkaunt yaratmaydi — ariza (lead) qoldiradi va 15 kunlik sinov uchun
 * jamoa bog'lanadi. Yuborish mantiqi landingdagi demo formasi bilan BIR
 * XIL (`marketingApi.createLead`): rozilik majburiy, bot tuzog'i
 * (`website`) va takrorlanmas `submission_id`.
 */

import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Check, Loader2, ShieldCheck } from 'lucide-react'
import { AuthShell } from '@/components/auth/AuthShell'
import { marketingApi } from '@/features/marketing/api'
import { ApiError } from '@/lib/api/types'
import { locale, t } from '@/lib/i18n'

const POLICY_VERSION = '2026-09'

const newSubmissionId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`

type State = 'idle' | 'sending' | 'success' | 'error'

export default function SignupPage() {
  const [submissionId, setSubmissionId] = useState(newSubmissionId)
  const [state, setState] = useState<State>('idle')
  const [error, setError] = useState('')

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formEl = event.currentTarget
    const form = new FormData(formEl)
    setState('sending')
    setError('')
    try {
      await marketingApi.createLead({
        name: String(form.get('name') ?? ''),
        phone: String(form.get('phone') ?? ''),
        kindergarten_name: String(form.get('kindergarten_name') ?? ''),
        children_count: Number(form.get('children_count')),
        city: String(form.get('city') ?? ''),
        message: '',
        language: locale,
        consent: form.get('consent') === 'on',
        privacy_policy_version: POLICY_VERSION,
        submission_id: submissionId,
        website: String(form.get('website') ?? ''),
      })
      setState('success')
      formEl.reset()
      setSubmissionId(newSubmissionId())
    } catch (reason) {
      setState('error')
      setError(
        reason instanceof ApiError
          ? reason.message
          : t("Kutilmagan xatolik. Qaytadan urinib ko'ring."),
      )
    }
  }

  const fields = [
    ['name', t('Ismingiz'), 'text', 'name'],
    ['phone', t('Telefon'), 'tel', 'tel'],
    ['kindergarten_name', t("Bog'cha nomi"), 'text', 'organization'],
    ['children_count', t('Bolalar soni'), 'number', 'off'],
    ['city', t('Shahar'), 'text', 'address-level1'],
  ] as const

  return (
    <AuthShell
      wide
      title={t("Radix CRM'ni sinab ko'ring")}
      subtitle={t("Arizani qoldiring — 15 kunlik bepul sinov uchun biz siz bilan bog'lanamiz.")}
      footer={
        <>
          {t('Akkauntingiz bormi?')}{' '}
          <Link
            to="/login"
            className="font-semibold text-nihol-700 underline-offset-4 transition hover:text-nihol-800 hover:underline"
          >
            {t('Kirish')}
          </Link>
        </>
      }
    >
      <AnimatePresence mode="wait" initial={false}>
        {state === 'success' ? (
          <motion.div
            key="success"
            role="status"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1, transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] } }}
            className="grid min-h-64 place-items-center text-center"
          >
            <div>
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 260, damping: 16, delay: 0.1 }}
                className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-nihol-50 text-nihol-600 shadow-glow"
              >
                <Check className="h-8 w-8" strokeWidth={2.5} />
              </motion.span>
              <p className="mt-5 font-display text-lg font-bold text-ildiz-900">
                {t('Arizangiz qabul qilindi.')}
              </p>
              <p className="mt-1.5 text-sm text-tosh-500">{t('Tez orada siz bilan bog‘lanamiz.')}</p>
            </div>
          </motion.div>
        ) : (
          <motion.form
            key="form"
            onSubmit={onSubmit}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              {fields.map(([name, label, type, autoComplete], index) => (
                <motion.label
                  key={name}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0, transition: { delay: 0.05 * index, duration: 0.4 } }}
                  className={`block text-sm font-semibold text-tosh-700 ${
                    name === 'kindergarten_name' ? 'sm:col-span-2' : ''
                  }`}
                >
                  {label}
                  <input
                    required
                    name={name}
                    type={type}
                    min={name === 'children_count' ? 1 : undefined}
                    autoComplete={autoComplete}
                    inputMode={
                      name === 'phone' ? 'tel' : name === 'children_count' ? 'numeric' : undefined
                    }
                    className="field mt-1.5"
                  />
                </motion.label>
              ))}
            </div>

            {/* Bot tuzog'i: odamga ko'rinmaydi, botlar to'ldiradi. */}
            <label className="sr-only" aria-hidden="true">
              Website
              <input tabIndex={-1} autoComplete="off" name="website" />
            </label>

            <label className="mt-5 flex cursor-pointer items-start gap-3 text-sm leading-5 text-tosh-600">
              <input
                required
                type="checkbox"
                name="consent"
                className="mt-0.5 h-5 w-5 shrink-0 rounded border-tosh-300 accent-nihol-600"
              />
              <span>
                {t("Shaxsiy ma'lumotlarimni qayta ishlashga roziman.")}{' '}
                <Link
                  className="font-semibold text-nihol-700 underline underline-offset-2"
                  to={`/${locale}/privacy`}
                >
                  {t('Maxfiylik siyosati')}
                </Link>
              </span>
            </label>

            <AnimatePresence>
              {state === 'error' && (
                <motion.p
                  role="alert"
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700"
                >
                  {error}
                </motion.p>
              )}
            </AnimatePresence>

            <button type="submit" disabled={state === 'sending'} className="btn-primary group mt-6">
              {state === 'sending' ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('Yuborilmoqda…')}
                </>
              ) : (
                <>
                  {t('Ariza yuborish')}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>

            <p className="mt-4 flex items-center justify-center gap-2 text-xs text-tosh-400">
              <ShieldCheck className="h-4 w-4" />
              {t("Ma'lumotlaringiz himoyalangan va uchinchi shaxslarga berilmaydi.")}
            </p>
          </motion.form>
        )}
      </AnimatePresence>
    </AuthShell>
  )
}
