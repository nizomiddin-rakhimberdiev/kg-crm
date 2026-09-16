/**
 * Vendor xodimining "bog'chaga kirish" sessiyasi (ADR-10).
 *
 * Token konsoldan mijoz ilovasiga shu modul orqali o'tadi. U URL'ga
 * YOZILMAYDI — manzil brauzer tarixida, server loglarida va `Referer`
 * sarlavhasida qoladi, ya'ni qisqa muddatli token ham u yerda uzoq
 * yashaydi. Ikkala tekislik bitta origin'da bo'lgani uchun `localStorage`
 * yetarli: konsol yozadi, mijoz ilovasi darhol o'qib O'CHIRADI.
 */

const HANDOFF_KEY = 'kg_crm_support_handoff'

export const supportHandoff = {
  stash(token: string) {
    try {
      localStorage.setItem(HANDOFF_KEY, token)
    } catch {
      /* private rejim — kirish ishlamaydi, lekin jimgina buzilmaydi */
    }
  },

  /** Bir martalik o'qish: qiymat darhol o'chiriladi. */
  take(): string | null {
    try {
      const token = localStorage.getItem(HANDOFF_KEY)
      localStorage.removeItem(HANDOFF_KEY)
      return token
    } catch {
      return null
    }
  },
}

/**
 * Joriy sahifa qo'llab-quvvatlash sessiyasidami?
 *
 * Faqat XOTIRADA saqlanadi — sahifa yangilansa sessiya tugaydi va bu
 * to'g'ri: qo'llab-quvvatlash sessiyasi vaqtinchalik bo'lishi kerak.
 *
 * Bayroq ikki ishni qiladi: interfeysda ogohlantirish chizig'ini
 * ko'rsatadi va tokenni yangilashni BLOKLAYDI. Ikkinchisi muhim —
 * brauzerda o'sha bog'chaning eski refresh tokeni qolgan bo'lsa,
 * `401` dan keyingi avtomatik yangilash faqat-o'qish sessiyasini
 * jimgina to'liq sessiyaga aylantirib yuborardi.
 */
let active = false

export const supportSession = {
  isActive: (): boolean => active,
  mark: () => {
    active = true
  },
}
