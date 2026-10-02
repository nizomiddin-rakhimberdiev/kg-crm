/**
 * Vendor konsolidagi xom enum qiymatlarining oʻzbekcha nomlari (PLAN 5.12).
 *
 * Konsol faqat oʻzbek tilida (ADR-16), shuning uchun `t()` emas — oddiy
 * lugʻat. Ilgari ekranda `semiannual`, `issued`, `standard` kabi kod
 * nomlari chiqib turardi: ular dasturchi uchun, mijoz bilan telefonda
 * gaplashayotgan odam uchun emas.
 *
 * Nomaʼlum qiymat — oʻzi koʻrsatiladi (`label()`): yangi holat
 * qoʻshilganda ekran boʻsh qolmaydi, faqat tarjimasiz koʻrinadi.
 */

export const PAYMENT_TERM: Record<string, string> = {
  monthly: 'Oylik',
  semiannual: 'Yarim yillik',
  annual: 'Yillik',
}

export const INVOICE_STATUS: Record<string, string> = {
  issued: 'Yozilgan',
  paid: 'Toʻlangan',
  overdue: 'Muddati oʻtgan',
  cancelled: 'Bekor qilingan',
}

export const PAYMENT_METHOD: Record<string, string> = {
  bank_transfer: 'Bank oʻtkazmasi',
  card: 'Karta',
  cash: 'Naqd',
}

export const USAGE_METHOD: Record<string, string> = {
  daily_peak: 'Kunlik eng yuqori',
  manual_adjustment: 'Qoʻlda tuzatish',
}

export const PLAN: Record<string, string> = {
  standard: 'Standart',
}

export const label = (map: Record<string, string>, value: string | null | undefined): string =>
  value ? (map[value] ?? value) : '—'
