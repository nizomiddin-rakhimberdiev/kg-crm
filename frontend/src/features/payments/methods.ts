/**
 * To'lov usullari — nom, rang va nishon BITTA joyda.
 *
 * Ilgari har bir ekran o'z ro'yxatini tutardi va ular ajralib ketgan
 * edi: hisobotlar sahifasida `bank_transfer` tarjimasiz, xom kod
 * bo'lib chiqardi (mijoz shuni ko'rsatdi). Yangi usul qo'shilganda
 * uni yana uch joyda eslash kerak bo'lmasligi uchun ro'yxat shu
 * faylda yashaydi.
 */

import { Banknote, Building2, CreditCard, Globe, type LucideIcon } from 'lucide-react'
import { BRAND, CHART } from '@/lib/brand'
import { t } from '@/lib/i18n'

/**
 * To'rtta usul — mijozning o'z lug'ati bilan (docs/03 §13.5).
 * `card` qiymati 2026-09-30 da `terminal` ga o'zgartirildi.
 */
export const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: t('Naqd'),
  terminal: t('Terminal'),
  bank_transfer: t('Oʻtkazma'),
  online: t('Payme / Click'),
}

/** Tanlash ro'yxatlari uchun — tartibi ekranda ko'rinadigan tartib. */
export const PAYMENT_METHODS: readonly string[] = ['cash', 'terminal', 'bank_transfer', 'online']

/** Noma'lum kod ham xom ko'rinmasin: baribir o'qiladigan matn qaytadi. */
export const paymentMethodLabel = (method: string): string =>
  PAYMENT_METHOD_LABELS[method] ?? method

/** Diagramma va ajratmalar uchun — usul bo'yicha barqaror rang. */
export const PAYMENT_METHOD_COLORS: Record<string, string> = {
  cash: BRAND.nihol,
  terminal: BRAND.ildiz,
  bank_transfer: BRAND.orik,
  online: CHART.niholSoft,
}

export const paymentMethodColor = (method: string): string =>
  PAYMENT_METHOD_COLORS[method] ?? CHART.axis

const ICONS: Record<string, LucideIcon> = {
  cash: Banknote,
  terminal: CreditCard,
  bank_transfer: Building2,
  online: Globe,
}

export const paymentMethodIcon = (method: string): LucideIcon => ICONS[method] ?? Banknote
