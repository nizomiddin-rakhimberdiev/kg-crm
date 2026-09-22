/**
 * Lug'at to'liqligi — kodda `t('…')` bilan o'ralgan HAR BIR manba matn
 * ruscha va inglizcha lug'atda bo'lishi shart. Aks holda o'sha satr
 * ikkinchi tilda o'zbekcha ko'rinardi va buni hech kim sezmasdi.
 */

import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { extractSources } from '../extract'
import { messages as en } from '../messages/en'
import { messages as ru } from '../messages/ru'

const sources = extractSources(resolve(__dirname, '../../..'))

describe("lug'at", () => {
  it('kodda kamida 400 ta manba matn topiladi (ekstraktor ishlayapti)', () => {
    expect(sources.length).toBeGreaterThan(400)
  })

  it.each([
    ['ru', ru],
    ['en', en],
  ])('%s — har bir manba matn tarjima qilingan', (_lang, catalog) => {
    const missing = sources.filter((s) => !(s in catalog))
    expect(missing).toEqual([])
  })

  it.each([
    ['ru', ru],
    ['en', en],
  ])("%s — lug'atda ortiqcha (kodda yo'q) kalit yo'q", (_lang, catalog) => {
    const set = new Set(sources)
    const stale = Object.keys(catalog).filter((k) => !set.has(k))
    expect(stale).toEqual([])
  })

  it.each([
    ['ru', ru],
    ['en', en],
  ])("%s — {o'rinbosar}lar manba bilan bir xil", (_lang, catalog) => {
    const holes = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
    const broken = Object.entries(catalog)
      .filter(([k, v]) => holes(k).join() !== holes(v).join())
      .map(([k]) => k)
    expect(broken).toEqual([])
  })

  it("tarjima manbaning o'zi emas (o'zbekcha qolib ketmagan)", () => {
    // Brend, qisqartma va bir xil yoziladigan so'zlar (Email, Bonus, Import…) bundan mustasno.
    const same = (catalog: Record<string, string>) =>
      Object.entries(catalog)
        .filter(([k, v]) => k === v && /[‘’'ʻ]|\b(va|yo|bo|to)\b/.test(k))
        .map(([k]) => k)
    expect(same(ru)).toEqual([])
    expect(same(en)).toEqual([])
  })
})
