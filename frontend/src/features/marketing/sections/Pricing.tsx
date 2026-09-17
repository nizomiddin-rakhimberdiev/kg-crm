/**
 * Narx kalkulyatori.
 *
 * Raqamlar BACKENDDAN keladi (`/api/v1/public/pricing`), kodda
 * qotirilmaydi. Sabab tarixiy: ADR-12 da narx o'zgarganda kodga yozib
 * qo'yilgan qiymatlar yetti joyda eskirib qolgan edi. Kalkulyator
 * amaldagi `SubscriptionPlan` bilan bir manbadan oziqlanishi shart —
 * aks holda sayt bir narxni, hisob-faktura boshqasini ko'rsatardi.
 *
 * Bir bola narxi ham hisoblanmaydi, bo'linadi: `monthly / children` —
 * formula yo'q, faqat API javobi ustida arifmetika.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { marketingApi } from '../api'
import { Reveal } from '../components/Motion'
import { copy, type Locale } from '../content'
import { formatAmount, groupThousands } from '../format'

type Term = 'monthly' | 'annual'

export function Pricing({ locale }: { locale: Locale }) {
  const t = copy[locale].pricing
  const [children, setChildren] = useState(50)
  const [term, setTerm] = useState<Term>('monthly')

  const quote = useQuery({
    queryKey: ['public-pricing', children],
    queryFn: () => marketingApi.pricing(children),
    staleTime: 60_000,
  })
  const data = quote.data
  const loading = quote.isLoading

  const monthlyTotal = data ? Number(data.monthly.total_amount) : null
  const annualTotal = data ? Number(data.annual.total_amount) : null
  const annualBefore = data ? Number(data.annual_before_discount) : null
  const saving = data ? Number(data.annual_saving) : null
  // Yillik to'lovda oyiga tushadigan summa — chegirmani "oyiga qancha"
  // tilida ko'rsatadi; bu odam o'zi hisoblab o'tirmaydigan raqam.
  const effectiveMonthly = annualTotal !== null ? annualTotal / 12 : null
  const perChild =
    term === 'monthly'
      ? monthlyTotal !== null ? monthlyTotal / children : null
      : effectiveMonthly !== null ? effectiveMonthly / children : null

  const headline = term === 'monthly' ? monthlyTotal : annualTotal
  const headlineUnit = term === 'monthly' ? t.perMonth : t.perYear

  return (
    <section id="pricing" className="scroll-mt-24 bg-slate-950 py-20 text-white lg:py-28">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[0.85fr_1.15fr] lg:items-start lg:px-8">
        <Reveal>
          <p className="eyebrow !text-brand-300">{t.eyebrow}</p>
          <h2 className="mt-4 text-balance text-3xl font-bold tracking-[-0.035em] sm:text-4xl">{t.title}</h2>
          <p className="mt-5 max-w-xl leading-7 text-slate-300">{t.text}</p>
          <div className="mt-8 border-l-2 border-brand-400 pl-4 text-sm leading-6 text-slate-300">{t.policy}</div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="rounded-[28px] bg-white p-5 text-slate-900 shadow-2xl shadow-black/30 sm:p-8">
            {/* --- Kirish: bolalar soni --- */}
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                {/* Birlik ("bola") label'dan TASHQARIDA: aks holda input'ning
                    kirish nomi "Bolalar soni bola" bo'lib o'qilardi. */}
                <label className="text-sm font-bold" htmlFor="children-count">
                  {t.children}
                </label>
                <div className="mt-2 flex items-center gap-3">
                  <input
                    id="children-count"
                    className="w-28 rounded-xl border border-slate-300 px-3 py-2.5 text-lg font-bold tabular-nums outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10"
                    type="number"
                    min="1"
                    max="10000"
                    inputMode="numeric"
                    value={children}
                    onChange={(event) =>
                      setChildren(Math.max(1, Math.min(10000, Number(event.target.value) || 1)))
                    }
                  />
                  <span className="text-sm text-slate-500" aria-hidden="true">
                    {t.childrenUnit}
                  </span>
                </div>
              </div>

              {/* --- Muddat: oyma-oy / yillik --- */}
              <div
                role="group"
                aria-label={`${t.monthly} / ${t.annual}`}
                className="inline-flex rounded-xl bg-slate-100 p-1 text-sm font-semibold"
              >
                <TermButton active={term === 'monthly'} onClick={() => setTerm('monthly')}>
                  {t.monthly}
                </TermButton>
                <TermButton active={term === 'annual'} onClick={() => setTerm('annual')}>
                  {t.annual}
                  <span
                    className={cn(
                      'ml-2 rounded-full px-1.5 py-0.5 text-[10px] font-bold',
                      term === 'annual' ? 'bg-white/20 text-white' : 'bg-emerald-100 text-emerald-700',
                    )}
                  >
                    −25%
                  </span>
                </TermButton>
              </div>
            </div>

            <input
              className="mt-6 h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-brand-600"
              type="range"
              min="1"
              max="500"
              value={Math.min(children, 500)}
              onChange={(event) => setChildren(Number(event.target.value))}
              aria-label={t.sliderLabel}
            />

            {/* --- Asosiy raqam --- */}
            <div className="mt-8 rounded-2xl bg-brand-600 p-6 text-white shadow-lg shadow-brand-600/25">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-sm font-medium text-brand-100">
                  {term === 'monthly' ? t.monthly : t.annual}
                </p>
                {term === 'annual' && (
                  <span className="rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-bold">
                    {t.discountBadge}
                  </span>
                )}
              </div>
              <p className="mt-2 text-4xl font-extrabold tracking-[-0.03em] tabular-nums sm:text-5xl">
                {loading || headline === null ? (
                  <span className="text-2xl font-semibold text-brand-100">{t.loading}</span>
                ) : (
                  groupThousands(headline)
                )}
              </p>
              <p className="mt-1 text-sm text-brand-100">{headlineUnit}</p>

              {/* Yillik rejimda: chegirmasiz summa chizilgan, tejov ko'rinadi. */}
              {term === 'annual' && annualBefore !== null && saving !== null && (
                <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/15 pt-4 text-sm">
                  <span className="text-brand-100 line-through decoration-brand-200/70">
                    {formatAmount(annualBefore, locale)}
                  </span>
                  <span className="font-semibold">
                    {t.saving}: {formatAmount(saving, locale)}
                  </span>
                </div>
              )}
            </div>

            {/* --- Yordamchi raqamlar ---
                Oyma-oy: yillik summa · tejov · bir bola.
                Yillik:  oylik summa · yillik to'lovda oyiga · bir bola.
                Tejov va chegirmasiz summa yillik rejimda allaqachon ko'k
                blokda — pastda takrorlanmaydi. */}
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <SubCell
                label={term === 'monthly' ? t.annual : t.monthly}
                value={
                  loading
                    ? t.loading
                    : formatAmount(term === 'monthly' ? (annualTotal ?? undefined) : (monthlyTotal ?? undefined), locale)
                }
              />
              {term === 'monthly' ? (
                <SubCell label={t.saving} value={loading ? t.loading : formatAmount(saving ?? undefined, locale)} accent />
              ) : (
                <SubCell
                  label={t.effectiveMonthly}
                  value={loading || effectiveMonthly === null ? t.loading : `≈ ${formatAmount(Math.round(effectiveMonthly), locale)}`}
                  accent
                />
              )}
              <SubCell
                label={t.perChild}
                value={loading || perChild === null ? t.loading : `≈ ${formatAmount(Math.round(perChild), locale)}`}
              />
            </div>

            {quote.isError && (
              <p role="alert" className="mt-4 text-xs text-red-600">
                {t.error}
              </p>
            )}

            <p className="mt-5 text-xs leading-5 text-slate-400">{t.disclaimer}</p>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function TermButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        'inline-flex items-center rounded-lg px-3.5 py-2 transition',
        active ? 'bg-slate-950 text-white shadow-sm' : 'text-slate-600 hover:text-slate-950',
      )}
    >
      {children}
    </button>
  )
}

function SubCell({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className={cn('mt-1.5 text-base font-bold tracking-tight tabular-nums', accent ? 'text-emerald-700' : 'text-slate-900')}>
        {value}
      </p>
    </div>
  )
}
