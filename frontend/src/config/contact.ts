/**
 * Sotuv aloqalari — public saytdagi YAGONA manba (PLAN 5.7).
 *
 * Header, mobil menyu, footer va demo forma shu fayldan oʻqiydi: raqam
 * bir joyda oʻzgaradi. Sirlar emas, ochiq biznes aloqalari — shuning
 * uchun `.env` da emas, kodda (sayt build paytida prerender qilinadi).
 *
 * Yuridik shaxs maʼlumotlari (nomi, STIR, manzili) esa `.env` da
 * (`VITE_LEGAL_*`, `config/env.ts`): ular hali toʻldirilmagan va boʻsh
 * boʻlsa saytda koʻrinmaydi — `{{STIR}}` degan yozuv chiqmasligi kerak.
 *
 * Ikkala raqam egasi tasdiqlagan (2026-10-03): brief'da birinchisi
 * `+999…` deb xato yozilgan edi, to'g'risi `+998947267726`.
 */

export const CONTACT = {
  /** E.164 (Q7). Birinchisi — header'dagi asosiy raqam. */
  phones: ['+998947267726', '+998950767726'],
  telegram: 'nizomiddin_rakhimberdiev',
  email: 'ranizomiddin@gmail.com',
} as const

/** `+998950767726` → `+998 95 076 77 26`. */
export function formatPhone(e164: string): string {
  const match = /^\+998(\d{2})(\d{3})(\d{2})(\d{2})$/.exec(e164)
  return match ? `+998 ${match[1]} ${match[2]} ${match[3]} ${match[4]}` : e164
}

export const telegramUrl = `https://t.me/${CONTACT.telegram}`
