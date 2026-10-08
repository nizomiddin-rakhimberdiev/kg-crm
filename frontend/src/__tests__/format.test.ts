/**
 * Formatlashning yagona uyi — qoʻriqlanadigan qoida (PLAN 10.7).
 *
 * Q12 boʻyicha sana, pul, son va miqdor faqat `lib/format.ts` da
 * formatlanadi. Qoida bir marta (PLAN 4.1) oʻtkazilgan edi, lekin
 * oʻn bitta `toLocaleString('uz-UZ')` undan keyin ham qolib ketdi va
 * ularni hech narsa koʻrsatmadi: ekranda sana shunchaki BOSHQACHA
 * koʻrinadi — "2026-09-17 17:20" va "17.09.2026, 17:20" — va
 * ru/en tilidagi foydalanuvchiga ham qatʼiy `uz-UZ` beriladi.
 *
 * Shuning uchun qoida endi testda. `lib/format.ts` ning oʻzi —
 * yagona istisno, chunki `Intl` oxir-oqibat oʻsha yerda chaqiriladi.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC = resolve(__dirname, '..')
/** Faqat formatlashning oʻz uyi va test fayllari chetda. */
const ALLOWED = ['lib/format.ts', '__tests__/']

function walk(dir: string, files: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) walk(full, files)
    else if (full.endsWith('.ts') || full.endsWith('.tsx')) files.push(full)
  }
  return files
}

const files = walk(SRC).filter(
  (file) => !ALLOWED.some((part) => file.replace(`${SRC}/`, '').includes(part)),
)

describe('formatlash bitta uydan', () => {
  it('hech qayerda yalangʻoch toLocaleString / toLocaleDateString yoʻq', () => {
    const offenders = files.filter((file) =>
      /\.toLocale(String|DateString|TimeString)\s*\(/.test(readFileSync(file, 'utf8')),
    )
    expect(offenders.map((f) => f.replace(`${SRC}/`, ''))).toEqual([])
  })

  it('hech qayerda toʻgʻridan-toʻgʻri Intl.NumberFormat / DateTimeFormat yoʻq', () => {
    const offenders = files.filter((file) =>
      /new Intl\.(NumberFormat|DateTimeFormat)\b/.test(readFileSync(file, 'utf8')),
    )
    expect(offenders.map((f) => f.replace(`${SRC}/`, ''))).toEqual([])
  })
})
