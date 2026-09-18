/**
 * Hero — birinchi 5 soniya.
 *
 * O'ng tomonda statik skrinshot emas, HTML bilan chizilgan Radix paneli:
 * yuklanganda qatlamlar chuqurlikdan chiqadi (CSS keyframes — rAF'siz
 * ham ishlaydi), raqamlar sanaydi, diagramma chiziladi. Scroll'da panel
 * tomoshabinga yaqinlashadi ("kamera kiradi") va keyingi sahnaga o'tadi.
 */

import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { ArrowDown, ArrowRight, Sparkles } from 'lucide-react'
import { copy, groupThousands, type Locale } from '../content'
import { CountUp, useCompact, useStatic } from '../motion'
import { Bars, Frame, Kpi, Pill, Row } from '../ui/Mock'

const TREND = [61, 68, 72, 70, 79, 86]

export function Hero({ locale }: { locale: Locale }) {
  const t = copy[locale]
  const ref = useRef<HTMLElement>(null)
  const compact = useCompact()
  const isStatic = useStatic()
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] })

  const scale = useTransform(scrollYProgress, [0, 1], [1, compact ? 1.06 : 1.22])
  const y = useTransform(scrollYProgress, [0, 1], [0, compact ? -30 : -90])
  const rotateY = useTransform(scrollYProgress, [0, 0.6], [compact ? 0 : -7, 0])
  const rotateX = useTransform(scrollYProgress, [0, 0.6], [compact ? 0 : 5, 0])
  const opacity = useTransform(scrollYProgress, [0.6, 0.98], [1, 0])
  const textY = useTransform(scrollYProgress, [0, 1], [0, -50])
  const textOpacity = useTransform(scrollYProgress, [0.3, 0.8], [1, 0])

  const motionStyle = isStatic ? undefined : { scale, y, rotateY, rotateX, opacity }

  return (
    <section ref={ref} id="product" className="relative overflow-hidden bg-white pt-[76px]">
      {/* Fon: juda och ko'k nur va nozik nuqta-to'r — "aniq panjara" hissi. */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 [background-image:radial-gradient(circle_at_1px_1px,rgba(15,23,42,0.07)_1px,transparent_0)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_at_70%_30%,black_10%,transparent_70%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-40 -top-40 h-[640px] w-[640px] rounded-full bg-[radial-gradient(closest-side,rgba(37,99,235,0.14),transparent)]"
      />

      <div className="relative mx-auto grid min-h-[calc(100svh-76px)] max-w-[1280px] items-center gap-10 px-5 py-12 lg:grid-cols-[minmax(0,6fr)_minmax(0,6fr)] lg:gap-10 lg:px-8 lg:py-16">
        <motion.div style={isStatic ? undefined : { y: textY, opacity: textOpacity }}>
          <p className="rx-rise inline-flex items-center gap-2 rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-[13px] font-semibold text-brand-700">
            <Sparkles className="h-3.5 w-3.5" />
            {t.hero.eyebrow}
          </p>
          <h1 className="rx-rise [animation-delay:80ms] mt-6 text-balance text-[2.6rem] font-extrabold !leading-[1.02] tracking-[-0.04em] text-slate-950 sm:text-6xl lg:text-[3.9rem] xl:text-[4.5rem]">
            {t.hero.title}
          </h1>
          <p className="rx-rise [animation-delay:160ms] mt-6 max-w-xl text-lg leading-8 text-slate-600 sm:text-xl">
            {t.hero.subtitle}
          </p>
          <div className="rx-rise [animation-delay:240ms] mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a
              href="#demo"
              className="group inline-flex min-h-[54px] items-center justify-center gap-2 rounded-xl bg-brand-600 px-6 text-base font-semibold text-white transition hover:bg-brand-700"
            >
              {t.hero.cta}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </a>
            <a
              href="#one-system"
              className="inline-flex min-h-[54px] items-center justify-center gap-2 rounded-xl border border-slate-200 px-6 text-base font-semibold text-slate-800 transition hover:border-slate-300 hover:bg-slate-50"
            >
              {t.hero.secondary}
            </a>
          </div>
          <p className="rx-rise [animation-delay:320ms] mt-5 text-sm font-medium text-slate-500">
            <span className="font-semibold text-slate-900">{t.hero.priceFrom}</span>
          </p>
        </motion.div>

        <div className="relative [perspective:1600px]">
          <motion.div
            style={motionStyle}
            className="relative origin-center will-change-transform [transform-style:preserve-3d]"
          >
            <div className="rx-rise [animation-delay:200ms]">
              <Frame demo={t.demo} compact>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {t.demo.kpis.slice(0, 4).map((kpi, i) => (
                    <Kpi
                      key={kpi.label}
                      kpi={kpi}
                      index={i}
                      valueNode={
                        <CountUp
                          to={kpi.value}
                          duration={1600}
                          format={(v) =>
                            kpi.value > 999 ? groupThousands(v) : String(Math.round(v))
                          }
                        />
                      }
                    />
                  ))}
                </div>
                <div className="mt-3 grid gap-3 sm:grid-cols-[1.5fr_1fr]">
                  <div className="rounded-xl border border-slate-200/80 p-3">
                    <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">
                      {t.demo.chartTitle}
                    </p>
                    <Bars values={TREND} labels={t.demo.months} className="mt-2" />
                  </div>
                  <div className="hidden rounded-xl border border-slate-200/80 p-3 sm:block">
                    <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">
                      {t.demo.sidebar[4]}
                    </p>
                    <div className="mt-1.5 space-y-0.5">
                      <Row
                        name="Karimov Ali"
                        meta="Quyosh"
                        right={<Pill tone="debt">1 500 000</Pill>}
                      />
                      <Row
                        name="Yusupova Dilnoza"
                        meta="Yulduzcha"
                        right={<Pill tone="debt">600 000</Pill>}
                      />
                      <Row
                        name="Rasulov Bekzod"
                        meta="Kamalak"
                        right={<Pill tone="wait">450 000</Pill>}
                      />
                    </div>
                  </div>
                </div>
              </Frame>
            </div>

            {/* Chuqurlikdagi qatlamlar — panel tepasida suzadi. */}
            <div className="rx-rise [animation-delay:420ms] absolute -bottom-10 -left-6 hidden w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-[0_24px_60px_-20px_rgba(11,23,48,0.35)] sm:block lg:-left-10 [transform:translateZ(60px)]">
              <div className="flex items-center gap-1.5 text-[11px] lg:text-[10px] font-semibold uppercase tracking-wider text-brand-600">
                <Sparkles className="h-3 w-3" /> Radix AI
              </div>
              <p className="mt-1.5 text-[12px] font-semibold leading-snug text-slate-900">
                {locale === 'uz'
                  ? '9 ta bola bo‘yicha to‘lov 15 kundan ortiq kechikmoqda'
                  : 'По 9 детям оплата задерживается более 15 дней'}
              </p>
              <div className="mt-2 flex gap-1.5">
                <Pill tone="debt">{locale === 'uz' ? 'Jiddiy' : 'Серьёзно'}</Pill>
                <Pill tone="neutral">12 450 000</Pill>
              </div>
            </div>
            <div className="rx-rise [animation-delay:520ms] absolute -right-2 -top-5 hidden rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-[0_24px_60px_-20px_rgba(11,23,48,0.3)] sm:block lg:-right-8 [transform:translateZ(90px)]">
              <p className="text-[11px] lg:text-[10px] font-medium text-slate-500">
                {t.demo.kpis[1].label}
              </p>
              <p className="text-lg font-bold tabular-nums text-slate-950">
                <CountUp to={94} duration={1400} />%
              </p>
              <div className="mt-1 h-1.5 w-28 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="rx-fill h-full rounded-full bg-emerald-500"
                  style={{ width: '94%' }}
                />
              </div>
            </div>
          </motion.div>
          <p className="mt-4 text-center text-[12px] text-slate-400 sm:mt-14 lg:text-right">
            {t.demo.note}
          </p>
        </div>
      </div>

      <a
        href="#problem"
        className="absolute bottom-5 left-1/2 hidden -translate-x-1/2 items-center gap-1.5 text-xs font-medium text-slate-400 transition hover:text-slate-700 lg:inline-flex"
      >
        {t.hero.scroll}
        <ArrowDown className="rx-bob h-3.5 w-3.5" />
      </a>
    </section>
  )
}
