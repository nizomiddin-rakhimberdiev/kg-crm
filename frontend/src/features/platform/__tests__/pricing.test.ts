/**
 * Platforma konsolidagi "Taxminiy oylik" — 2026-09-30 auditi (PLAN 1.11).
 *
 * Auditda: 42 bolali bog'chaga ham, 0 bolali bog'chaga ham 500 000
 * ko'rsatildi. To'g'ri javob — 400 000: ADR-12 narxni 400 000 / 50 bola,
 * har boshlangan 10 bolaga +50 000 qilib belgilagan. Eski 500 000 /
 * +80 000 faqat 2026-09-14 dan OLDIN yozilgan hisoblar uchun to'g'ri.
 *
 * Sabab: `PlatformOrganizationsPage.tsx` narxni O'ZI hisoblaydi
 * (`const base = 500_000`, `steps * 80_000`). Tizimda narxning ikkinchi
 * nusxasi bor va u eskirgan. Landing kalkulyatori esa backend'dan
 * oladi (`/public/pricing`) va to'g'ri — ya'ni ikki manba bir-biriga
 * zid javob beryapti.
 *
 * `it.fails` — xato takrorlanadi, CI yashil qoladi. Tuzatilgach test
 * o'tadi va `it.fails` buni XATO deb belgilaydi, ya'ni marker'ni olib
 * tashlashga majbur qiladi.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const PAGE = resolve('src/features/platform/pages/PlatformOrganizationsPage.tsx')
const SHARED_PRICING = resolve('src/lib/pricing.ts')

/** ADR-12: 400 000 / 50 bola, har boshlangan 10 bola uchun +50 000. */
const EXPECTED: Array<[children: number, monthly: number]> = [
  [0, 400_000],
  [42, 400_000],
  [50, 400_000],
  [51, 450_000],
  [60, 450_000],
  [150, 900_000],
]

const exists = (path: string): boolean => {
  try {
    readFileSync(path)
    return true
  } catch {
    return false
  }
}

describe('platforma konsoli — taxminiy oylik', () => {
  it.fails('narx yagona modulda (PLAN 1.11), sahifada qayta hisoblanmaydi', () => {
    expect(exists(SHARED_PRICING), 'src/lib/pricing.ts').toBe(true)
  })

  it.fails('sahifada eski narx qattiq yozilmagan', () => {
    const source = readFileSync(PAGE, 'utf8')
    expect(source).not.toMatch(/500_000|80_000/)
  })

  it.fails('ADR-12 bo’yicha hisoblaydi', async () => {
    if (!exists(SHARED_PRICING)) throw new Error('src/lib/pricing.ts hali yo’q')
    // Yo'l ish paytida yig'iladi — modul hali yo'q va statik import
    // butun faylni yiqitardi.
    const mod = (await import(/* @vite-ignore */ ['@', 'lib', 'pricing'].join('/'))) as {
      monthlyEstimate: (children: number) => number
    }
    for (const [children, monthly] of EXPECTED) {
      expect(mod.monthlyEstimate(children), `${children} bola`).toBe(monthly)
    }
  })
})
