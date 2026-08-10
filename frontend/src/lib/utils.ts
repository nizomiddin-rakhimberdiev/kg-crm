import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Merge Tailwind class names, resolving conflicts. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format a number with thousands separators, e.g. 1800000 -> "1,800,000". */
export function formatMoney(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

/** Format money with the UZS suffix, e.g. "1,800,000 UZS". */
export function formatUZS(value: number): string {
  return `${formatMoney(value)} UZS`
}

/** Compact millions formatting, e.g. 485200000 -> "485.2M". */
export function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return String(value)
}

/** Signed money, e.g. +250,000 / -450,000 (no suffix). */
export function formatSigned(value: number): string {
  const sign = value > 0 ? '+' : value < 0 ? '-' : ''
  return `${sign}${formatMoney(Math.abs(value))}`
}

/** Bosh harflar: "Abdullayev Diyor" → "AD". */
export function initials(name: string): string {
  return (
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0] ?? '')
      .join('')
      .toUpperCase() || '—'
  )
}

/**
 * Nomga qarab BARQAROR rang tanlaydi (avatar va nishonlar uchun).
 *
 * Tasodifiy emas, xesh orqali: bitta guruh yoki bola har safar bir xil
 * rangda ko'rinadi. Ro'yxatga ritm beradi, lekin ma'no bermaydi —
 * shuning uchun holat rangi (yashil/sariq) hech qachon bu yerdan olinmaydi.
 */
const AVATAR_TONES = [
  'bg-brand-100 text-brand-700',
  'bg-emerald-100 text-emerald-700',
  'bg-amber-100 text-amber-700',
  'bg-violet-100 text-violet-700',
  'bg-rose-100 text-rose-700',
  'bg-cyan-100 text-cyan-700',
] as const

export function avatarTone(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  return AVATAR_TONES[hash % AVATAR_TONES.length]
}
