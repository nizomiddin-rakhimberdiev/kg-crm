/**
 * Muammo sahnasi: TARQOQLIK → TARTIB.
 *
 * Pinned (sticky) sahna. Scroll progressi 0 → 0.6: Telegram xabari, Excel
 * jadvali, daftar, chek — hammasi markazga yig'iladi, burilishi to'g'rilanadi
 * va kichrayadi; 0.5 → 0.75: ular so'nadi, ularning O'RNIDA bitta Radix
 * oynasi paydo bo'ladi — o'sha ma'lumot, endi tartibli qatorlar sifatida.
 *
 * Progress = 0 kadr o'zi ma'noli (tarqoq qog'ozlar), shuning uchun JS'siz
 * ham bo'lim bo'sh emas.
 */

import { useRef } from 'react'
import { motion, useTransform, type MotionValue } from 'framer-motion'
import {
  CalendarCheck,
  FileSpreadsheet,
  MessageCircle,
  Receipt,
  StickyNote,
  Users,
  Wallet,
} from 'lucide-react'
import { copy, type Copy, type FragmentCopy, type Locale } from '../content'
import { useCompact, useScene, useStatic } from '../motion'
import { Frame, Pill, Row } from '../ui/Mock'

const POSES: { x: number; y: number; r: number }[] = [
  { x: -430, y: -150, r: -7 },
  { x: 370, y: -170, r: 6 },
  { x: -330, y: 120, r: 5 },
  { x: 430, y: 110, r: -5 },
  { x: -40, y: -210, r: 3 },
  { x: -120, y: 220, r: -4 },
  { x: 220, y: -20, r: 8 },
]

const ICONS = {
  chat: MessageCircle,
  sheet: FileSpreadsheet,
  note: StickyNote,
  receipt: Receipt,
  attendance: CalendarCheck,
  staff: Users,
  expense: Wallet,
} as const

const SKIN: Record<keyof typeof ICONS, string> = {
  chat: 'bg-sky-50 border-sky-200 text-sky-900',
  sheet:
    'bg-emerald-50 border-emerald-200 text-emerald-900 [background-image:linear-gradient(rgba(5,150,105,0.08)_1px,transparent_1px)] [background-size:100%_18px]',
  note: 'bg-amber-50 border-amber-200 text-amber-900',
  receipt:
    'bg-white border-slate-200 text-slate-800 [background-image:radial-gradient(rgba(15,23,42,0.12)_1px,transparent_1px)] [background-size:8px_8px]',
  attendance: 'bg-white border-slate-200 text-slate-800',
  staff: 'bg-violet-50 border-violet-200 text-violet-900',
  expense: 'bg-rose-50 border-rose-200 text-rose-900',
}

function Paper({
  fragment,
  className = '',
  compact = false,
}: {
  fragment: FragmentCopy
  className?: string
  compact?: boolean
}) {
  const kind = fragment.kind as keyof typeof ICONS
  const Icon = ICONS[kind] ?? StickyNote
  return (
    <div
      className={`rounded-lg border p-3 text-left shadow-[0_18px_40px_-18px_rgba(11,23,48,0.35)] ${compact ? 'w-40' : 'w-56'} ${SKIN[kind] ?? SKIN.note} ${className}`}
    >
      <div className="flex items-center gap-1.5 text-[11px] font-semibold">
        <Icon className="h-3.5 w-3.5 opacity-70" />
        <span className="truncate">{fragment.title}</span>
      </div>
      <ul className="mt-2 space-y-1 text-[11px] leading-snug opacity-90">
        {fragment.lines.map((line) => (
          <li key={line} className="truncate">
            {line}
          </li>
        ))}
      </ul>
    </div>
  )
}

function FlyingPaper({
  fragment,
  index,
  progress,
  factor,
}: {
  fragment: FragmentCopy
  index: number
  progress: MotionValue<number>
  factor: number
}) {
  const pose = POSES[index % POSES.length]
  // Yig'ilish: 0 → 0.6. Yo'qolish: 0.5 → 0.68 (oyna 0.5 dan chiqa boshlaydi).
  const x = useTransform(progress, [0, 0.6], [pose.x * factor, (index - 3) * 22 * factor])
  const y = useTransform(progress, [0, 0.6], [pose.y * factor, 0])
  const rotate = useTransform(progress, [0, 0.6], [pose.r, 0])
  const scale = useTransform(progress, [0, 0.6], [1, 0.55])
  const opacity = useTransform(progress, [0.48, 0.66], [1, 0])
  // Tashqi qatlam — framer transform'i; ichki — markazlash. Bitta elementda
  // ikkalasi bo'lsa, framer inline `transform` Tailwind'nikini bekor qiladi.
  return (
    <motion.div
      style={{ x, y, rotate, scale, opacity }}
      className="absolute left-1/2 top-1/2 will-change-transform"
    >
      <div className="-translate-x-1/2 -translate-y-1/2">
        <Paper fragment={fragment} compact={factor < 1} />
      </div>
    </motion.div>
  )
}

function Resolved({ locale, compact }: { locale: Locale; compact: boolean }) {
  const t = copy[locale]
  const f = t.problem.fragments
  return (
    <Frame demo={t.demo} active={0} compact={compact} className="w-full">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-slate-200/80 p-3">
          <p className="text-[11px] font-semibold text-slate-800">{f[4].title}</p>
          <Row
            name={f[4].lines[0].split(' · ')[0]}
            meta={t.demo.today}
            right={<Pill tone="ok">18 / 20</Pill>}
            avatar={false}
          />
          <Row
            name={f[0].lines[0]}
            meta={f[0].title}
            right={<Pill tone="wait">3</Pill>}
            avatar={false}
          />
        </div>
        <div className="rounded-xl border border-slate-200/80 p-3">
          <p className="text-[11px] font-semibold text-slate-800">{t.demo.sidebar[3]}</p>
          <Row
            name="Karimov A."
            meta="1 500 000"
            right={<Pill tone="wait">{locale === 'uz' ? 'kutilmoqda' : 'ожидает'}</Pill>}
          />
          <Row
            name="Rasulova M."
            meta="1 500 000"
            right={<Pill tone="ok">{locale === 'uz' ? 'to‘landi' : 'оплачено'}</Pill>}
          />
          <Row
            name="Yusupov S."
            meta="600 000"
            right={<Pill tone="debt">{locale === 'uz' ? 'qarz' : 'долг'}</Pill>}
          />
        </div>
        <div className="hidden rounded-xl border border-slate-200/80 p-3 sm:block">
          <p className="text-[11px] font-semibold text-slate-800">{t.demo.sidebar[6]}</p>
          <Row
            name={f[5].lines[0].split(' · ')[0]}
            meta={f[5].lines[1]}
            right={<Pill tone="neutral">24</Pill>}
            avatar={false}
          />
          <Row
            name={f[2].lines[1]}
            meta={f[2].title}
            right={<Pill tone="ok">✓</Pill>}
            avatar={false}
          />
        </div>
        <div className="hidden rounded-xl border border-slate-200/80 p-3 sm:block">
          <p className="text-[11px] font-semibold text-slate-800">{t.demo.sidebar[7]}</p>
          <Row
            name={f[6].lines[0]}
            meta={f[3].lines[1].split(' · ')[0]}
            right={
              <Pill tone="neutral">{locale === 'uz' ? 'chek biriktirilgan' : 'чек приложен'}</Pill>
            }
            avatar={false}
          />
        </div>
      </div>
    </Frame>
  )
}

export function Problem({ locale }: { locale: Locale }) {
  const t = copy[locale].problem
  const ref = useRef<HTMLElement>(null)
  const progress = useScene(ref)
  const compact = useCompact()
  const isStatic = useStatic()
  const factor = compact ? 0.38 : 1

  const windowOpacity = useTransform(progress, [0.5, 0.72], [0, 1])
  const windowScale = useTransform(progress, [0.5, 0.75], [0.92, 1])
  const windowY = useTransform(progress, [0.5, 0.75], [40, 0])
  const labelOpacity = useTransform(progress, [0.72, 0.85], [0, 1])
  const headY = useTransform(progress, [0, 0.4], [0, compact ? -10 : -30])

  if (isStatic) {
    return (
      <section ref={ref} id="problem" className="bg-slate-50 py-20 lg:py-28">
        <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
          <Heading t={t} />
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            {t.fragments.map((fragment, i) => (
              <Paper
                key={fragment.title}
                fragment={fragment}
                className={i % 2 ? 'rotate-2' : '-rotate-2'}
              />
            ))}
          </div>
          <div className="mt-10 flex justify-center">
            <Resolved locale={locale} compact={compact} />
          </div>
        </div>
      </section>
    )
  }

  return (
    <section
      ref={ref}
      id="problem"
      className="relative bg-slate-50"
      style={{ height: compact ? '230vh' : '280vh' }}
    >
      <div className="sticky top-0 flex h-screen flex-col overflow-hidden pt-[76px]">
        <motion.div
          style={{ y: headY }}
          className="mx-auto w-full max-w-[1280px] px-5 pt-6 lg:px-8 lg:pt-10"
        >
          <Heading t={t} />
        </motion.div>

        <div className="relative mx-auto w-full max-w-[1280px] flex-1 px-5 lg:px-8">
          {t.fragments.map((fragment, i) => (
            <FlyingPaper
              key={fragment.title}
              fragment={fragment}
              index={i}
              progress={progress}
              factor={factor}
            />
          ))}

          <div className="absolute inset-x-5 inset-y-0 flex items-center justify-center lg:inset-x-8">
            <motion.div
              style={{ opacity: windowOpacity, scale: windowScale, y: windowY }}
              className="w-full max-w-3xl will-change-transform"
            >
              <Resolved locale={locale} compact={compact} />
            </motion.div>
          </div>

          <motion.p
            style={{ opacity: labelOpacity }}
            className="pointer-events-none absolute bottom-6 left-1/2 -translate-x-1/2 rounded-full bg-slate-950 px-4 py-1.5 text-sm font-semibold text-white"
          >
            {t.resolved}
          </motion.p>
        </div>
      </div>
    </section>
  )
}

function Heading({ t }: { t: Copy['problem'] }) {
  return (
    <div className="mx-auto max-w-3xl text-center">
      <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
        {t.eyebrow}
      </p>
      <h2 className="mt-3 text-balance text-[1.75rem] font-extrabold !leading-[1.08] tracking-[-0.03em] text-slate-950 sm:text-4xl lg:text-[2.75rem]">
        {t.title}
      </h2>
      <p className="mx-auto mt-4 hidden max-w-2xl text-base leading-7 text-slate-600 sm:block lg:text-lg">
        {t.text}
      </p>
    </div>
  )
}
