/**
 * Moliyaviy nazorat — aniqlik, diagramma to'plami emas.
 *
 * Kirim → chiqim → balans: bitta oqim, sanaladigan raqamlar, bitta
 * tenglama. Raqamlar bir-biriga MOS (73 950 000 − 18 300 000 − 31 500 000
 * = 24 150 000) — namunaviy, lekin hisob to'g'ri.
 */

import { ArrowDown, ArrowRight } from 'lucide-react'
import { copy, groupThousands, money, type Locale } from '../content'
import { CountUp, Reveal } from '../motion'

const TONE = {
  in: 'text-emerald-700',
  out: 'text-rose-700',
  warn: 'text-amber-700',
  neutral: 'text-slate-900',
}
const BAR = {
  in: 'bg-emerald-500',
  out: 'bg-rose-400',
  warn: 'bg-amber-400',
  neutral: 'bg-slate-400',
}

export function Finance({ locale }: { locale: Locale }) {
  const t = copy[locale].finance
  const byId = Object.fromEntries(t.metrics.map((m) => [m.id, m]))
  const payments = byId.payments.value
  const parts = [byId.expenses, byId.salaries, byId.balance]

  return (
    <section className="bg-[#0B1730] py-20 text-white lg:py-32">
      <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
        <Reveal>
          <div className="max-w-3xl">
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-400">
              {t.eyebrow}
            </p>
            <h2 className="mt-3 text-balance text-3xl font-extrabold !leading-[1.08] tracking-[-0.03em] text-white sm:text-4xl lg:text-[3.4rem]">
              {t.title}
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-300 lg:text-lg">{t.text}</p>
          </div>
        </Reveal>

        <div className="mt-12 grid gap-4 lg:mt-16 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:items-stretch">
          {/* Kirim */}
          <Reveal>
            <div className="h-full rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <p className="text-[12px] font-semibold uppercase tracking-wider text-slate-400">
                {locale === 'uz' ? 'Kirim' : 'Приход'}
              </p>
              {[byId.revenue, byId.payments, byId.debt].map((m) => (
                <div key={m.id} className="mt-5 first:mt-4">
                  <p className="text-[13px] text-slate-400">{m.label}</p>
                  <p
                    className={`mt-0.5 text-2xl font-bold tabular-nums tracking-tight ${m.tone === 'neutral' ? 'text-white' : m.tone === 'warn' ? 'text-amber-300' : 'text-emerald-300'}`}
                  >
                    <CountUp to={m.value} format={groupThousands} />
                  </p>
                </div>
              ))}
            </div>
          </Reveal>
          <div className="hidden items-center lg:flex">
            <ArrowRight className="h-6 w-6 text-slate-600" />
          </div>
          <div className="flex justify-center lg:hidden">
            <ArrowDown className="h-5 w-5 text-slate-600" />
          </div>

          {/* Chiqim */}
          <Reveal delay={0.06}>
            <div className="h-full rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <p className="text-[12px] font-semibold uppercase tracking-wider text-slate-400">
                {locale === 'uz' ? 'Chiqim' : 'Расход'}
              </p>
              {[byId.expenses, byId.salaries].map((m) => (
                <div key={m.id} className="mt-5 first:mt-4">
                  <p className="text-[13px] text-slate-400">{m.label}</p>
                  <p className="mt-0.5 text-2xl font-bold tabular-nums tracking-tight text-rose-300">
                    <CountUp to={m.value} format={groupThousands} />
                  </p>
                </div>
              ))}
            </div>
          </Reveal>
          <div className="hidden items-center lg:flex">
            <ArrowRight className="h-6 w-6 text-slate-600" />
          </div>
          <div className="flex justify-center lg:hidden">
            <ArrowDown className="h-5 w-5 text-slate-600" />
          </div>

          {/* Balans */}
          <Reveal delay={0.12}>
            <div className="h-full rounded-2xl border border-brand-400/40 bg-brand-500/10 p-6">
              <p className="text-[12px] font-semibold uppercase tracking-wider text-brand-300">
                {byId.balance.label}
              </p>
              <p className="mt-4 text-4xl font-extrabold tabular-nums tracking-tight text-white">
                <CountUp to={byId.balance.value} format={groupThousands} duration={1800} />
              </p>
              <p className="mt-1 text-[13px] text-slate-400">
                {locale === 'uz' ? 'so‘m · sentabr' : 'сум · сентябрь'}
              </p>
              <p className="mt-6 text-[13px] leading-5 text-slate-300">{t.equation}</p>
            </div>
          </Reveal>
        </div>

        {/* To'lovlar qanday taqsimlanadi — bitta chiziq. */}
        <Reveal delay={0.1}>
          <div className="mt-8 rounded-2xl border border-white/10 bg-white/[0.04] p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-[13px] text-slate-400">{byId.payments.label}</p>
              <p className="text-sm font-semibold tabular-nums text-white">
                {money(payments, locale)}
              </p>
            </div>
            <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-white/10">
              {parts.map((m) => (
                <div
                  key={m.id}
                  className={`rx-grow-x h-full origin-left ${BAR[m.tone]}`}
                  style={{ width: `${(m.value / payments) * 100}%` }}
                />
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
              {parts.map((m) => (
                <span key={m.id} className="flex items-center gap-2 text-[13px] text-slate-300">
                  <span className={`h-2.5 w-2.5 rounded-full ${BAR[m.tone]}`} />
                  {m.label} ·{' '}
                  <span
                    className={`font-semibold tabular-nums ${TONE[m.tone] === 'text-slate-900' ? 'text-white' : ''}`}
                  >
                    {Math.round((m.value / payments) * 100)}%
                  </span>
                </span>
              ))}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
