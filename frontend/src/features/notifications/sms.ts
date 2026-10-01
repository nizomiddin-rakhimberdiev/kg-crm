/**
 * SMS uzunligi va bo'laklari — mijoz tomonidagi hisob (PLAN 3.4).
 *
 * Nega mijozda ham bor: shablon muharririda hisoblagich HAR BOSISHDA
 * yangilanadi va har harf uchun serverga so'rov yuborish ham sekin,
 * ham ma'nosiz. Saqlangan shablonning rasmiy raqami esa SERVERDAN
 * keladi (`template.length`) — narx shu bo'laklar bo'yicha to'lanadi
 * va bitta haqiqat manbai bo'lishi kerak.
 *
 * Shuning uchun bu fayl `apps/notifications/segments.py` ning AYNAN
 * nusxasi: chegaralar, GSM-7 jadvali va apostrof almashtirishi bir
 * xil. Ikkisi ajralib ketmasligi uchun test ikkala tomonning bir xil
 * javob berishini tekshiradi.
 */

const GSM7_BASIC =
  '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?' +
  '¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà'
const GSM7_EXTENDED = '^{}\\[~]|€'

export const GSM7_SINGLE = 160
export const GSM7_MULTI = 153
export const UCS2_SINGLE = 70
export const UCS2_MULTI = 67

/**
 * Q11: o'zbek apostroflari SMS'da oddiy `'` ga almashtiriladi.
 *
 * `ʻ` GSM-7 da yo'q, ya'ni bitta shunday belgi 160 belgilik xabarni
 * 70 belgilik UCS-2 xabariga aylantiradi — narx ikki baravar.
 */
const REPLACEMENTS: Array<[string, string]> = [
  ['ʻ', "'"],
  ['ʼ', "'"],
  ['‘', "'"],
  ['’', "'"],
  ['′', "'"],
  ['´', "'"],
  ['“', '"'],
  ['”', '"'],
  ['–', '-'],
  ['—', '-'],
  ['…', '...'],
  [' ', ' '],
]

export function smsSafe(text: string): string {
  return REPLACEMENTS.reduce((acc, [from, to]) => acc.split(from).join(to), text)
}

export interface SmsMeasure {
  encoding: 'gsm7' | 'ucs2'
  characters: number
  parts: number
  limit: number
}

const isGsm7 = (text: string) =>
  [...text].every((char) => GSM7_BASIC.includes(char) || GSM7_EXTENDED.includes(char))

export function measureSms(text: string): SmsMeasure {
  const chars = [...text]
  let length: number
  let single: number
  let multi: number
  let encoding: 'gsm7' | 'ucs2'

  if (isGsm7(text)) {
    length = chars.reduce((sum, char) => sum + (GSM7_EXTENDED.includes(char) ? 2 : 1), 0)
    single = GSM7_SINGLE
    multi = GSM7_MULTI
    encoding = 'gsm7'
  } else {
    // Emoji va boshqa BMP tashqarisidagi belgilar UCS-2 da ikki o'rin
    // egallaydi (surrogat juftlik).
    length = chars.reduce((sum, char) => sum + ((char.codePointAt(0) ?? 0) > 0xffff ? 2 : 1), 0)
    single = UCS2_SINGLE
    multi = UCS2_MULTI
    encoding = 'ucs2'
  }

  if (length === 0) return { encoding, characters: 0, parts: 0, limit: single }
  if (length <= single) return { encoding, characters: length, parts: 1, limit: single }
  return { encoding, characters: length, parts: Math.ceil(length / multi), limit: multi }
}

/** Matnga `${name}` o'rinbosarini kursor joyiga qo'yadi. */
export function insertVariable(text: string, cursor: number, name: string): [string, number] {
  const token = '${' + name + '}'
  const at = Math.max(0, Math.min(cursor, text.length))
  return [text.slice(0, at) + token + text.slice(at), at + token.length]
}
