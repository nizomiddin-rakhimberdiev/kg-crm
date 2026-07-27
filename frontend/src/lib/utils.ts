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
