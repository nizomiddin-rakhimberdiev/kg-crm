/**
 * Demo formasi — butun hikoyaning tabiiy yakuni.
 *
 * Yuborish mantiqi asosiy landing bilan BIR XIL (`marketingApi.createLead`,
 * rozilik majburiy, bot tuzog'i, idempotent `submission_id`): lead —
 * platforma darajasidagi ma'lumot, tenant emas.
 */

import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Check, Send, ShieldCheck } from 'lucide-react'
import { telegramUrl } from '@/config/contact'
import { POLICY_VERSION } from '@/features/marketing/legal'
import { marketingApi } from '@/features/marketing/api'
import { ApiError } from '@/lib/api/types'
import { copy, type Locale } from '../content'
import { Reveal } from '../motion'

const newSubmissionId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`

const FIELD =
  'peer mt-1.5 min-h-[50px] w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-base text-slate-900 outline-none transition placeholder:text-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10'

export function Lead({ locale }: { locale: Locale }) {
  const t = copy[locale].lead
  const [submissionId, setSubmissionId] = useState(newSubmissionId)
  const [state, setState] = useState<'idle' | 'sending' | 'success' | 'error'>('idle')
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
        message: String(form.get('message') ?? ''),
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
      setError(reason instanceof ApiError ? reason.message : t.error)
    }
  }

  const fields = [
    ['name', t.name, 'text'],
    ['phone', t.phone, 'tel'],
    ['kindergarten_name', t.kindergarten, 'text'],
    ['children_count', t.children, 'number'],
    ['city', t.city, 'text'],
  ] as const

  return (
    <section id="demo" className="relative scroll-mt-16 overflow-hidden bg-white py-20 lg:py-32">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-40 top-1/3 h-[560px] w-[560px] rounded-full bg-[radial-gradient(closest-side,rgba(46,158,107,0.12),transparent)]"
      />
      <div className="relative mx-auto grid max-w-[1280px] gap-10 px-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16 lg:px-8">
        <Reveal>
          <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
            {t.eyebrow}
          </p>
          <h2 className="mt-3 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900 sm:text-[2rem]">
            {t.title}
          </h2>
          <p className="mt-4 max-w-md text-base leading-7 text-slate-600 lg:text-lg">{t.text}</p>
          <div className="mt-8 flex items-start gap-3 rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
            {copy[locale].faq.items[6].a}
          </div>
        </Reveal>

        <Reveal delay={0.08}>
          <form
            onSubmit={onSubmit}
            className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_30px_80px_-40px_rgba(18,53,47,0.3)] sm:p-8"
          >
            {state === 'success' ? (
              <div role="status" className="grid min-h-72 place-items-center text-center">
                <div>
                  <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-emerald-50 text-emerald-600">
                    <Check className="h-7 w-7" strokeWidth={2.5} />
                  </span>
                  <p className="mt-5 text-lg font-bold text-slate-900">{t.success}</p>
                  {/* Qachon bog'lanishimiz ANIQ aytiladi (PLAN 5.7):
                      "tez orada" kutishni noaniq qiladi va odam ertasi
                      kuni boshqa CRM'ga yozadi. Kutishni xohlamaganga —
                      Telegram. */}
                  <p className="mt-2 text-[15px] text-slate-600">{t.successNext}</p>
                  <a
                    href={telegramUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-5 inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-brand-600 px-5 text-[15px] font-semibold text-white transition hover:bg-brand-700"
                  >
                    <Send aria-hidden="true" className="h-4 w-4" />
                    {t.telegram}
                  </a>
                </div>
              </div>
            ) : (
              <>
                <div className="grid gap-4 sm:grid-cols-2">
                  {fields.map(([name, label, type]) => (
                    <label key={name} className="block text-sm font-medium text-slate-700">
                      {label}
                      <input
                        required
                        min={name === 'children_count' ? 1 : undefined}
                        className={FIELD}
                        name={name}
                        type={type}
                        inputMode={
                          name === 'phone'
                            ? 'tel'
                            : name === 'children_count'
                              ? 'numeric'
                              : undefined
                        }
                        autoComplete={
                          name === 'name'
                            ? 'name'
                            : name === 'phone'
                              ? 'tel'
                              : name === 'city'
                                ? 'address-level1'
                                : 'off'
                        }
                      />
                    </label>
                  ))}
                </div>
                <label className="mt-4 block text-sm font-medium text-slate-700">
                  {t.message}
                  <textarea
                    className={`${FIELD} min-h-24 resize-y`}
                    name="message"
                    maxLength={1000}
                  />
                </label>
                <label className="sr-only" aria-hidden="true">
                  Website
                  <input tabIndex={-1} autoComplete="off" name="website" />
                </label>
                <label className="mt-5 flex cursor-pointer items-start gap-3 text-sm leading-5 text-slate-600">
                  <input
                    required
                    className="mt-0.5 h-5 w-5 shrink-0 rounded border-slate-300 accent-brand-600"
                    type="checkbox"
                    name="consent"
                  />
                  <span>
                    {t.consent}{' '}
                    <Link
                      className="font-semibold text-brand-700 underline underline-offset-2"
                      to={`/${locale}/privacy`}
                    >
                      {t.privacy}
                    </Link>
                  </span>
                </label>
                {state === 'error' && (
                  <p role="alert" className="mt-4 text-sm text-red-600">
                    {error || t.error}
                  </p>
                )}
                <button
                  disabled={state === 'sending'}
                  className="group mt-6 inline-flex min-h-[54px] w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 text-base font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
                >
                  {state === 'sending' ? t.sending : t.submit}
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </button>
              </>
            )}
          </form>
        </Reveal>
      </div>
    </section>
  )
}
