/**
 * Token saqlash (docs/05 §12, PLAN 5.1).
 *
 * **Access token — faqat XOTIRADA.** U qisqa yashaydi (15 daqiqa) va
 * uni `localStorage` da saqlash XSS uchun bepul oʻlja boʻlardi.
 *
 * **Refresh token — `httpOnly` cookie'da, bu yerda EMAS.** Avval u
 * `localStorage` da yashardi va bu ongli murosa edi; narxi aniq:
 * bitta zararli skript (buzilgan npm paketi, reklama kodi) uni oʻqib
 * oʻz serveriga yuborishi mumkin, va u yetti kun ishlaydi.
 * `httpOnly` cookie'ni JavaScript UMUMAN oʻqiy olmaydi — shuning
 * uchun bu modulda refresh token bilan ishlash funksiyalari ataylab
 * YOʻQ: ularni qaytarish murosani ham qaytarardi.
 *
 * Yangilash endi tanasiz soʻrov: `POST /auth/refresh` cookie'ni
 * brauzerning oʻzi qoʻshadi, biz faqat CSRF sarlavhasini yuboramiz
 * (`lib/api/client.ts`).
 *
 * **Eski kalitlar tozalanadi**: `localStorage` da qolgan token endi
 * ishlatilmaydi, lekin u yerda turishi ham kerak emas.
 */

let accessToken: string | null = null

/** Eski versiyalardan qolgan refresh kalitlari (PLAN 5.1 dan oldin). */
const LEGACY_PREFIX = 'kg_crm_refresh'

export const tokenStorage = {
  getAccess: (): string | null => accessToken,

  setAccess(token: string | null) {
    accessToken = token
  },

  clear() {
    accessToken = null
  },

  /**
   * `localStorage` dagi eski tokenlarni oʻchiradi.
   *
   * Ilova yuklanganda bir marta chaqiriladi: cookie'ga oʻtgandan
   * keyin u yerdagi qiymat foydasiz, lekin XSS uchun hamon oʻlja.
   */
  dropLegacyTokens() {
    try {
      const keys = Object.keys(localStorage).filter((key) => key.startsWith(LEGACY_PREFIX))
      for (const key of keys) localStorage.removeItem(key)
    } catch {
      /* maxfiy rejimda `localStorage` bloklanadi — tozalashga narsa ham yoʻq */
    }
  },
}
