/**
 * "Bitta tizim" transformatsiyasi.
 *
 * Yetti modul halqa bo'ylab turadi. Scroll: markazdan har biriga chiziq
 * chiziladi (ular BOG'LANGAN), so'ng halqa qisqarib, plitkalar bitta
 * panelning kataklariga tushadi — panel ularning o'rnida paydo bo'ladi.
 * Sarlavha shu payt kuchayadi: "Operatsion ish va moliyaviy nazorat —
 * bir tizimda."
 */

import { useRef } from 'react'
import { motion, useTransform, type MotionValue } from 'framer-motion'
import {
  ArrowRight,
  BarChart3,
  Boxes,
  CalendarCheck,
  Receipt,
  UserRound,
  Users,
  Wallet,
} from 'lucide-react'
import { RadixMark } from '@/components/brand/Logo'
import { BRAND } from '@/lib/brand'
import { copy, type Locale } from '../content'
import { useScene, useStaticScene } from '../motion'

const ICONS = [UserRound, Wallet, CalendarCheck, Users, Boxes, Receipt, BarChart3]
// Yetti modul — besh brend rangining tiniqlik darajalarida.
const TONES = [
  'bg-nihol-50 text-nihol-600',
  'bg-ildiz-50 text-ildiz-700',
  'bg-orik-50 text-orik-700',
  'bg-tosh-100 text-tosh-600',
  'bg-nihol-100 text-nihol-700',
  'bg-ildiz-100 text-ildiz-800',
  'bg-orik-100 text-orik-800',
]

// Yakuniy katak (panel ichida): 4 + 3.
const SLOTS = [
  { x: -258, y: -40 },
  { x: -86, y: -40 },
  { x: 86, y: -40 },
  { x: 258, y: -40 },
  { x: -172, y: 44 },
  { x: 0, y: 44 },
  { x: 172, y: 44 },
]

const RADIUS = 250

function ringPose(i: number, radius: number) {
  const angle = (i / 7) * Math.PI * 2 - Math.PI / 2
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius }
}

/**
 * Modul plitkasi.
 *
 * `fluid` — katakning enini oladi (panel ichida). Belgilangan `w-[…]`
 * telefonda plitkani 11 px gacha siqib qo'yardi va yozuv "B…" bo'lib
 * ko'rinardi: aylana maketi uchun kerak bo'lgan qat'iy en panel ichida
 * kerak emas edi.
 */
function Tile({
  label,
  index,
  className = '',
  compact = false,
  fluid = false,
}: {
  label: string
  index: number
  className?: string
  compact?: boolean
  fluid?: boolean
}) {
  const Icon = ICONS[index]
  const size = fluid
    ? 'w-full min-w-0 px-2.5 py-2'
    : compact
      ? 'w-[6.5rem] px-2 py-1.5'
      : 'w-[9.5rem] px-3 py-2.5'
  return (
    <div
      className={`flex items-center gap-2 rounded-xl border border-slate-200 bg-white shadow-[0_16px_40px_-20px_rgba(18,53,47,0.35)] ${size} ${className}`}
    >
      <span
        className={`grid shrink-0 place-items-center rounded-lg ${compact ? 'h-6 w-6' : 'h-7 w-7'} ${TONES[index]}`}
      >
        <Icon className={compact ? 'h-3.5 w-3.5' : 'h-4 w-4'} />
      </span>
      <span
        className={`truncate font-semibold text-slate-800 ${compact ? 'text-[12px]' : 'text-[12px]'}`}
      >
        {label}
      </span>
    </div>
  )
}

function Orbiting({
  label,
  index,
  progress,
  factor,
}: {
  label: string
  index: number
  progress: MotionValue<number>
  factor: number
}) {
  const radius = RADIUS * factor
  const ring = ringPose(index, radius)
  // Desktop: plitka panel katagiga tushadi. Mobil: panel 2 ustunli, katak
  // mosligi yo'q — halqa qisqarib, plitkalar so'nadi, panel o'rnida chiqadi.
  const slot = factor < 1 ? { x: ring.x * 0.3, y: ring.y * 0.3 } : SLOTS[index]
  const x = useTransform(progress, [0.4, 0.72], [ring.x, slot.x])
  const y = useTransform(progress, [0.4, 0.72], [ring.y, slot.y])
  const scale = useTransform(progress, [0.4, 0.72], [1, factor < 1 ? 0.7 : 0.92])
  const opacity = useTransform(progress, [0.74, 0.84], [1, 0])
  return (
    <motion.div
      style={{ x, y, scale, opacity }}
      className="absolute left-1/2 top-1/2 will-change-transform"
    >
      <div className="-translate-x-1/2 -translate-y-1/2">
        <Tile label={label} index={index} compact={factor < 1} />
      </div>
    </motion.div>
  )
}

function Connector({
  index,
  progress,
  factor,
}: {
  index: number
  progress: MotionValue<number>
  factor: number
}) {
  const ring = ringPose(index, RADIUS * factor)
  const draw = useTransform(progress, [0.08 + index * 0.02, 0.36 + index * 0.02], [0, 1])
  const fade = useTransform(progress, [0.4, 0.6], [1, 0])
  return (
    <motion.line
      x1={0}
      y1={0}
      x2={ring.x}
      y2={ring.y}
      stroke={BRAND.nihol}
      strokeOpacity={0.55}
      strokeWidth={1.5}
      strokeLinecap="round"
      pathLength={1}
      style={{ pathLength: draw, opacity: fade }}
    />
  )
}

function Panel({
  locale,
  factor,
  fluid = false,
}: {
  locale: Locale
  factor: number
  fluid?: boolean
}) {
  const t = copy[locale]
  return (
    <div
      className={`rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_30px_80px_-30px_rgba(18,53,47,0.25)] ${
        fluid ? 'w-full max-w-[720px]' : ''
      }`}
      style={fluid ? undefined : { width: factor < 1 ? 320 : 720 }}
    >
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <RadixMark size={24} />
          <span className="text-[12px] font-semibold text-slate-800">{t.demo.org}</span>
        </div>
        <span className="text-[12px] text-slate-500">{t.demo.today}</span>
      </div>
      <div
        className={`mt-3 grid gap-2 ${fluid ? 'grid-cols-2 sm:grid-cols-4' : factor < 1 ? 'grid-cols-2' : 'grid-cols-4'}`}
      >
        {t.oneSystem.modules.map((label, i) => (
          <Tile
            key={label}
            label={label}
            index={i}
            compact={!fluid && factor < 1}
            fluid={fluid}
            className={`shadow-none ${
              fluid
                ? i === 6
                  ? 'col-span-2 sm:col-span-1'
                  : ''
                : factor < 1
                  ? i === 6
                    ? 'col-span-2'
                    : ''
                  : i === 4
                    ? 'col-start-1'
                    : ''
            }`}
          />
        ))}
      </div>
      {/* Bog'liqlik: bitta amal — boshqa modulda natija. */}
      <ul
        className={`mt-3 grid gap-2 border-t border-slate-100 pt-3 ${
          fluid ? 'sm:grid-cols-3' : factor < 1 ? '' : 'grid-cols-3'
        }`}
      >
        {t.oneSystem.links.map(([cause, effect]) => (
          <li
            key={cause}
            className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 rounded-lg bg-slate-50 px-2.5 py-2 text-[12px]"
          >
            <span className="text-slate-600">{cause}</span>
            <ArrowRight className="h-3 w-3 shrink-0 text-brand-600" />
            <span className="font-semibold text-slate-900">{effect}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function OneSystem({ locale }: { locale: Locale }) {
  const t = copy[locale].oneSystem
  const ref = useRef<HTMLElement>(null)
  const progress = useScene(ref)
  const isStatic = useStaticScene()
  const factor = 1

  const panelOpacity = useTransform(progress, [0.7, 0.85], [0, 1])
  const panelScale = useTransform(progress, [0.7, 0.9], [0.96, 1])
  const titleScale = useTransform(progress, [0.75, 0.95], [1, 1.06])
  const titleY = useTransform(progress, [0, 0.4], [0, -20])

  if (isStatic) {
    return (
      <section ref={ref} id="one-system" className="bg-white py-14 lg:py-28">
        <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
          <Heading locale={locale} />
          <div className="mt-8 flex justify-center lg:mt-10">
            <Panel locale={locale} factor={factor} fluid />
          </div>
        </div>
      </section>
    )
  }

  return (
    <section ref={ref} id="one-system" className="relative bg-white" style={{ height: '260vh' }}>
      <div className="sticky top-0 flex h-screen flex-col overflow-hidden pt-[76px]">
        <motion.div
          style={{ y: titleY, scale: titleScale }}
          className="mx-auto w-full max-w-[1280px] px-5 pt-3 lg:px-8 lg:pt-8"
        >
          <Heading locale={locale} />
        </motion.div>

        <div className="relative flex-1">
          <svg
            aria-hidden="true"
            className="pointer-events-none absolute left-1/2 top-1/2 overflow-visible"
            width={1}
            height={1}
          >
            {t.modules.map((_, i) => (
              <Connector key={i} index={i} progress={progress} factor={factor} />
            ))}
          </svg>

          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div
              style={{ opacity: panelOpacity, scale: panelScale }}
              className="will-change-transform"
            >
              <Panel locale={locale} factor={factor} />
            </motion.div>
          </div>

          {t.modules.map((label, i) => (
            <Orbiting key={label} label={label} index={i} progress={progress} factor={factor} />
          ))}
        </div>
      </div>
    </section>
  )
}

function Heading({ locale }: { locale: Locale }) {
  const t = copy[locale].oneSystem
  return (
    <div className="mx-auto max-w-3xl text-center">
      <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
        {t.eyebrow}
      </p>
      <h2 className="mt-3 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900 sm:text-[2rem]">
        {t.title}
      </h2>
      <p className="mx-auto mt-4 hidden max-w-2xl text-base leading-7 text-slate-600 sm:block lg:text-lg">
        {t.text}
      </p>
    </div>
  )
}
