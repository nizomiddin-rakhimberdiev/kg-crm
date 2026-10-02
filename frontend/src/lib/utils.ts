import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Merge Tailwind class names, resolving conflicts. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/*
 * Formatlash — `@/lib/format` da (PLAN 4.1).
 *
 * Bu yerdagi nomlar ESKI import joylari uchun saqlangan (55 fayl) va
 * ular endi yagona uyga qarab turadi. Ikkita ta'rif bo'lsa, ular
 * ertami-kechmi ajralib ketadi — auditda aynan shunday bo'lgan:
 * bu fayl `en-US` vergul bilan formatlardi, sahifalar esa `uz-UZ`
 * bo'shliq bilan, va bitta summa ikki ekranda ikki xil ko'rinardi.
 *
 * Yangi kod to'g'ridan-to'g'ri `@/lib/format` dan oladi.
 */
export {
  MONTHS,
  UZ_MONTHS,
  formatDate,
  formatDateLong,
  formatDateTime,
  isoDate,
  today,
} from '@/lib/format'

export {
  compact as formatCompact,
  money as formatMoney,
  signed as formatSigned,
  som as formatUZS,
} from '@/lib/format'

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
  'bg-nihol-100 text-nihol-800',
  'bg-orik-100 text-orik-800',
  'bg-ildiz-100 text-ildiz-800',
  'bg-tosh-200 text-tosh-700',
  'bg-nihol-200 text-nihol-900',
  'bg-orik-200 text-orik-900',
] as const

export function avatarTone(seed: string): string {
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  return AVATAR_TONES[hash % AVATAR_TONES.length]
}
