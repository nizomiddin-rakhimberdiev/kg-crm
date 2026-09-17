/**
 * Hero.
 *
 * `100vh` ATAYLAB ishlatilmagan: balandligi ekranga tenglashtirilgan
 * hero sahifaning o'zini birinchi kadrdan tashqariga itarib yuboradi —
 * mijoz pastga aylantirmaguncha mahsulot haqida hech narsa ko'rmaydi.
 *
 * Narx trust-point'i (`priceNote`) API'dan keladi, kodga yozilmagan:
 * hero'dagi raqam bilan kalkulyatordagi raqam bitta manbadan bo'lishi
 * shart — aks holda ular bir kun ajralib qoladi va mijoz buni birinchi
 * bo'lib sezadi.
 */

import { useQuery } from '@tanstack/react-query'
import { motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, CalendarCheck, CircleDollarSign, LayoutDashboard, UsersRound } from 'lucide-react'
import { marketingApi } from '../api'
import { CountUp } from '../components/Motion'
import { RootMotif } from '../components/RootMotif'
import { copy, type Locale } from '../content'
import { formatAmount } from '../format'

const EASE = [0.16, 1, 0.3, 1] as const

export function Hero({ locale }: { locale: Locale }) {
  const t = copy[locale]
  const reduced = useReducedMotion()

  // Kalkulyator bilan bir xil kalit — TanStack Query bitta so'rovni
  // ikkalasiga ham beradi.
  const baseQuote = useQuery({
    queryKey: ['public-pricing', 50],
    queryFn: () => marketingApi.pricing(50),
    staleTime: 60_000,
  })
  const priceNote = baseQuote.data
    ? t.hero.priceNote
        .replace('{children}', String(baseQuote.data.plan.included_children))
        .replace('{amount}', formatAmount(baseQuote.data.monthly.total_amount, locale))
    : null

  const rise = (delay: number) =>
    reduced
      ? {}
      : {
          initial: { opacity: 0, y: 24 },
          animate: { opacity: 1, y: 0 },
          transition: { duration: 0.7, delay, ease: EASE },
        }

  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_50%_at_72%_18%,rgba(37,99,235,0.10),transparent_60%),linear-gradient(180deg,#f7faff_0%,#ffffff_70%)]"
      />
      <RootMotif className="pointer-events-none absolute -right-24 top-4 hidden h-[560px] w-[560px] opacity-[0.55] lg:block" />

      <div className="relative mx-auto grid max-w-7xl gap-10 px-5 pb-14 pt-10 sm:pt-14 lg:grid-cols-[1.02fr_0.98fr] lg:items-center lg:gap-10 lg:px-8 lg:pb-28 lg:pt-20">
        <div>
          <motion.p className="eyebrow tracking-[0.1em] sm:tracking-[0.16em]" {...rise(0)}>
            {t.hero.eyebrow}
          </motion.p>

          <motion.h1
            className="mt-5 max-w-2xl text-pretty text-4xl font-extrabold leading-[1.06] tracking-[-0.045em] text-slate-950 sm:text-5xl lg:text-[3.4rem]"
            {...rise(0.08)}
          >
            {t.hero.title}
          </motion.h1>

          <motion.p className="mt-5 max-w-xl text-[17px] leading-[1.6] text-slate-600 sm:mt-6 sm:text-lg sm:leading-8" {...rise(0.16)}>
            {t.hero.text}
          </motion.p>


          {/* Narx — CTA'dan OLDIN (brif §4 iyerarxiyasi): sarlavha → matn →
              narx → harakat. Odam avval "qancha?" ga javob oladi, keyin
              bosadi. Yuklanmaguncha joy band turadi, sahifa sakramaydi. */}
          <motion.div
            className="mt-6 flex flex-col gap-1.5 text-sm text-slate-500 sm:flex-row sm:items-center sm:gap-4"
            {...rise(0.24)}
          >
            <span className="inline-flex min-h-[1.5rem] shrink-0 items-center gap-2 whitespace-nowrap text-[15px] font-semibold text-slate-800 sm:text-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-brand-600" aria-hidden="true" />
              {priceNote ?? '\u00a0'}
            </span>
            <span className="hidden text-slate-300 sm:inline" aria-hidden="true">
              ·
            </span>
            <span>{t.hero.note}</span>
          </motion.div>

          {/* Mobil'da BITTA dominant tugma: secondary — oddiy havola ko'rinishida
              (brif §5). Desktopda ikkalasi tugma — avvalgidek. */}
          <motion.div className="mt-6 flex flex-col gap-3 sm:mt-8 sm:flex-row" {...rise(0.32)}>
            <a
              className="group inline-flex min-h-[52px] items-center justify-center gap-2 rounded-xl bg-slate-950 px-6 py-4 text-[15px] font-semibold text-white shadow-lg shadow-slate-900/15 transition hover:-translate-y-0.5 hover:bg-slate-800 hover:shadow-xl sm:text-sm"
              href="#demo"
            >
              {t.hero.primary}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </a>
            <a
              className="inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-xl px-4 py-2.5 text-[15px] font-semibold text-slate-700 transition hover:text-slate-950 sm:min-h-[52px] sm:border sm:border-slate-200 sm:bg-white sm:px-6 sm:py-4 sm:text-sm sm:hover:-translate-y-0.5 sm:hover:border-slate-300 sm:hover:shadow-md"
              href="#capabilities"
            >
              {t.hero.secondary}
              <ArrowRight className="h-4 w-4 sm:hidden" aria-hidden="true" />
            </a>
          </motion.div>
        </div>

        <motion.div
          className="relative"
          {...(reduced
            ? {}
            : {
                initial: { opacity: 0, y: 32, scale: 0.97 },
                animate: { opacity: 1, y: 0, scale: 1 },
                transition: { duration: 0.85, delay: 0.2, ease: EASE },
              })}
        >
          <div className="absolute -inset-8 -z-10 rounded-[40px] bg-brand-200/35 blur-3xl" />
          <div className="rounded-[24px] border border-slate-200/80 bg-white/95 p-4 shadow-2xl shadow-brand-900/10 backdrop-blur sm:rounded-[28px] sm:p-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <span className="text-sm font-bold tracking-tight text-slate-900">{t.preview.live}</span>
              {/* "Namuna" — bu jonli ma'lumot emas va shunday deyilmaydi. */}
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide text-slate-500">
                {t.preview.sample}
              </span>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2.5 sm:mt-5 sm:gap-3">
              <HeroMetric
                icon={CircleDollarSign}
                label={t.preview.revenue}
                value={<CountUp to={18.5} format={(v) => `${v.toFixed(1)}M`} />}
              />
              <HeroMetric icon={UsersRound} label={t.preview.children} value={<CountUp to={142} />} />
              <HeroMetric
                icon={CalendarCheck}
                label={t.preview.attendance}
                value={<CountUp to={91} format={(v) => `${Math.round(v)}%`} />}
              />
              <HeroMetric icon={LayoutDashboard} label={t.preview.debt} value={<CountUp to={2.4} format={(v) => `${v.toFixed(1)}M`} />} />
            </div>

            <div className="mt-3 rounded-2xl bg-slate-950 p-4 text-white sm:mt-4 sm:p-5">
              <p className="text-xs text-slate-400">{t.preview.tasksTitle}</p>
              <div className="mt-4 space-y-3">
                {t.preview.tasks.map((label, index) => (
                  <motion.div
                    key={label}
                    className="flex items-center gap-3 text-sm"
                    {...(reduced
                      ? {}
                      : {
                          initial: { opacity: 0, x: -8 },
                          animate: { opacity: 1, x: 0 },
                          transition: { duration: 0.4, delay: 0.7 + index * 0.12, ease: EASE },
                        })}
                  >
                    <span className="h-2 w-2 rounded-full bg-brand-400" />
                    {label}
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

function HeroMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof UsersRound
  label: string
  value: React.ReactNode
}) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3 transition hover:border-brand-200 hover:bg-white sm:p-3.5">
      <Icon className="h-4 w-4 text-brand-600" />
      <p className="mt-2.5 text-xs font-medium uppercase tracking-wide text-slate-400 sm:mt-3">{label}</p>
      <p className="mt-1 text-xl font-bold tracking-tight tabular-nums text-slate-900">{value}</p>
    </div>
  )
}
