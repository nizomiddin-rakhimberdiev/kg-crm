/**
 * CRM ilovasining tili (docs/05 §18, docs/02 ADR-16).
 *
 * Qoida oddiy: kodda matn O'ZBEKCHA yoziladi va `t('…')` bilan o'raladi;
 * ruscha va inglizcha lug'atlar (`messages/ru.ts`, `messages/en.ts`)
 * o'sha o'zbekcha matnni kalit qilib oladi. Tarjima topilmasa — manba
 * qaytadi, ya'ni tizim hech qachon bo'sh yoki «undefined» ko'rsatmaydi;
 * lug'at to'liqligini esa test tekshiradi (`__tests__/catalog.test.ts`).
 *
 * Til ILOVA YUKLANISHIDA bir marta o'qiladi va o'zgartirilganda sahifa
 * qayta yuklanadi. Shu tufayli `t()` sof funksiya: modul darajasidagi
 * konstantalarda ham (`STATUS_LABELS`), hook ichida ham, JSX'da ham
 * ishlaydi — React konteksti, provayder yoki qayta render kerak emas.
 * Narx: tilni almashtirish bir reload; foyda: 700+ satr uchun bitta
 * oddiy mexanizm va nolga teng ishga tushirish tartibi xatolari.
 *
 * Lug'at `initI18n()` da (main.tsx, ilova modullaridan OLDIN) yuklanadi:
 * o'zbek uchun hech narsa yuklanmaydi, ru/en uchun bitta kichik chunk.
 */

export type AppLocale = 'uz' | 'ru' | 'en'

export const APP_LOCALES: { code: AppLocale; label: string; short: string }[] = [
  { code: 'uz', label: 'O‘zbekcha', short: 'UZ' },
  { code: 'ru', label: 'Русский', short: 'RU' },
  { code: 'en', label: 'English', short: 'EN' },
]

export const LOCALE_STORAGE_KEY = 'kg-crm.locale'

const isLocale = (value: unknown): value is AppLocale =>
  value === 'uz' || value === 'ru' || value === 'en'

function detect(): AppLocale {
  if (typeof window === 'undefined') return 'uz'
  try {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY)
    if (isLocale(stored)) return stored
  } catch {
    // Maxfiy rejim yoki bloklangan storage — sukut tili.
  }
  return 'uz'
}

/** Joriy til — ilova yuklanganda bir marta aniqlanadi. */
export const locale: AppLocale = detect()

/** Tilni saqlab, sahifani qayta yuklaydi (yuqoridagi izohga qarang). */
export function setLocale(next: AppLocale) {
  if (next === locale) return
  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, next)
  } catch {
    // Storage yo'q bo'lsa ham reload qilamiz — bu safar uchun `?lang` yo'q,
    // shunchaki sukut tili qoladi; foydalanuvchi buni ko'radi.
  }
  window.location.reload()
}

type Catalog = Record<string, string>
let catalog: Catalog = {}

/** Lug'atni yuklaydi. `main.tsx` buni ilova modullaridan oldin kutadi. */
export async function initI18n(): Promise<void> {
  if (typeof document !== 'undefined') document.documentElement.lang = locale
  if (locale === 'uz') return
  const mod = locale === 'ru' ? await import('./messages/ru') : await import('./messages/en')
  catalog = mod.messages
}

/** Testlar uchun: lug'atni to'g'ridan-to'g'ri o'rnatish. */
export function setCatalogForTests(next: Catalog) {
  catalog = next
}

/**
 * Tarjima. `{name}` o'rinbosarlari `vars` dan to'ldiriladi — tarjimada
 * so'z tartibi boshqacha bo'lishi mumkin, shuning uchun qo'shib yozish
 * (`'Jami ' + n + ' ta'`) emas, o'rinbosar ishlatiladi.
 */
export function t(
  source: string,
  vars?: Record<string, string | number | null | undefined>,
): string {
  const text = catalog[source] ?? source
  if (!vars) return text
  return text.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in vars ? String(vars[key] ?? '') : match,
  )
}

/** Sana/raqam formatlash uchun BCP-47 tegi. */
export const INTL_LOCALE: Record<AppLocale, string> = {
  uz: 'uz-UZ',
  ru: 'ru-RU',
  en: 'en-GB',
}
