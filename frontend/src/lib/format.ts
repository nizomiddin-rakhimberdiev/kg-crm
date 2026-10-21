/**
 * Formatlashning YAGONA uyi — pul, raqam, miqdor, sana (Q12, PLAN 4.1).
 *
 * Auditda har sahifa o'zining `money()` funksiyasini yozib olgan edi:
 * o'n yettita nusxa, va ular bir-biridan farq qilardi — biri
 * `Math.round`, biri yo'q; biri "so'm" qo'shadi, biri qo'shmaydi.
 * Natijada bitta summa ikki ekranda ikki xil ko'rinishi mumkin edi,
 * va buni hech kim sezmasdi.
 *
 * **Guruhlash tilga bog'liq** (Q12): o'zbek va rus tilida
 * bo'linmaydigan bo'shliq (`1 500 000`), inglizchada vergul
 * (`1,500,000`). `Intl` ning o'zi bu ishni bajarardi, lekin
 * natijasi brauzer va Node versiyasiga bog'liq — bir xil kod
 * serverda va ekranda boshqacha chiqsa, "nusxa olib tekshirdim,
 * boshqacha" degan shikoyat paydo bo'ladi. Shuning uchun guruhlash
 * qo'lda.
 *
 * **Pul hech qachon `float` emas.** Bu yerga `string` yoki `number`
 * keladi, lekin arifmetika bu yerda YO'Q: faqat ko'rsatish. Hisob
 * backendda `Decimal` bilan bajariladi (CLAUDE.md, invariant 3).
 */

import { locale, t } from '@/lib/i18n'

/** Bo'linmaydigan bo'shliq — raqam qatorning oxirida bo'linib ketmasin. */
const NBSP = ' '

/** Valyuta nomi (Q12). O'zbekchada apostrof U+02BB — Q11 bo'yicha. */
export const CURRENCY: Record<string, string> = {
  uz: 'soʻm',
  ru: 'сум',
  en: 'UZS',
}

const SEPARATOR = locale === 'en' ? ',' : NBSP

const toNumber = (value: string | number | null | undefined): number | null => {
  if (value === null || value === undefined || value === '') return null
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

/** Minglarni guruhlaydi: `1 500 000` (uz/ru) yoki `1,500,000` (en). */
function group(whole: string): string {
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, SEPARATOR)
}

/**
 * Butun son — guruhlangan. `null`/buzuq qiymat uchun tire.
 *
 * Tire ataylab `0` emas: "ma'lumot yo'q" va "nol" bir xil narsa emas,
 * va ularni aralashtirish hisobotda eng yomon joyda chiqadi.
 */
export function number(value: string | number | null | undefined): string {
  const parsed = toNumber(value)
  if (parsed === null) return '—'
  const rounded = Math.round(parsed)
  const sign = rounded < 0 ? '−' : ''
  return sign + group(String(Math.abs(rounded)))
}

/** Pul — guruhlangan, valyutasiz: `1 500 000`. */
export function money(value: string | number | null | undefined): string {
  return number(value)
}

/** Pul + valyuta: `1 500 000 soʻm`. */
export function som(value: string | number | null | undefined): string {
  const parsed = toNumber(value)
  if (parsed === null) return '—'
  return `${number(parsed)}${NBSP}${CURRENCY[locale] ?? CURRENCY.uz}`
}

/**
 * Ishorali summa: `+250 000` / `−450 000`.
 *
 * Minus — tipografik (U+2212), defis emas: u raqam bilan bir
 * balandlikda turadi va jadvalda ko'zga tashlanadi.
 */
export function signed(value: string | number | null | undefined): string {
  const parsed = toNumber(value)
  if (parsed === null) return '—'
  const prefix = parsed > 0 ? '+' : ''
  return prefix + number(parsed)
}

/**
 * Grafik o'qi uchun qisqa pul: `1.2 mln`, `200 ming`, `1.5 mlrd`.
 *
 * Uchta nusxa bor edi va ularning bittasi YOLG'ON gapirardi: bosh
 * sahifa o'qi summani millionga bo'lib yumaloqlardi, ya'ni 200 000
 * so'm "0 mln" deb turardi (audit, 2026-10-21). O'q grafikdagi
 * balandlikni o'qiydigan yagona narsa — u kattalikni yashirmasligi
 * kerak, shuning uchun birlik summaning O'ZIGA qarab tanlanadi.
 *
 * Birliklar tarjima qilinadi (`mln` / `млн` / `M`), chunki o'qni
 * mijozning buxgalteri ham, inglizcha interfeysdagi odam ham o'qiydi.
 */
export function axisMoney(value: string | number | null | undefined): string {
  const parsed = toNumber(value)
  if (parsed === null) return '—'
  const abs = Math.abs(parsed)
  const sign = parsed < 0 ? '−' : ''
  // Kasr qism faqat KERAK bo'lsa: "2 mln", lekin "1.2 mln".
  const short = (divisor: number) => {
    const scaled = abs / divisor
    return Number.isInteger(scaled) ? String(scaled) : scaled.toFixed(1)
  }
  if (abs >= 1_000_000_000) return `${sign}${short(1_000_000_000)}${NBSP}${t('mlrd')}`
  if (abs >= 1_000_000) return `${sign}${short(1_000_000)}${NBSP}${t('mln')}`
  if (abs >= 1_000) return `${sign}${short(1_000)}${NBSP}${t('ming')}`
  return number(parsed)
}

/**
 * Birlik kodining nomi: `pcs` → `dona`, `pack` → `quti`.
 *
 * Omborda birlik KOD bo'lib saqlanadi (`product.unit`), va u ekranda
 * ham kod bo'lib chiqardi: "12 pcs" — ayni paytda Chiqimlarda o'sha
 * narsa "dona" deb yozilardi (audit, 2026-10-21). Ro'yxatda yo'q
 * qiymat o'zgarmaydi: bog'cha o'z birligini erkin yozishi mumkin va
 * uni "tarjima qilish" uning so'zini buzardi.
 */
const UNIT_NAMES: Record<string, string> = {
  // `t()` ataylab shu yerda, chaqiruvda emas: `t(oʻzgaruvchi)` ni
  // lugʻat chiqaruvchisi koʻrmaydi (05 §17) va kalit tarjimasiz qolardi.
  pcs: t('dona'),
  pack: t('quti'),
}

export function unitLabel(unit: string | null | undefined): string {
  if (!unit) return ''
  return UNIT_NAMES[unit] ?? unit
}

/**
 * Miqdor + birlik: `12 dona`, `3.5 kg`.
 *
 * Birlik backenddan keladi (`product.unit`): ro'yxatdagi kod nomga
 * aylanadi (`unitLabel`), erkin matn esa o'zgarmaydi — faqat
 * bo'linmaydigan bo'shliq bilan qo'shiladi, ya'ni
 * "12" va "dona" qatorlar orasida ajralib qolmaydi.
 */
export function quantity(value: string | number | null | undefined, unit?: string | null): string {
  const parsed = toNumber(value)
  if (parsed === null) return '—'
  // Kasr qism faqat bor bo'lsa ko'rsatiladi: "3 kg", "3.5 kg".
  const whole = Number.isInteger(parsed)
    ? number(parsed)
    : group(String(Math.trunc(Math.abs(parsed)))) +
      String(Math.abs(parsed)).slice(String(Math.trunc(Math.abs(parsed))).length)
  const sign = parsed < 0 ? '−' : ''
  const text = Number.isInteger(parsed) ? whole : sign + whole
  return unit ? `${text}${NBSP}${unitLabel(unit)}` : text
}

/** Foiz: `92.0 %`. */
export function percent(value: string | number | null | undefined, digits = 1): string {
  const parsed = toNumber(value)
  if (parsed === null) return '—'
  return `${parsed.toFixed(digits)}${NBSP}%`
}

/* ------------------------------------------------------------ Sana */

/**
 * Sana — `toLocaleDateString('uz-UZ')` EMAS.
 *
 * Brauzerlarning `uz` lokali to'liq emas: Chromium `dateStyle: 'medium'`
 * ni "2023 M09 14" deb chiqaradi (oy nomi o'rniga "M09"). Foydalanuvchi
 * ko'radigan sana brauzerga emas, bizga bog'liq bo'lishi kerak.
 *
 * Raqamli shakl uch tilda ham `dd.mm.yyyy` (Q12) — o'zgarmas.
 */
const MONTHS_BY_LOCALE = {
  uz: [
    'yanvar',
    'fevral',
    'mart',
    'aprel',
    'may',
    'iyun',
    'iyul',
    'avgust',
    'sentabr',
    'oktabr',
    'noyabr',
    'dekabr',
  ],
  ru: [
    'января',
    'февраля',
    'марта',
    'апреля',
    'мая',
    'июня',
    'июля',
    'августа',
    'сентября',
    'октября',
    'ноября',
    'декабря',
  ],
  en: [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ],
} as const

/** Joriy tildagi oy nomlari (sana ichida: «14-sentabr» / «14 сентября»). */
export const MONTHS: readonly string[] = MONTHS_BY_LOCALE[locale]

/*
 * Yolgʻiz turgan oy nomi — sana ichidagisidan FARQ qiladi.
 *
 * Ruschada sana ichida qaratqich kelishigi kerak ("14 сентября"), yolgʻiz
 * turganda esa bosh kelishik ("Сентябрь 2026"). Oʻzbekcha va inglizchada
 * bitta shakl ishlaydi.
 */
const STANDALONE_RU = [
  'Январь',
  'Февраль',
  'Март',
  'Апрель',
  'Май',
  'Июнь',
  'Июль',
  'Август',
  'Сентябрь',
  'Октябрь',
  'Ноябрь',
  'Декабрь',
] as const

/** «Sentabr 2026» / «Сентябрь 2026» / «September 2026». */
export function monthLabel(year: number, month: number): string {
  const names = locale === 'ru' ? STANDALONE_RU : MONTHS_BY_LOCALE[locale]
  const name = names[month - 1]
  if (!name) return `${year}-${String(month).padStart(2, '0')}`
  return `${name.charAt(0).toUpperCase()}${name.slice(1)} ${year}`
}

/** Yolgʻiz turgan oy nomi: «Oktabr» / «Октябрь» / «October». */
export function monthName(month: number): string {
  const names = locale === 'ru' ? STANDALONE_RU : MONTHS_BY_LOCALE[locale]
  const name = names[month - 1]
  if (!name) return String(month)
  return `${name.charAt(0).toUpperCase()}${name.slice(1)}`
}

/** «2026-09» koʻrinishidagi davrni oʻqiladigan yorliqqa aylantiradi. */
export function periodLabel(period: string): string {
  const match = /^(\d{4})-(\d{2})$/.exec(period)
  if (!match) return period
  return monthLabel(Number(match[1]), Number(match[2]))
}
/** @deprecated `MONTHS` — til bo'yicha. Eski import nomi uchun saqlangan. */
export const UZ_MONTHS = MONTHS

const two = (n: number) => String(n).padStart(2, '0')

const toDate = (value: string | Date | null | undefined): Date | null => {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

/** "14.09.2023" */
export function formatDate(value: string | Date | null | undefined): string {
  const date = toDate(value)
  if (!date) return '—'
  return `${two(date.getDate())}.${two(date.getMonth() + 1)}.${date.getFullYear()}`
}

/** "10:35" — faqat soat. */
export function formatTime(value: string | Date | null | undefined): string {
  const date = toDate(value)
  if (!date) return '—'
  return `${two(date.getHours())}:${two(date.getMinutes())}`
}

/**
 * "14.09.2023, 10:35" — `seconds` bilan "14.09.2023, 10:35:07".
 *
 * Soniyalar audit izi uchun kerak: bitta so'rovda ketma-ket yozilgan
 * ikki yozuvni faqat o'sha yerda ajratib bo'ladi.
 */
export function formatDateTime(
  value: string | Date | null | undefined,
  { seconds = false }: { seconds?: boolean } = {},
): string {
  const date = toDate(value)
  if (!date) return '—'
  const time = `${formatTime(date)}${seconds ? `:${two(date.getSeconds())}` : ''}`
  return `${formatDate(date)}, ${time}`
}

/** "14-sentabr, 2023" / "14 сентября 2023" / "14 September 2023" — sarlavhalar uchun. */
export function formatDateLong(value: string | Date | null | undefined): string {
  const date = toDate(value)
  if (!date) return '—'
  const month = MONTHS[date.getMonth()]
  if (locale === 'uz') return `${date.getDate()}-${month}, ${date.getFullYear()}`
  return `${date.getDate()} ${month} ${date.getFullYear()}`
}

/** `Date` → `yyyy-mm-dd` (API va `input[type=date]` uchun). */
export function isoDate(value: Date): string {
  // `toISOString()` UTC'ga o'giradi va Toshkentda kunni bir kun
  // orqaga surardi — sana mahalliy qismlardan yig'iladi.
  return `${value.getFullYear()}-${two(value.getMonth() + 1)}-${two(value.getDate())}`
}

/** Bugun — `yyyy-mm-dd`. Forma sukutlari uchun (PLAN 4.7). */
export function today(): string {
  return isoDate(new Date())
}

/**
 * `dd.mm.yyyy` → `yyyy-mm-dd`. Noto'g'ri bo'lsa `null`.
 *
 * Qo'lda yozilgan sanani qabul qilish uchun (PLAN 4.1): date
 * picker'ning o'zi `yyyy-mm-dd` bilan ishlaydi, foydalanuvchi esa
 * `dd.mm.yyyy` yozadi — va u shu ko'rinishda to'g'ri bo'lishi kerak.
 */
export function parseLocalDate(input: string): string | null {
  const match = /^(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})$/.exec(input.trim())
  if (!match) return null
  const [, day, month, year] = match
  const date = new Date(Number(year), Number(month) - 1, Number(day))
  if (
    date.getFullYear() !== Number(year) ||
    date.getMonth() !== Number(month) - 1 ||
    date.getDate() !== Number(day)
  ) {
    // 31.02.2026 kabi mavjud bo'lmagan sana: `Date` uni jimgina
    // keyingi oyga surib yuboradi, biz esa rad etamiz.
    return null
  }
  return isoDate(date)
}

/** `yyyy-mm-dd` → `dd.mm.yyyy` (bo'sh bo'lsa bo'sh satr). */
export function toLocalDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim())
  if (!match) return ''
  const [, year, month, day] = match
  return `${day}.${month}.${year}`
}
