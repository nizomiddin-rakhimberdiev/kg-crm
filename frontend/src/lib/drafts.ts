/**
 * Saqlanmagan formalar qoralamasi (mijoz soʻrovi, 2026-10-14).
 *
 * Mijoz: *"bola qoʻshish yoki chiqim qoʻshish formasiga maʼlumot yozib
 * qoʻyilsa, lekin saqlash bosilmasdan boshqa boʻlimga oʻtib qaytib
 * kelinsa, forma tozalanib ketmoqda"*. Sabab oddiy: sahifa komponenti
 * yopiladi va uning `useState` i bilan birga yoʻqoladi.
 *
 * **Nega `sessionStorage`, `localStorage` emas.** Bola qoʻshish
 * formasida bolaning va vasiyning shaxsiy maʼlumoti bor. `sessionStorage`
 * shu brauzer YORLIGʻIDA yashaydi va u yopilganda oʻzi oʻchadi;
 * `localStorage` esa umumiy kompyuterda kunlab qolardi.
 *
 * **Chiqishda hammasi tozalanadi** (`clearAllDrafts`, AuthProvider):
 * bitta yorliqda bir xodim chiqib, boshqasi kirsa, birinchisining
 * qoralamasi qolmasligi kerak. Kalitda foydalanuvchi ID'si ham bor —
 * ikkinchi himoya qatlami.
 *
 * Har bir chaqiruv `try` ichida: xususiy rejim yoki toʻlgan xotira
 * xatoga emas, oddiy "qoralama yoʻq" ga olib keladi.
 */

const PREFIX = 'radix:draft:'

function storage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.sessionStorage
  } catch {
    return null
  }
}

export function draftKey(userId: string | undefined, form: string): string | null {
  return userId ? `${PREFIX}${userId}:${form}` : null
}

export function readDraft<T>(key: string | null): T | null {
  if (!key) return null
  try {
    const raw = storage()?.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

export function writeDraft(key: string | null, value: unknown): void {
  if (!key) return
  try {
    storage()?.setItem(key, JSON.stringify(value))
  } catch {
    // Xotira toʻla yoki taqiqlangan — qoralamasiz ishlayveramiz.
  }
}

export function clearDraft(key: string | null): void {
  if (!key) return
  try {
    storage()?.removeItem(key)
  } catch {
    // ahamiyatsiz
  }
}

/** Chiqishda — barcha qoralamalar, kimniki boʻlishidan qatʼi nazar. */
export function clearAllDrafts(): void {
  const store = storage()
  if (!store) return
  try {
    const keys: string[] = []
    for (let i = 0; i < store.length; i += 1) {
      const key = store.key(i)
      if (key?.startsWith(PREFIX)) keys.push(key)
    }
    keys.forEach((key) => store.removeItem(key))
  } catch {
    // ahamiyatsiz
  }
}
