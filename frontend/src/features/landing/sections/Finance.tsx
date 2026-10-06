/**
 * Moliyaviy nazorat — pul oqimi scroll bilan yuradi.
 *
 * Pinned sahna. Raqamlar sanoqni scroll'dan oladi (vaqtdan emas): kirim
 * o'sadi → strelka chiziladi → chiqim ayiriladi → balans chiqadi →
 * taqsimot chizig'i bo'lak-bo'lak to'ladi. Orqaga scroll — orqaga
 * hisob. Raqamlar bir-biriga mos (73 950 000 − 18 300 000 − 31 500 000 =
 * 24 150 000).
 */

import { useRef } from 'react'
import { motion, useTransform, type MotionValue } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { copy, groupThousands, money, type Locale } from '../content'
import { CountUp, Reveal, useScene, useStaticScene } from '../motion'

type Tone = 'in' | 'out' | 'warn' | 'neutral'
const TEXT: Record<Tone, string> = {
  in: 'text-emerald-300',
  out: 'text-rose-300',
  warn: 'text-amber-300',
  neutral: 'text-white',
}
const BAR: Record<Tone, string> = {
  in: 'bg-emerald-500',
  out: 'bg-rose-400',
  warn: 'bg-amber-400',
  neutral: 'bg-slate-400',
}

/** Scroll oralig'i [a, b] ichida 0 → value gacha sanaydigan raqam. */
function Scrub({
  progress,
  range,
  value,
  className,
}: {
  progress: MotionValue<number>
  range: [number, number]
  value: number
  className?: string
}) {
  const text = useTransform(progress, range, [0, value], { clamp: true })
  const label = useTransform(text, (v) => groupThousands(v))
  return <motion.span className={className}>{label}</motion.span>
}

function Appear({
  progress,
  at,
  children,
  className = '',
}: {
  progress: MotionValue<number>
  at: number
  children: React.ReactNode
  className?: string
}) {
  const opacity = useTransform(progress, [at, at + 0.06], [0, 1], { clamp: true })
  const y = useTransform(progress, [at, at + 0.08], [18, 0], { clamp: true })
  return (
    <motion.div style={{ opacity, y }} className={className}>
      {children}
    </motion.div>
  )
}

function Arrow({ progress, at }: { progress: MotionValue<number>; at: number }) {
  const opacity = useTransform(progress, [at, at + 0.05], [0.2, 1], { clamp: true })
  const shift = useTransform(progress, [at, at + 0.08], [-10, 0], { clamp: true })
  return (
    <motion.div style={{ opacity, x: shift }} className="flex items-center">
      <ArrowRight className="h-6 w-6 text-brand-400" />
    </motion.div>
  )
}

export function Finance({ locale }: { locale: Locale }) {
  const t = copy[locale].finance
  const ref = useRef<HTMLElement>(null)
  const progress = useScene(ref)
  const isStatic = useStaticScene()
  const byId = Object.fromEntries(t.metrics.map((m) => [m.id, m]))
  const payments = byId.payments.value
  const parts = [byId.expenses, byId.salaries, byId.balance]
  const ui = copy[locale].ui.finance

  // Taqsimot chizig'i bo'laklari: har biri o'z oralig'ida to'ladi.
  const seg = [
    useTransform(progress, [0.7, 0.78], [0, 1], { clamp: true }),
    useTransform(progress, [0.78, 0.86], [0, 1], { clamp: true }),
    useTransform(progress, [0.86, 0.94], [0, 1], { clamp: true }),
  ]
  const equationOpacity = useTransform(progress, [0.62, 0.7], [0, 1], { clamp: true })

  const heading = (
    <div className="max-w-3xl">
      <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-400">
        {t.eyebrow}
      </p>
      <h2 className="mt-2 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-white sm:text-[2rem] lg:mt-3">
        {t.title}
      </h2>
      <p className="mt-3 hidden text-base leading-7 text-slate-300 sm:block lg:text-lg">{t.text}</p>
    </div>
  )

  if (isStatic) {
    return (
      <section ref={ref} data-nav-dark className="bg-ildiz-900 py-20 text-white lg:py-32">
        <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
          <Reveal>{heading}</Reveal>
          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            {[
              [byId.revenue, byId.payments, byId.debt],
              [byId.expenses, byId.salaries],
              [byId.balance],
            ].map((group, gi) => (
              <div key={gi} className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
                {group.map((m) => (
                  <div key={m.id} className="mt-4 first:mt-0">
                    <p className="text-[13px] text-slate-400">{m.label}</p>
                    <p className={`text-2xl font-bold tabular-nums ${TEXT[m.tone]}`}>
                      <CountUp to={m.value} format={groupThousands} />
                    </p>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  const card = 'rounded-2xl border border-white/10 bg-white/[0.04] p-3.5 lg:p-6'
  const label = 'text-[12px] text-slate-400 lg:text-[13px]'
  const num = 'text-xl font-bold tabular-nums tracking-tight lg:text-2xl'

  return (
    <section
      ref={ref}
      data-nav-dark
      className="relative bg-ildiz-900 text-white"
      style={{ height: '280vh' }}
    >
      <div className="sticky top-0 flex h-screen flex-col overflow-hidden pt-[76px]">
        <div className="mx-auto flex w-full max-w-[1280px] flex-1 flex-col justify-center px-5 py-4 lg:px-8">
          {heading}

          <div className="mt-4 grid gap-2 lg:mt-12 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:gap-4">
            {/* Kirim */}
            <Appear progress={progress} at={0.02} className={card}>
              <p className="text-[12px] font-semibold uppercase tracking-wider text-slate-400">
                {ui.inflow}
              </p>
              <div>
                {[
                  [byId.revenue, [0.04, 0.2]],
                  [byId.payments, [0.12, 0.28]],
                  [byId.debt, [0.2, 0.34]],
                ].map(([m, range]) => {
                  const metric = m as typeof byId.revenue
                  return (
                    <div key={metric.id} className="mt-4 first:mt-3">
                      <p className={label}>{metric.label}</p>
                      <Scrub
                        progress={progress}
                        range={range as [number, number]}
                        value={metric.value}
                        className={`${num} ${TEXT[metric.tone]}`}
                      />
                    </div>
                  )
                })}
              </div>
            </Appear>
            <Arrow progress={progress} at={0.34} />

            {/* Chiqim */}
            <Appear progress={progress} at={0.38} className={card}>
              <p className="text-[12px] font-semibold uppercase tracking-wider text-slate-400">
                {ui.outflow}
              </p>
              <div>
                {[
                  [byId.expenses, [0.4, 0.52]],
                  [byId.salaries, [0.46, 0.58]],
                ].map(([m, range]) => {
                  const metric = m as typeof byId.expenses
                  return (
                    <div key={metric.id} className="mt-4 first:mt-3">
                      <p className={label}>{metric.label}</p>
                      <Scrub
                        progress={progress}
                        range={range as [number, number]}
                        value={metric.value}
                        className={`${num} ${TEXT[metric.tone]}`}
                      />
                    </div>
                  )
                })}
              </div>
            </Appear>
            <Arrow progress={progress} at={0.58} />

            {/* Balans */}
            <Appear
              progress={progress}
              at={0.6}
              className="rounded-2xl border border-brand-400/40 bg-brand-500/10 p-3.5 lg:p-6"
            >
              <p className="text-[12px] font-semibold uppercase tracking-wider text-brand-300">
                {byId.balance.label}
              </p>
              <p className="mt-2 num text-3xl font-bold tracking-tight text-white lg:mt-4 lg:text-4xl">
                <Scrub progress={progress} range={[0.62, 0.8]} value={byId.balance.value} />
              </p>
              <p className="mt-0.5 text-[12px] text-slate-400 lg:text-[13px]">{ui.unitMonth}</p>
              <motion.p
                style={{ opacity: equationOpacity }}
                className="mt-2 text-[12px] leading-5 text-slate-300 lg:mt-6 lg:text-[13px] [@media(max-height:780px)]:hidden"
              >
                {t.equation}
              </motion.p>
            </Appear>
          </div>

          {/* To'lovlar qanday taqsimlanadi — bo'lak-bo'lak. */}
          <Appear progress={progress} at={0.66} className={`${card} mt-3 lg:mt-6`}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className={label}>{byId.payments.label}</p>
              <p className="text-sm font-semibold tabular-nums text-white">
                {money(payments, locale)}
              </p>
            </div>
            <div className="mt-2 flex h-3 overflow-hidden rounded-full bg-white/10 lg:mt-3">
              {parts.map((m, i) => (
                <motion.div
                  key={m.id}
                  style={{ scaleX: seg[i], width: `${(m.value / payments) * 100}%` }}
                  className={`h-full origin-left ${BAR[m.tone]}`}
                />
              ))}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 lg:mt-3 [@media(max-height:780px)]:hidden">
              {parts.map((m, i) => (
                <motion.span
                  key={m.id}
                  style={{ opacity: seg[i] }}
                  className="flex items-center gap-2 text-[12px] text-slate-300 lg:text-[13px]"
                >
                  <span className={`h-2.5 w-2.5 rounded-full ${BAR[m.tone]}`} />
                  {m.label} ·{' '}
                  <span className="font-semibold tabular-nums text-white">
                    {Math.round((m.value / payments) * 100)}%
                  </span>
                </motion.span>
              ))}
            </div>
          </Appear>
        </div>
      </div>
    </section>
  )
}
