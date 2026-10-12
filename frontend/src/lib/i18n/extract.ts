/**
 * Koddagi `t('…')` manba matnlarini ajratib oladi — lug'at to'liqligi
 * testi va tarjima ro'yxatini chiqarish uchun (Node/vitest, brauzer emas).
 *
 * Faqat birinchi argumenti STRING LITERAL bo'lgan chaqiruvlar: `t(name)`
 * kabi dinamik chaqiruv hisobga olinmaydi — u lug'atda bo'lishi shart emas
 * (manba qaytadi), lekin tarjimasiz qoladi; shuning uchun kodda dinamik
 * `t()` ishlatilmaydi.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, sep } from 'node:path'

/** Public sayt va vendor konsoli lug'atga kirmaydi — ularning o'z matn qatlami bor. */
const SKIP = [
  'features/landing',
  'features/marketing',
  'features/platform',
  '__tests__',
  'prerender',
  'lib/i18n',
  'src/test',
]

const CALL = /(?<![\w.])t\(\s*('((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")/g

const unescape = (s: string) => s.replace(/\\(['"\\])/g, '$1')

export function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p, out)
    else if (/\.tsx?$/.test(name) && !name.endsWith('.d.ts')) out.push(p)
  }
  return out
}

/** `srcDir` ichidagi barcha manba matnlar (takrorsiz, tartiblangan). */
export function extractSources(srcDir: string): string[] {
  const keys = new Set<string>()
  for (const file of walk(srcDir)) {
    // Windows'da yo'l `\` bilan keladi — SKIP ro'yxati `/` bilan yozilgan.
    const posix = file.split(sep).join('/')
    if (SKIP.some((s) => posix.includes(s))) continue
    const text = readFileSync(file, 'utf8')
    for (const m of text.matchAll(CALL)) keys.add(unescape(m[2] ?? m[3] ?? ''))
  }
  return [...keys].sort((a, b) => a.localeCompare(b))
}
