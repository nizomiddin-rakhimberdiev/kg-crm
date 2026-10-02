/**
 * Bolaning oylik narxi — forma qiymati va API maydonlari orasidagi o'tish.
 * Komponent: `components/PricePicker.tsx`.
 */

import { t } from '@/lib/i18n'

export interface PriceValue {
  tariffId: string | null
  /** `null` — tarif rejimi; satr — individual narx (so'mda). */
  monthlyFee: string | null
}

/** Bo'sh joy va ajratuvchilarni olib tashlaydi: "1 250 000" → "1250000". */
export const digitsOnly = (raw: string) => raw.replace(/[^\d]/g, '')

/**
 * Formadagi qiymatni API maydonlariga o'giradi.
 * Individual rejimda summa bo'lmasa — `error` qaytadi (so'rov yuborilmaydi).
 */
export function priceToPayload(value: PriceValue): {
  payload: { tariff_id: string | null; monthly_fee: string | null }
  error: string | null
} {
  if (value.monthlyFee === null) {
    return { payload: { tariff_id: value.tariffId, monthly_fee: null }, error: null }
  }
  const amount = digitsOnly(value.monthlyFee)
  if (!amount || Number(amount) <= 0) {
    return {
      payload: { tariff_id: null, monthly_fee: null },
      error: t("Individual narxni kiriting (so'mda, 0 dan katta)."),
    }
  }
  return { payload: { tariff_id: null, monthly_fee: amount }, error: null }
}

/** Serverdagi bola holatidan forma qiymati. */
export function priceFromChild(child: {
  tariff: string | null
  monthly_fee: string | null
}): PriceValue {
  return child.monthly_fee !== null
    ? { tariffId: null, monthlyFee: String(Math.round(Number(child.monthly_fee))) }
    : { tariffId: child.tariff, monthlyFee: null }
}
