/**
 * Brend qo'riqchisi — Brendbuk 1.1 (04, 08).
 *
 * Brendbukda ko'k va binafsha ATAYLAB ishlatilmaydi: "raqobatchi CRM
 * tizimlarining deyarli hammasi shu ranglarda". Bitta ekranda qolib
 * ketgan `bg-sky-50` yoki `#6366f1` esa ko'zga tashlanmaydi — u ishlaydi,
 * xato bermaydi va shunchaki brendga zid bo'lib turaveradi.
 *
 * Shuning uchun tekshiruv testga qo'yilgan: yangi ekran yozgan odam
 * eski odatiga qaytsa, build shu yerda to'xtaydi va unga brend nomini
 * ko'rsatadi (`nihol`, `ildiz`, `orik`, `tosh`).
 *
 * `tailwind.config.js` da bu shkalalar o'chirilmagan, balki brendga
 * qayta yo'naltirilgan — ya'ni test o'tmay qolgan taqdirda ham ekranda
 * ko'k chiqmaydi. Ikki qatlam: biri ko'rinishni, ikkinchisi kodni
 * toza saqlaydi.
 */

import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..')

/** Logotip fayli brendbukdagi aniq qiymatlarni o'zida saqlaydi. */
const EXEMPT = ['components/brand/Logo.tsx', 'lib/brand.ts', '__tests__/brand.test.ts']

function sourceFiles(dir: string, found: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      sourceFiles(full, found)
    } else if (/\.(ts|tsx|css)$/.test(entry)) {
      const rel = relative(ROOT, full)
      if (!EXEMPT.includes(rel)) found.push(rel)
    }
  }
  return found
}

const FILES = sourceFiles(ROOT).map((rel) => [rel, readFileSync(join(ROOT, rel), 'utf8')] as const)

/** `bg-sky-50`, `text-indigo-600`, `border-violet-200` … */
const BANNED_CLASS = /\b[a-z-]*-(blue|sky|indigo|cyan|violet|purple|fuchsia)-\d{2,3}\b/g

/** Tailwind qamrovidan tashqaridagi qattiq ranglar — diagramma, inline style. */
const HEX = /#[0-9a-fA-F]{6}\b/g

describe('brend', () => {
  it('ekstraktor ishlayapti (kamida 100 ta fayl ko’riladi)', () => {
    expect(FILES.length).toBeGreaterThan(100)
  })

  it("ko'k va binafsha sinflari ishlatilmaydi", () => {
    const hits = FILES.flatMap(([rel, text]) =>
      (text.match(BANNED_CLASS) ?? []).map((cls) => `${rel}: ${cls}`),
    )
    expect(hits).toEqual([])
  })

  it("rang qattiq yozilmaydi — `lib/brand.ts` yoki Tailwind shkalasi ishlatiladi", () => {
    const hits = FILES.flatMap(([rel, text]) =>
      (text.match(HEX) ?? []).map((hex) => `${rel}: ${hex}`),
    )
    expect(hits).toEqual([])
  })
})
