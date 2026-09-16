/**
 * Token saqlash (docs/05 §12).
 *
 * Access token **xotirada** — u qisqa yashaydi va uni `localStorage` da
 * saqlash XSS uchun bepul o'lja bo'lardi.
 *
 * Refresh token `localStorage` da: sahifa yangilanganda sessiya
 * yo'qolmasligi kerak. Bu ideal emas (XSS uni ham o'g'irlaydi), lekin
 * MVP uchun ongli murosa — httpOnly cookie'ga o'tish uchun backend
 * CSRF himoyasi bilan birga qayta ishlanadi va bu alohida qaror.
 *
 * **Kalit bog'cha MANZILI bilan nomlanadi.** Barcha bog'chalar bitta
 * origin'da yashaydi (`/t/<slug>`), ya'ni ular bitta `localStorage` ni
 * bo'lishadi. Bitta kalit bo'lganda ikki bog'chada ishlaydigan odam —
 * masalan bir necha bog'chaga xizmat qiladigan buxgalter — ikkinchisiga
 * kirishi bilan birinchisidan chiqib ketardi. Subdomenga o'tilganda har
 * bir bog'cha o'z origin'ini oladi va bu masala o'z-o'zidan yo'qoladi;
 * shu paytgacha nom bilan ajratamiz.
 */

import { currentSlug } from '@/lib/tenantAddress'

const BASE_KEY = 'kg_crm_refresh'

const keyFor = (slug: string | null): string => (slug ? `${BASE_KEY}:${slug}` : BASE_KEY)

let accessToken: string | null = null

export const tokenStorage = {
  getAccess: (): string | null => accessToken,

  setAccess(token: string | null) {
    accessToken = token
  },

  getRefresh(slug: string | null = currentSlug): string | null {
    try {
      return localStorage.getItem(keyFor(slug))
    } catch {
      return null
    }
  },

  /**
   * `slug` ataylab beriladigan parametr: kirish paytida foydalanuvchi
   * hali o'z manzilida turmagan bo'lishi mumkin (`/login` dan kirdi), va
   * token DARHOL to'g'ri kalit ostida yozilishi kerak — aks holda
   * manzilga o'tishda u yo'qolardi.
   */
  setRefresh(token: string | null, slug: string | null = currentSlug) {
    try {
      if (token) localStorage.setItem(keyFor(slug), token)
      else localStorage.removeItem(keyFor(slug))
    } catch {
      /* private rejimda localStorage bloklanadi — sessiya shu tab bilan cheklanadi */
    }
  },

  clear() {
    accessToken = null
    this.setRefresh(null)
  },
}
