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
 */

const REFRESH_KEY = 'kg_crm_refresh'

let accessToken: string | null = null

export const tokenStorage = {
  getAccess: (): string | null => accessToken,

  setAccess(token: string | null) {
    accessToken = token
  },

  getRefresh(): string | null {
    try {
      return localStorage.getItem(REFRESH_KEY)
    } catch {
      return null
    }
  },

  setRefresh(token: string | null) {
    try {
      if (token) localStorage.setItem(REFRESH_KEY, token)
      else localStorage.removeItem(REFRESH_KEY)
    } catch {
      /* private rejimda localStorage bloklanadi — sessiya shu tab bilan cheklanadi */
    }
  },

  clear() {
    accessToken = null
    this.setRefresh(null)
  },
}
