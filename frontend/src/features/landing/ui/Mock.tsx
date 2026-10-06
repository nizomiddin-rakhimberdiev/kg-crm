/**
 * "Jonli" mahsulot ko'rinishi — HTML/CSS bilan chizilgan Radix UI.
 *
 * Skrinshot emas: har bir raqam, ustun va qator — element. Shuning uchun
 * ular scroll bilan alohida harakatlana oladi (kattalashadi, sanaydi,
 * filtrlanadi). Ranglar va shakllar haqiqiy CRM (`features/dashboard`)
 * bilan bir xil oilada — mijoz demo'ga kirganda «boshqa mahsulot» ko'rmaydi.
 *
 * Barcha raqamlar NAMUNAVIY (content.ts `demo.note`).
 */

import type { ReactNode } from 'react'
import {
  AlertTriangle,
  BarChart3,
  Boxes,
  CalendarCheck,
  LayoutDashboard,
  Receipt,
  Users,
  UserRound,
  Wallet,
} from 'lucide-react'
import { RadixMark } from '@/components/brand/Logo'
import { type Copy, groupThousands } from '../content'

const ICONS = [
  LayoutDashboard,
  UserRound,
  Users,
  Wallet,
  AlertTriangle,
  CalendarCheck,
  Users,
  Boxes,
  BarChart3,
]

export function Frame({
  demo,
  active = 0,
  children,
  className = '',
  compact = false,
}: {
  demo: Copy['demo']
  active?: number
  children: ReactNode
  className?: string
  compact?: boolean
}) {
  return (
    <div
      className={`overflow-hidden rounded-2xl border border-slate-200/80 bg-white text-left shadow-[0_30px_80px_-30px_rgba(18,53,47,0.25)] ${className}`}
    >
      <div className="flex">
        {!compact && (
          <aside className="hidden w-44 shrink-0 border-r border-slate-100 bg-slate-50/70 p-3 sm:block">
            <div className="flex items-center gap-2 px-2 py-1.5">
              <RadixMark size={24} />
              <span className="truncate text-[12px] font-semibold text-slate-800">{demo.org}</span>
            </div>
            <ul className="mt-3 space-y-0.5">
              {demo.sidebar.map((item, index) => {
                const Icon = ICONS[index] ?? Users
                const on = index === active
                return (
                  <li
                    key={item}
                    className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-[12px] ${
                      on ? 'bg-brand-50 font-semibold text-brand-700' : 'text-slate-500'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <span className="truncate">{item}</span>
                  </li>
                )
              })}
            </ul>
          </aside>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-2.5">
            {/*
              Ilgari bu yerda bo'sh kulrang to'rtburchak turardi va u
              telefonda "yuklanmagan skelет" bo'lib ko'rinardi —
              mahsulot tayyor emasdek. Endi oyna sarlavhasi: qaysi
              ekran ochiq ekani yoziladi.
            */}
            <p className="truncate text-[13px] font-semibold text-slate-800">
              {demo.sidebar[active] ?? demo.sidebar[0]}
            </p>
            <div className="flex items-center gap-2">
              <span className="hidden whitespace-nowrap text-[12px] text-slate-500 sm:block">
                {demo.today}
              </span>
              <span className="grid h-6 w-6 place-items-center rounded-full bg-amber-100 text-[12px] font-bold text-amber-800">
                DR
              </span>
            </div>
          </div>
          <div className="p-4">{children}</div>
        </div>
      </div>
    </div>
  )
}

// Ko'rsatkich ikonkalari — ma'nosiga qarab, bezakka qarab emas:
// bolalar va pul Nihol, davomat Ildiz, qarzdorlik O'rik, xodimlar Tosh.
const TONES = [
  'bg-nihol-50 text-nihol-600',
  'bg-ildiz-50 text-ildiz-700',
  'bg-orik-100 text-orik-700',
  'bg-nihol-100 text-nihol-700',
  'bg-tosh-100 text-tosh-600',
]
const KPI_ICONS = [Users, CalendarCheck, AlertTriangle, Wallet, UserRound]

export function Kpi({
  kpi,
  index,
  valueNode,
  money,
  emphasis = false,
}: {
  kpi: Copy['demo']['kpis'][number]
  index: number
  valueNode?: ReactNode
  money?: boolean
  emphasis?: boolean
}) {
  const Icon = KPI_ICONS[index] ?? Users
  return (
    <div
      className={`min-w-0 rounded-xl border bg-white p-3 transition-colors ${
        emphasis ? 'border-brand-300 ring-4 ring-brand-500/10' : 'border-slate-200/80'
      }`}
    >
      <span className={`grid h-7 w-7 place-items-center rounded-lg ${TONES[index] ?? TONES[0]}`}>
        <Icon className="h-3.5 w-3.5" />
      </span>
      <p className="num mt-2.5 truncate text-[14px] font-bold tracking-tight text-slate-950 sm:text-[15px]">
        {valueNode ?? (money ? groupThousands(kpi.value) : kpi.value)}
        {kpi.suffix ?? ''}
      </p>
      {/* Ikki qatorgacha, `truncate` emas (PLAN 5.7): 12px da
          "120 / 128 belgilangan" bir qatorga sig'masdi va "belgila…"
          bo'lib kesilardi — ya'ni raqamning ma'nosi yo'qolardi. */}
      <p className="line-clamp-2 text-[12px] font-medium leading-4 text-slate-600">{kpi.label}</p>
      <p className="mt-0.5 line-clamp-2 text-[12px] leading-4 text-slate-500">{kpi.hint}</p>
    </div>
  )
}

/** Oddiy ustunli diagramma — SVG, `progress` (0..1) bilan chiziladi. */
export function Bars({
  values,
  labels,
  progress = 1,
  className = '',
}: {
  values: number[]
  labels: string[]
  progress?: number
  className?: string
}) {
  const max = Math.max(...values)
  return (
    <div className={className}>
      <div className="flex h-24 gap-2 sm:h-28">
        {values.map((v, i) => (
          <div key={i} className="flex h-full flex-1 flex-col items-center gap-1">
            <div className="flex w-full flex-1 items-end">
              <div
                className="w-full rounded-t-md bg-brand-600/90"
                style={{
                  height: `${(v / max) * 100 * Math.min(1, Math.max(0, progress * 1.4 - i * 0.08))}%`,
                  transition: 'height 0.25s ease-out',
                }}
              />
            </div>
            <span className="text-[12px] text-slate-500">{labels[i]}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function Pill({
  tone,
  children,
}: {
  tone: 'ok' | 'wait' | 'debt' | 'neutral'
  children: ReactNode
}) {
  const cls = {
    ok: 'bg-nihol-50 text-nihol-700',
    wait: 'bg-orik-100 text-orik-900',
    debt: 'bg-orik-50 text-orik-900',
    neutral: 'bg-tosh-100 text-tosh-600',
  }[tone]
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-full px-2 py-0.5 text-[12px] font-semibold ${cls}`}
    >
      {children}
    </span>
  )
}

export function Row({
  name,
  meta,
  right,
  avatar = true,
  active = false,
}: {
  name: string
  meta?: string
  right?: ReactNode
  avatar?: boolean
  active?: boolean
}) {
  return (
    <div
      className={`flex items-center gap-2.5 rounded-lg px-2 py-1.5 ${active ? 'bg-brand-50' : ''}`}
    >
      {avatar && (
        <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-slate-100 text-[12px] font-bold text-slate-600">
          {name
            .split(' ')
            .map((p) => p[0])
            .join('')
            .slice(0, 2)}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-[12px] font-semibold text-slate-800">{name}</p>
        {meta && <p className="truncate text-[12px] text-slate-500">{meta}</p>}
      </div>
      {right}
    </div>
  )
}

export { Receipt }
