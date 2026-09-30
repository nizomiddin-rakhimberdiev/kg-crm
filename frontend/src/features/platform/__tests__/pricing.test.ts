/**
 * Obuna narxi — yagona formula (PLAN 1.11).
 *
 * Auditda platforma konsolidagi "Taxminiy oylik" 42 bolali bog'chaga
 * ham, 0 bolaliga ham 500 000 ko'rsatdi: sahifa narxni o'zi hisoblardi
 * va u ADR-12 dan oldingi ishga tushirish narxida (500 000 / +80 000)
 * qotib qolgan edi.
 *
 * Bu yerdagi testlar ikki narsani qo'riqlaydi: raqamlar ADR-12 ga mos
 * kelishini va sahifada narxning ikkinchi nusxasi qayta paydo
 * bo'lmasligini.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import { billableChildren, monthlyEstimate, overageSteps, PLAN } from '@/lib/pricing'

const PAGE = resolve('src/features/platform/pages/PlatformOrganizationsPage.tsx')

describe('obuna narxi', () => {
  it.each([
    // [bolalar, oylik] — ADR-12: 400 000 / 50 bola, har 10 bolaga +50 000.
    [0, 400_000], // bo'sh bog'cha ham bazani to'laydi
    [42, 400_000],
    [50, 400_000], // chegara — hali ortiqcha yo'q
    [51, 450_000], // bitta bola to'liq qadamni yoqadi
    [59, 450_000],
    [60, 450_000], // qadam chegarasi
    [61, 500_000],
    [150, 900_000],
  ])('%i bola → %i so‘m', (children, expected) => {
    expect(monthlyEstimate(children)).toBe(expected)
  })

  it('kiritilgan son eng past chegara — chegirma emas, daromad poli', () => {
    expect(billableChildren(0)).toBe(PLAN.includedChildren)
    expect(billableChildren(12)).toBe(PLAN.includedChildren)
    expect(billableChildren(80)).toBe(80)
  })

  it('ortiqcha qadam tepaga yaxlitlanadi', () => {
    expect(overageSteps(50)).toBe(0)
    expect(overageSteps(51)).toBe(1)
    expect(overageSteps(60)).toBe(1)
    expect(overageSteps(61)).toBe(2)
  })

  it('manfiy yoki butun bo’lmagan son yiqitmaydi', () => {
    expect(monthlyEstimate(-5)).toBe(PLAN.basePrice)
    expect(monthlyEstimate(50.7)).toBe(PLAN.basePrice)
  })

  it('sahifada narxning ikkinchi nusxasi yo’q', () => {
    // Regressiya qo'riqchisi: kimdir yana sahifada hisoblab qo'ymasin.
    expect(readFileSync(PAGE, 'utf8')).not.toMatch(/500_000|80_000|includedChildren\s*=/)
  })
})
