/**
 * Narxlar — juda aniq. Bitta slayder, ikki rejim, bitta raqam.
 *
 * Summa BACKEND'dan (`/public/pricing`, ADR-12 formulasi) — frontend
 * narxni hisoblamaydi. Misollar jadvali — matn (content.ts), formulani
 * tushuntirish uchun.
 */

import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useMotionValueEvent, useScroll, useTransform } from 'framer-motion'
import { ArrowRight, Check } from 'lucide-react'
import { marketingApi } from '@/features/marketing/api'
import { CURRENCY, copy, groupThousands, money, type Locale } from '../content'
import { Reveal, useStatic } from '../motion'
import { Num } from '../ui/Num'

type Term = 'monthly' | 'annual'

// Bo'lim ekranga kirayotganda slayder o'zi "namoyish" qiladi: 20 → 50 bola,
// narx shunga qarab o'zgaradi. Foydalanuvchi slayderga tegishi bilan
// namoyish to'xtaydi — kalkulyator uniki.
const DEMO_FROM = 20
const DEMO_TO = 50

export function Pricing({ locale }: { locale: Locale }) {
  const t = copy[locale].pricing
  const ref = useRef<HTMLElement>(null)
  const isStatic = useStatic()
  const [children, setChildren] = useState(isStatic ? DEMO_TO : DEMO_FROM)
  const [touched, setTouched] = useState(false)
  const [term, setTerm] = useState<Term>('monthly')

  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 90%', 'start 25%'] })
  const demo = useTransform(scrollYProgress, [0, 1], [DEMO_FROM, DEMO_TO], { clamp: true })
  useMotionValueEvent(demo, 'change', (v) => {
    if (!touched && !isStatic) setChildren(Math.round(v))
  })

  // API'ga har bir oraliq qiymat uchun emas — to'xtagandan keyin so'raladi.
  const [queried, setQueried] = useState(children)
  useEffect(() => {
    const timer = window.setTimeout(() => setQueried(children), 160)
    return () => window.clearTimeout(timer)
  }, [children])

  const pick = (value: number) => {
    setTouched(true)
    setChildren(value)
  }

  const quote = useQuery({
    queryKey: ['public-pricing', queried],
    queryFn: () => marketingApi.pricing(queried),
    staleTime: 60_000,
    placeholderData: (previous) => previous,
  })
  const data = quote.data
  const monthly = data ? Number(data.monthly.total_amount) : null
  const annual = data ? Number(data.annual.total_amount) : null
  const shown = term === 'monthly' ? monthly : annual
  const effective = annual !== null ? annual / 12 : null

  return (
    <section ref={ref} id="pricing" className="scroll-mt-16 bg-white py-20 lg:py-32">
      <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
        <Reveal>
          <div className="max-w-3xl">
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
              {t.eyebrow}
            </p>
            <h2 className="mt-3 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900 sm:text-[2rem]">
              {t.title}
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-600 lg:text-lg">{t.text}</p>
          </div>
        </Reveal>

        <div className="mt-10 grid gap-6 lg:mt-14 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-8">
          <Reveal>
            <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-6 sm:p-8">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <label htmlFor="rx-children" className="text-base font-semibold text-slate-900">
                  {t.childrenLabel}
                </label>
                <div className="flex items-center gap-2">
                  <input
                    id="rx-children"
                    type="number"
                    min={1}
                    max={500}
                    value={children}
                    onChange={(e) =>
                      setChildren(Math.min(500, Math.max(1, Number(e.target.value) || 1)))
                    }
                    className="h-11 w-24 rounded-xl border border-slate-200 bg-white px-3 text-center text-lg font-bold tabular-nums text-slate-950 outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10"
                  />
                  <span className="text-sm text-slate-500">{t.childrenUnit}</span>
                </div>
              </div>
              <input
                aria-label={t.childrenLabel}
                type="range"
                min={10}
                max={300}
                step={1}
                value={Math.min(300, children)}
                onChange={(e) => pick(Number(e.target.value))}
                onPointerDown={() => setTouched(true)}
                className="mt-5 h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-brand-600"
              />
              <div className="mt-1 flex justify-between text-[12px] text-slate-400">
                <span>10</span>
                <span>300</span>
              </div>

              <div role="tablist" className="mt-7 inline-flex rounded-xl bg-slate-200/70 p-1">
                {(['monthly', 'annual'] as const).map((k) => (
                  <button
                    key={k}
                    role="tab"
                    aria-selected={term === k}
                    type="button"
                    onClick={() => setTerm(k)}
                    className={`inline-flex min-h-[44px] items-center gap-2 rounded-lg px-4 text-sm font-semibold transition ${
                      term === k
                        ? 'bg-white text-slate-950 shadow-card'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {t[k]}
                    {k === 'annual' && (
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[12px] font-bold text-emerald-700">
                        {t.annualBadge}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              <div className="mt-6 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <p
                  className="num text-4xl font-bold tracking-tight text-tosh-900 sm:text-5xl"
                  aria-live="polite"
                >
                  {shown === null ? (
                    quote.isError ? (
                      '—'
                    ) : (
                      '…'
                    )
                  ) : (
                    <Num value={shown} duration={0.45} />
                  )}
                </p>
                <span className="text-base font-medium text-slate-500">
                  {shown === null
                    ? ''
                    : `${CURRENCY[locale]} ${term === 'monthly' ? t.perMonth : t.perYear}`}
                </span>
              </div>
              {term === 'annual' && effective !== null && (
                <p className="mt-1 text-sm text-slate-500">
                  {t.effective.replace('{amount}', money(effective, locale))}
                </p>
              )}
              {quote.isError && (
                <p role="alert" className="mt-2 text-sm text-red-600">
                  {t.error}
                </p>
              )}

              <ul className="mt-6 grid gap-2 sm:grid-cols-2">
                {t.includes.map((item) => (
                  <li key={item} className="flex items-center gap-2 text-[15px] text-slate-700">
                    <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-emerald-100 text-emerald-700">
                      <Check className="h-3 w-3" strokeWidth={3} />
                    </span>
                    {item}
                  </li>
                ))}
              </ul>

              <a
                href="#demo"
                className="group mt-7 inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-6 text-base font-semibold text-white transition hover:bg-brand-700 sm:w-auto"
              >
                {t.cta}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </a>
            </div>
          </Reveal>

          <Reveal delay={0.08}>
            <div className="rounded-[28px] border border-slate-200 p-6 sm:p-8">
              <p className="text-base font-semibold text-slate-900">{t.examplesTitle}</p>
              <table className="mt-4 w-full text-[15px]">
                <thead className="text-left text-[12px] uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="pb-2 font-medium">{t.childrenUnit}</th>
                    <th className="pb-2 text-right font-medium">{t.monthly}</th>
                    <th className="pb-2 text-right font-medium">{t.annual}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {t.examples.map((row) => (
                    <tr
                      key={row.children}
                      className={row.children === children ? 'bg-brand-50/60' : ''}
                    >
                      <td className="py-2.5 font-semibold tabular-nums text-slate-900">
                        {row.children}
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-slate-700">
                        {groupThousands(row.monthly)}
                      </td>
                      <td className="py-2.5 text-right tabular-nums text-slate-700">
                        {groupThousands(row.monthly * 12 * 0.75)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-[13px] text-slate-500">{t.annualFormula}</p>
              <div className="mt-6 rounded-2xl bg-slate-50 p-4">
                <p className="text-[15px] font-semibold text-slate-900">{t.first3}</p>
                <p className="mt-1 text-[13px] leading-5 text-slate-500">{t.note}</p>
              </div>
            </div>
          </Reveal>

          {/* Ikkinchi model — alohida o'rnatma (ADR-13): narx kelishuv asosida. */}
          <Reveal delay={0.12} className="lg:col-span-2">
            <div className="flex flex-col gap-4 rounded-[28px] border border-ildiz-800 bg-ildiz-900 p-6 text-white sm:flex-row sm:items-center sm:justify-between sm:p-8">
              <div>
                <span className="rounded-full bg-white/10 px-2.5 py-1 text-[12px] font-semibold uppercase tracking-wider text-slate-200">
                  {t.standalone.badge}
                </span>
                <p className="mt-3 text-xl font-bold tracking-tight">{t.standalone.title}</p>
                <p className="mt-1 max-w-xl text-[15px] leading-6 text-slate-300">
                  {t.standalone.text}
                </p>
                <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5">
                  {t.standalone.points.map((point) => (
                    <li
                      key={point}
                      className="flex items-center gap-1.5 text-[13px] text-slate-300"
                    >
                      <Check className="h-3.5 w-3.5 text-emerald-400" strokeWidth={3} />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
              <a
                href="#demo"
                className="inline-flex min-h-[48px] shrink-0 items-center justify-center rounded-xl border border-white/20 px-5 text-[15px] font-semibold text-white transition hover:bg-white/10"
              >
                {t.standalone.cta}
              </a>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
