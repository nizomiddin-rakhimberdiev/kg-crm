/**
 * To'lov usullari — nom, rang va nishon BITTA joyda.
 *
 * Ilgari har bir ekran o'z ro'yxatini tutardi va ular ajralib ketgan
 * edi: hisobotlar sahifasida `bank_transfer` tarjimasiz, xom kod
 * bo'lib chiqardi (mijoz shuni ko'rsatdi). Yangi usul qo'shilganda
 * uni yana uch joyda eslash kerak bo'lmasligi uchun ro'yxat shu
 * faylda yashaydi.
 */

import {
  Banknote,
  Building2,
  CreditCard,
  Globe,
  Smartphone,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import { BRAND, CHART } from '@/lib/brand'
import { t } from '@/lib/i18n'

/**
 * Usullar — mijozning o'z lug'ati bilan (docs/03 §13.5).
 * `card` qiymati 2026-09-30 da `terminal` ga o'zgartirildi; Click va
 * Payme 2026-10-15 dan alohida (Bosqich 12.4) — `online` faqat eski
 * yozuvlar uchun qoladi.
 */
export const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: t('Naqd'),
  terminal: t('Terminal'),
  bank_transfer: t('Oʻtkazma'),
  click: 'Click',
  payme: 'Payme',
  payroll: t('Oylikdan ushlash'),
  online: t('Payme / Click'),
}

/** Kassir tugmalari — tartibi ekranda ko'rinadigan tartib. */
export const PAYMENT_METHODS: readonly string[] = [
  'cash',
  'terminal',
  'bank_transfer',
  'click',
  'payme',
]

/**
 * Filtr va hisobotlar uchun. `payroll` kassir tugmalarida alohida: u
 * xodimni so'raydi. Eski `online` ro'yxatda YO'Q (audit 2026-11-12, H8):
 * alohida Click va Payme yonida "Payme / Click" ortiqcha edi; eski
 * yozuvlarda u baribir o'z nomi bilan ko'rinadi (`paymentMethodLabel`).
 */
export const ALL_PAYMENT_METHODS: readonly string[] = [...PAYMENT_METHODS, 'payroll']

/** Noma'lum kod ham xom ko'rinmasin: baribir o'qiladigan matn qaytadi. */
export const paymentMethodLabel = (method: string): string =>
  PAYMENT_METHOD_LABELS[method] ?? method

/** Diagramma va ajratmalar uchun — usul bo'yicha barqaror rang. */
export const PAYMENT_METHOD_COLORS: Record<string, string> = {
  cash: BRAND.nihol,
  terminal: BRAND.ildiz,
  bank_transfer: BRAND.orik,
  click: CHART.niholSoft,
  payme: CHART.ildizMid,
  payroll: CHART.axis,
  online: CHART.niholSoft,
}

export const paymentMethodColor = (method: string): string =>
  PAYMENT_METHOD_COLORS[method] ?? CHART.axis

const ICONS: Record<string, LucideIcon> = {
  cash: Banknote,
  terminal: CreditCard,
  bank_transfer: Building2,
  click: Smartphone,
  payme: Smartphone,
  payroll: Wallet,
  online: Globe,
}

export const paymentMethodIcon = (method: string): LucideIcon => ICONS[method] ?? Banknote
