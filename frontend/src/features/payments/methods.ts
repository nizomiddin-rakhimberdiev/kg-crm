/**
 * To'lov usullarining nomlari — BITTA joyda.
 *
 * Ilgari har bir ekran o'z ro'yxatini tutardi va ular ajralib ketgan
 * edi: hisobotlar sahifasida `bank_transfer` tarjimasiz, xom kod
 * bo'lib chiqardi (mijoz shuni ko'rsatdi). Yangi usul qo'shilganda
 * uni yana uch joyda eslash kerak bo'lmasligi uchun ro'yxat shu
 * faylda yashaydi.
 */

import { t } from '@/lib/i18n'

export const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: t('Naqd'),
  card: t('Karta'),
  bank_transfer: t("Bank o'tkazmasi"),
  online: t('Onlayn'),
}

/** Noma'lum kod ham xom ko'rinmasin: baribir o'qiladigan matn qaytadi. */
export const paymentMethodLabel = (method: string): string =>
  PAYMENT_METHOD_LABELS[method] ?? method

/** Diagramma va ajratmalar uchun — usul bo'yicha barqaror rang. */
export const PAYMENT_METHOD_COLORS: Record<string, string> = {
  cash: '#10b981',
  card: '#6366f1',
  bank_transfer: '#f59e0b',
  online: '#06b6d4',
}
