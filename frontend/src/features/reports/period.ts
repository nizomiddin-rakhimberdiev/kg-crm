/**
 * Hisobot davri — sof funksiyalar, React'siz (test qilish oson).
 *
 * Davr ikki narsadan iborat: `preset` (kun/hafta/oy/chorak/yil/ixtiyoriy)
 * va `[from, to]` chegaralar. Preset bo'yicha oldinga-orqaga yurish
 * mumkin; `custom` da chegaralar qo'lda kiritiladi.
 *
 * Sanalar MAHALLIY: `toISOString()` UTC'ga o'girib, Toshkentda kechqurun
 * soat 19:00 dan keyin "ertangi" kunni bugun deb ko'rsatardi.
 */

import type { ReportGroupBy } from '@/lib/api/types'
import { UZ_MONTHS } from '@/lib/utils'

export type PeriodPreset = 'day' | 'week' | 'month' | 'quarter' | 'year' | 'custom'

export interface Period {
  preset: PeriodPreset
  /** ISO `YYYY-MM-DD` */
  from: string
  to: string
}

export const PRESETS: Array<{ key: PeriodPreset; label: string }> = [
  { key: 'day', label: 'Kun' },
  { key: 'week', label: 'Hafta' },
  { key: 'month', label: 'Oy' },
  { key: 'quarter', label: 'Chorak' },
  { key: 'year', label: 'Yil' },
  { key: 'custom', label: 'Ixtiyoriy' },
]

const MONTHS = UZ_MONTHS
const MONTHS_SHORT = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']
const ROMAN = ['I', 'II', 'III', 'IV']

const pad = (n: number) => String(n).padStart(2, '0')

export function toISODate(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function parseISODate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, (m ?? 1) - 1, d ?? 1)
}

const addDays = (date: Date, days: number) =>
  new Date(date.getFullYear(), date.getMonth(), date.getDate() + days)
const addMonths = (date: Date, months: number) =>
  new Date(date.getFullYear(), date.getMonth() + months, 1)
const lastDayOfMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth() + 1, 0)

/** Sana tushadigan davr — preset bo'yicha. `custom` uchun sana o'zi. */
export function periodFor(preset: PeriodPreset, anchor: Date): Period {
  switch (preset) {
    case 'day':
      return { preset, from: toISODate(anchor), to: toISODate(anchor) }
    case 'week': {
      // ISO: dushanba — backend `TruncWeek` bilan bir xil.
      const offset = (anchor.getDay() + 6) % 7
      const monday = addDays(anchor, -offset)
      return { preset, from: toISODate(monday), to: toISODate(addDays(monday, 6)) }
    }
    case 'month': {
      const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1)
      return { preset, from: toISODate(first), to: toISODate(lastDayOfMonth(first)) }
    }
    case 'quarter': {
      const startMonth = Math.floor(anchor.getMonth() / 3) * 3
      const first = new Date(anchor.getFullYear(), startMonth, 1)
      const last = lastDayOfMonth(addMonths(first, 2))
      return { preset, from: toISODate(first), to: toISODate(last) }
    }
    case 'year':
      return {
        preset,
        from: `${anchor.getFullYear()}-01-01`,
        to: `${anchor.getFullYear()}-12-31`,
      }
    case 'custom':
      return { preset, from: toISODate(anchor), to: toISODate(anchor) }
  }
}

/** Bir davr oldinga (+1) yoki orqaga (−1). `custom` da uzunligicha suriladi. */
export function shiftPeriod(period: Period, direction: -1 | 1): Period {
  const from = parseISODate(period.from)
  switch (period.preset) {
    case 'day':
      return periodFor('day', addDays(from, direction))
    case 'week':
      return periodFor('week', addDays(from, 7 * direction))
    case 'month':
      return periodFor('month', addMonths(from, direction))
    case 'quarter':
      return periodFor('quarter', addMonths(from, 3 * direction))
    case 'year':
      return periodFor('year', new Date(from.getFullYear() + direction, 0, 1))
    case 'custom': {
      const to = parseISODate(period.to)
      const length = Math.round((to.getTime() - from.getTime()) / 86_400_000) + 1
      return {
        preset: 'custom',
        from: toISODate(addDays(from, length * direction)),
        to: toISODate(addDays(to, length * direction)),
      }
    }
  }
}

/** Davr necha kun. */
export function periodDays(period: Period): number {
  const from = parseISODate(period.from)
  const to = parseISODate(period.to)
  return Math.round((to.getTime() - from.getTime()) / 86_400_000) + 1
}

/**
 * Grafik kesimi — preset'dan bir pog'ona mayda: oy kunlarga, chorak
 * haftalarga, yil oylarga bo'linadi. `custom` da uzunlikka qarab.
 */
export function groupByFor(period: Period): ReportGroupBy {
  switch (period.preset) {
    case 'day':
    case 'week':
    case 'month':
      return 'day'
    case 'quarter':
      return 'week'
    case 'year':
      return 'month'
    case 'custom': {
      const days = periodDays(period)
      if (days <= 31) return 'day'
      if (days <= 120) return 'week'
      if (days <= 731) return 'month'
      return 'year'
    }
  }
}

/** Sarlavha: "18-sentabr, 2026", "15–21 sentabr 2026", "III chorak 2026". */
export function periodLabel(period: Period): string {
  const from = parseISODate(period.from)
  const to = parseISODate(period.to)
  switch (period.preset) {
    case 'day':
      return `${from.getDate()}-${MONTHS[from.getMonth()]}, ${from.getFullYear()}`
    case 'week':
      if (from.getMonth() === to.getMonth()) {
        return `${from.getDate()}–${to.getDate()} ${MONTHS[from.getMonth()]} ${from.getFullYear()}`
      }
      return `${from.getDate()} ${MONTHS[from.getMonth()]} – ${to.getDate()} ${MONTHS[to.getMonth()]} ${to.getFullYear()}`
    case 'month': {
      const name = MONTHS[from.getMonth()]
      return `${name[0].toUpperCase()}${name.slice(1)} ${from.getFullYear()}`
    }
    case 'quarter':
      return `${ROMAN[Math.floor(from.getMonth() / 3)]} chorak ${from.getFullYear()}`
    case 'year':
      return `${from.getFullYear()}-yil`
    case 'custom':
      return `${formatShort(from)} – ${formatShort(to)}`
  }
}

const formatShort = (date: Date) => `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()}`

/** Grafik o'qi uchun qisqa yorliq: davr boshi ISO sanasidan. */
export function bucketLabel(periodStart: string, groupBy: ReportGroupBy): string {
  const date = parseISODate(periodStart)
  switch (groupBy) {
    case 'day':
      return `${date.getDate()} ${MONTHS_SHORT[date.getMonth()]}`
    case 'week':
      return `${date.getDate()} ${MONTHS_SHORT[date.getMonth()]}`
    case 'month':
      return `${MONTHS_SHORT[date.getMonth()]} ${String(date.getFullYear()).slice(2)}`
    case 'quarter':
      return `${ROMAN[Math.floor(date.getMonth() / 3)]} ch. ${date.getFullYear()}`
    case 'year':
      return String(date.getFullYear())
  }
}

/** Tooltip uchun to'liq yorliq: "15–21 sentabr 2026" kabi. */
export function bucketTitle(periodStart: string, groupBy: ReportGroupBy): string {
  const date = parseISODate(periodStart)
  switch (groupBy) {
    case 'day':
      return periodLabel(periodFor('day', date))
    case 'week':
      return `Hafta: ${periodLabel(periodFor('week', date))}`
    case 'month':
      return periodLabel(periodFor('month', date))
    case 'quarter':
      return periodLabel(periodFor('quarter', date))
    case 'year':
      return periodLabel(periodFor('year', date))
  }
}
