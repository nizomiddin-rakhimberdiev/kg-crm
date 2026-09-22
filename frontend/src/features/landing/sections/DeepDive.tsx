/**
 * Mahsulot ichiga sho'ng'ish — panel sahnaning qahramoni.
 *
 * Katta panel pinned turadi; scroll uni "kamera" kabi vidjetdan vidjetga
 * yaqinlashtiradi: umumiy → davomat → qarzdorlik → tushum → umumiy.
 * Nishon koordinatalari DOM'dan o'lchanadi (offset zanjiri — transform
 * ta'sir qilmaydi), shuning uchun har qanday ekran kengligida markazga tushadi.
 */

import { useLayoutEffect, useRef, useState } from 'react'
import { motion, useMotionValueEvent, useTransform } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { copy, groupThousands, type Locale } from '../content'
import { CountUp, easeInOut, Reveal, useCompact, useScene, useStatic } from '../motion'
import { Bars, Frame, Kpi, Pill, Row } from '../ui/Mock'

const TREND = [61, 68, 72, 70, 79, 86]
const ZOOM_DESKTOP = 1.7
const ZOOM_COMPACT = 1.3

type Point = { x: number; y: number }

/** Elementning markazi — `root` markaziga nisbatan, px (transform'siz). */
function centerWithin(el: HTMLElement, root: HTMLElement): Point {
  let x = el.offsetWidth / 2
  let y = el.offsetHeight / 2
  let node: HTMLElement | null = el
  while (node && node !== root) {
    x += node.offsetLeft
    y += node.offsetTop
    node = node.offsetParent as HTMLElement | null
  }
  return { x: x - root.offsetWidth / 2, y: y - root.offsetHeight / 2 }
}

// Progress bo'yicha bosqichlar: [boshlanish, tugash] — orasida ushlab turadi.
const STOPS: [number, number][] = [
  [0, 0.16],
  [0.24, 0.42],
  [0.5, 0.68],
  [0.76, 0.92],
]

function stepAt(p: number): number {
  for (let i = STOPS.length - 1; i >= 0; i--) if (p >= STOPS[i][0]) return i
  return 0
}

/** Ikki bosqich orasidagi silliq o'tish (0 → 1). */
function blendAt(p: number): { from: number; to: number; t: number } {
  const i = stepAt(p)
  const [, end] = STOPS[i]
  const nextStart = STOPS[i + 1]?.[0] ?? 1
  if (p <= end) return { from: i, to: i, t: 0 }
  const t = easeInOut(Math.min(1, (p - end) / (nextStart - end)))
  return { from: i, to: Math.min(i + 1, STOPS.length), t }
}

export function DeepDive({ locale }: { locale: Locale }) {
  const t = copy[locale]
  const ref = useRef<HTMLElement>(null)
  const frameRef = useRef<HTMLDivElement>(null)
  const stickyRef = useRef<HTMLDivElement>(null)
  const targets = useRef<(HTMLDivElement | null)[]>([])
  const points = useRef<Point[]>([
    { x: 0, y: 0 },
    { x: 0, y: 0 },
    { x: 0, y: 0 },
    { x: 0, y: 0 },
  ])
  // Frame markazining VIEWPORT markazidan siljishi — zoom nishoni ekran
  // o'rtasiga kelishi uchun shu ham qo'shiladi.
  const frameShift = useRef<Point>({ x: 0, y: 0 })
  const progress = useScene(ref)
  const compact = useCompact()
  const isStatic = useStatic()
  const [step, setStep] = useState(0)

  useLayoutEffect(() => {
    const measure = () => {
      const root = frameRef.current
      if (!root) return
      points.current = [0, 1, 2, 3].map((i) => {
        const el = targets.current[i]
        return i === 0 || !el ? { x: 0, y: 0 } : centerWithin(el, root)
      })
      frameShift.current = stickyRef.current
        ? centerWithin(root, stickyRef.current)
        : { x: 0, y: 0 }
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [compact])

  // Bosqich i uchun (scale, x, y): 0 — umumiy (1, 0, 0); qolganlari —
  // nishon markazga kelsin: translate = −markaz × scale.
  const pose = (i: number) => {
    if (i === 0 || i >= STOPS.length) return { s: 1, x: 0, y: 0 }
    const c = points.current[i]
    const zoom = compact ? ZOOM_COMPACT : ZOOM_DESKTOP
    return { s: zoom, x: -c.x * zoom - frameShift.current.x, y: -c.y * zoom - frameShift.current.y }
  }
  const mix = (p: number, key: 's' | 'x' | 'y') => {
    const { from, to, t: k } = blendAt(p)
    const a = pose(from)[key]
    const b = pose(to)[key]
    return a + (b - a) * k
  }
  const scale = useTransform(progress, (p) => mix(p, 's'))
  const x = useTransform(progress, (p) => mix(p, 'x'))
  const y = useTransform(progress, (p) => mix(p, 'y'))
  const stepMv = useTransform(progress, (p) => {
    const { from, to, t: k } = blendAt(p)
    return k > 0.5 ? to : from
  })
  useMotionValueEvent(stepMv, 'change', (v) => setStep(v >= STOPS.length ? 0 : v))

  const pinned = !isStatic
  const ui = copy[locale].ui.deepDive

  const panel = (
    <div className="relative">
      <motion.div
        ref={frameRef}
        style={pinned ? { scale, x, y } : undefined}
        className="origin-center will-change-transform"
      >
        <Frame demo={t.demo} compact={compact}>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
            {t.demo.kpis.map((kpi, i) => (
              <div
                key={kpi.label}
                ref={
                  i === 1
                    ? (el) => (targets.current[1] = el)
                    : i === 2 && compact
                      ? (el) => (targets.current[2] = el)
                      : undefined
                }
              >
                <Kpi
                  kpi={kpi}
                  index={i}
                  emphasis={
                    pinned && ((step === 1 && i === 1) || (compact && step === 2 && i === 2))
                  }
                  valueNode={
                    <CountUp
                      to={kpi.value}
                      duration={1500}
                      format={(v) => (kpi.value > 999 ? groupThousands(v) : String(Math.round(v)))}
                    />
                  }
                />
              </div>
            ))}
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-[1.6fr_1fr]">
            <div
              ref={(el) => (targets.current[3] = el)}
              className={`rounded-xl border p-3 transition-colors ${pinned && step === 3 ? 'border-brand-300 ring-4 ring-brand-500/10' : 'border-slate-200/80'}`}
            >
              <div className="flex items-center justify-between">
                <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">
                  {t.demo.chartTitle}
                </p>
                <span className="text-[11px] lg:text-[10px] text-slate-400">{ui.last6}</span>
              </div>
              <Bars values={TREND} labels={t.demo.months} className="mt-2" />
            </div>
            <div
              ref={compact ? undefined : (el) => (targets.current[2] = el)}
              className={`hidden rounded-xl border p-3 transition-colors sm:block ${pinned && !compact && step === 2 ? 'border-brand-300 ring-4 ring-brand-500/10' : 'border-slate-200/80'}`}
            >
              <div className="flex items-center justify-between">
                <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">
                  {t.demo.sidebar[4]}
                </p>
                <Pill tone="debt">9</Pill>
              </div>
              <div className="mt-1.5 space-y-0.5">
                <Row
                  name="Karimov Ali"
                  meta="Quyosh · 42 kun"
                  right={<Pill tone="debt">1 500 000</Pill>}
                />
                <Row
                  name="Yusupova Dilnoza"
                  meta="Yulduzcha · 31 kun"
                  right={<Pill tone="debt">600 000</Pill>}
                />
                <Row
                  name="Rasulov Bekzod"
                  meta="Kamalak · 18 kun"
                  right={<Pill tone="wait">450 000</Pill>}
                />
              </div>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-l-4 border-slate-200/80 border-l-red-500 px-3 py-2">
            <Sparkles className="h-3.5 w-3.5 text-brand-600" />
            <p className="truncate text-[12px] lg:text-[11px] font-semibold text-slate-800">
              {ui.alert}
            </p>
            <span className="ml-auto whitespace-nowrap text-[11px] lg:text-[10px] font-semibold text-brand-700">
              {ui.why}
            </span>
          </div>
        </Frame>
      </motion.div>
    </div>
  )

  const heading = (
    <div className="mx-auto max-w-3xl text-center">
      <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
        {t.deepDive.eyebrow}
      </p>
      <h2 className="mt-3 text-balance text-[1.75rem] font-extrabold !leading-[1.08] tracking-[-0.03em] text-slate-950 sm:text-4xl lg:text-[2.75rem]">
        {t.deepDive.title}
      </h2>
      <p className="mx-auto mt-3 hidden max-w-2xl text-base leading-7 text-slate-600 sm:block lg:text-lg">
        {t.deepDive.text}
      </p>
    </div>
  )

  if (!pinned) {
    return (
      <section ref={ref} className="bg-white py-16 lg:py-24">
        <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
          <Reveal>{heading}</Reveal>
          <Reveal delay={0.08} className="mt-8">
            {panel}
            <p className="mt-3 text-center text-[12px] text-slate-400">{t.demo.note}</p>
          </Reveal>
        </div>
      </section>
    )
  }

  return (
    <section
      ref={ref}
      className="relative bg-white"
      style={{ height: compact ? '280vh' : '320vh' }}
    >
      <div
        ref={stickyRef}
        className="sticky top-0 flex h-screen flex-col overflow-hidden pt-[76px]"
      >
        <div className="mx-auto w-full max-w-[1280px] px-5 pt-3 lg:px-8 lg:pt-4">{heading}</div>
        <div className="mt-3 flex justify-center gap-1.5 px-5 lg:mt-4 lg:gap-2">
          {t.deepDive.steps.map((label, i) => (
            <span
              key={label}
              className={`whitespace-nowrap rounded-full px-2.5 py-1 text-[12px] lg:text-[11px] font-semibold transition-colors duration-300 lg:px-3 lg:text-[12px] ${
                step === i ? 'bg-slate-950 text-white' : 'bg-slate-100 text-slate-500'
              }`}
            >
              {label}
            </span>
          ))}
        </div>
        <div className="relative mx-auto mt-3 w-full max-w-5xl flex-1 px-5 lg:mt-4 lg:px-8">
          {panel}
        </div>
        <p className="pb-3 text-center text-[12px] text-slate-400">{t.demo.note}</p>
      </div>
    </section>
  )
}
