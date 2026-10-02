/**
 * Q11: o'zbek apostrofi — `oʻ`/`gʻ` uchun U+02BB, tutuq uchun U+02BC.
 *
 * Nega test kerak: bu farq ko'zga ko'rinmaydi. ASCII `'` bilan
 * yozilgan "to'lov" ekranda deyarli bir xil ko'rinadi, lekin u
 * **boshqa satr** — ya'ni lug'at kaliti mos kelmaydi, qidiruv
 * topmaydi va bitta so'z sahifada ikki xil yozilib qoladi. Bir marta
 * normallashtirib, keyin qo'riqlash — yagona ishlaydigan yo'l.
 *
 * Foydalanuvchi MA'LUMOTIGA tegilmaydi: bu test faqat bizning
 * matnlarimizni tekshiradi.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { messages as en } from '../messages/en'
import { messages as ru } from '../messages/ru'

const SRC = resolve(__dirname, '../../..')
const SKIP = ['__tests__', 'node_modules']

/** Harf—ASCII apostrof—harf: aynan shu normallashtirilishi kerak. */
const RAW = /\p{L}['‘’`´]\p{L}/u

function walk(dir: string, files: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    if (SKIP.some((part) => entry.includes(part))) continue
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) walk(full, files)
    else if (/\.tsx?$/.test(full)) files.push(full)
  }
  return files
}

/** `t('…')` ning birinchi argumenti. */
const T_CALL = /\bt\(\s*('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")/g

describe('Q11 — apostroflar', () => {
  it("t() manbalarida ASCII apostrof yo'q", () => {
    const offenders: string[] = []
    for (const file of walk(SRC)) {
      const text = readFileSync(file, 'utf8')
      for (const match of text.matchAll(T_CALL)) {
        const inner = match[1].slice(1, -1)
        if (RAW.test(inner)) offenders.push(`${file.replace(SRC, '')}: ${inner.slice(0, 60)}`)
      }
    }
    expect(offenders).toEqual([])
  })

  it("lug'at kalitlarida ham yo'q", () => {
    const offenders = [...Object.keys(ru), ...Object.keys(en)].filter((key) => RAW.test(key))
    expect(offenders).toEqual([])
  })

  it('landing matnlarida ham (uz bo‘limi)', () => {
    const content = readFileSync(join(SRC, 'features/landing/content.ts'), 'utf8')
    const uz = content.slice(content.indexOf('const uz: Copy'), content.indexOf('const ru: Copy'))
    const lines = uz.split('\n').filter((line) => RAW.test(line))
    expect(lines).toEqual([])
  })

  it('valyuta nomi ham normallashtirilgan', async () => {
    const { CURRENCY } = await import('@/lib/format')
    expect(CURRENCY.uz).toBe('soʻm')
  })
})
