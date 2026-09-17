/**
 * Demo zayavkasi formasi.
 *
 * `noValidate` ATAYLAB YO'Q: brauzerning o'z tekshiruvi `required`
 * maydonlarni va rozilik belgisini yuborishdan oldin to'xtatadi. Uni
 * o'chirib qo'yish rozilik belgilanmagan zayavkani ham backendga
 * yuborardi — ya'ni maxfiylik siyosatidagi va'da buzilardi.
 */

import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Check, ShieldCheck } from 'lucide-react'
import { ApiError } from '@/lib/api/types'
import { marketingApi } from '../api'
import { Reveal } from '../components/Motion'
import { copy, type Locale } from '../content'

const POLICY_VERSION = '2026-09'

const newSubmissionId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`

const FIELD_CLASS =
  'mt-1.5 w-full rounded-xl border border-slate-200 px-3.5 py-3 text-sm outline-none transition placeholder:text-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10'

export function LeadForm({ locale }: { locale: Locale }) {
  const t = copy[locale].form
  const [submissionId, setSubmissionId] = useState(newSubmissionId)
  const [state, setState] = useState<'idle' | 'sending' | 'success' | 'error'>('idle')
  const [error, setError] = useState('')

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    // Forma ELEMENTINING O'ZI `await` dan OLDIN saqlanadi.
    //
    // `event.currentTarget` hodisa tarqatilishi tugagach `null` bo'ladi
    // (bu haqiqiy DOM xatti-harakati). `await` dan keyin unga murojaat
    // qilish — `formEl.reset()` — har doim `TypeError` ko'tarardi, HATTO
    // lead backendda muvaffaqiyatli yaratilgan bo'lsa ham; pastdagi
    // `catch` esa uni "yuborib bo'lmadi" degan xabarga aylantirardi.
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
    <section id="demo" className="scroll-mt-24 bg-white py-20 lg:py-28">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[0.78fr_1.22fr] lg:px-8">
        <Reveal>
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="section-title mt-4 text-balance">{t.title}</h2>
          <p className="mt-5 max-w-md leading-7 text-slate-600">{t.text}</p>
          <div className="mt-8 flex items-start gap-3 rounded-2xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />
            {locale === 'uz'
              ? 'Ma’lumotlaringiz faqat demo zayavkasini ko‘rib chiqish uchun ishlatiladi.'
              : 'Ваши данные используются только для обработки заявки на демо.'}
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <form
            className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-card sm:p-8"
            onSubmit={onSubmit}
          >
            {state === 'success' ? (
              <div role="status" className="grid min-h-72 place-items-center text-center">
                <div>
                  <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-emerald-50 text-emerald-600">
                    <Check className="h-7 w-7" strokeWidth={2.5} />
                  </span>
                  <p className="mt-5 text-lg font-bold text-slate-900">{t.success}</p>
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
                        className={FIELD_CLASS}
                        name={name}
                        type={type}
                        inputMode={
                          name === 'phone' ? 'tel' : name === 'children_count' ? 'numeric' : undefined
                        }
                      />
                    </label>
                  ))}
                </div>

                <label className="mt-4 block text-sm font-medium text-slate-700">
                  {t.message}
                  <textarea
                    className={`${FIELD_CLASS} min-h-24 resize-y`}
                    name="message"
                    maxLength={1000}
                  />
                </label>

                {/* Bot tuzog'i: odam ko'rmaydi, bot to'ldiradi. */}
                <label className="sr-only" aria-hidden="true">
                  Website
                  <input tabIndex={-1} autoComplete="off" name="website" />
                </label>

                <label className="mt-5 flex cursor-pointer items-start gap-3 text-sm leading-5 text-slate-600">
                  <input
                    required
                    className="mt-0.5 h-4 w-4 rounded border-slate-300 accent-brand-600"
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
                  className="group mt-6 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 py-4 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-60"
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
