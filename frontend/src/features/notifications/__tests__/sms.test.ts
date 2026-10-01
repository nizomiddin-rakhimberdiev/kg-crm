/**
 * SMS hisobi — mijoz va server BIR XIL javob berishi kerak (PLAN 3.4).
 *
 * Narx bo'laklar bo'yicha to'lanadi. Muharrirdagi hisoblagich
 * `apps/notifications/segments.py` bilan ajralib ketsa, mudira
 * "bitta SMS" deb o'ylab yozgan matn amalda ikkitasi bo'lardi — va
 * buni faqat oy oxirida, hisobdan bilardi.
 *
 * Shuning uchun bu yerdagi raqamlar backend testidagi raqamlar bilan
 * bir xil: `apps/notifications/tests/test_sms_rules.py::TestSegments`.
 */

import { describe, expect, it } from 'vitest'
import { insertVariable, measureSms, smsSafe } from '../sms'

describe('measureSms', () => {
  it('lotin matni: 160 belgi — bitta SMS, 161 — ikkitasi', () => {
    expect(measureSms('a'.repeat(160)).parts).toBe(1)
    expect(measureSms('a'.repeat(161)).parts).toBe(2)
    expect(measureSms('a'.repeat(160)).encoding).toBe('gsm7')
  })

  it('kirill matni: 70 belgi — bitta SMS, 71 — ikkitasi', () => {
    expect(measureSms('ё'.repeat(70)).parts).toBe(1)
    expect(measureSms('ё'.repeat(71)).parts).toBe(2)
    expect(measureSms('ё'.repeat(70)).encoding).toBe('ucs2')
  })

  it("bo'sh matn nol bo'lak", () => {
    expect(measureSms('').parts).toBe(0)
  })

  it("GSM-7 da ikki o'rin egallaydigan belgilar hisobga olinadi", () => {
    // `{` escape bilan yoziladi — ikkita o'rin.
    expect(measureSms('{').characters).toBe(2)
  })
})

describe('smsSafe', () => {
  it("o'zbek apostrofi narxni ikki baravar qiladi — almashtirilgach yo'q", () => {
    const text = "Toʻlov qabul qilindi. " + 'a'.repeat(100)
    expect(measureSms(text).encoding).toBe('ucs2')
    expect(measureSms(smsSafe(text)).encoding).toBe('gsm7')
    expect(measureSms(smsSafe(text)).parts).toBeLessThan(measureSms(text).parts)
  })

  it("tipografik tirnoq va tire ham oddiylashtiriladi", () => {
    expect(smsSafe('“matn” — izoh…')).toBe('"matn" - izoh...')
  })
})

describe('insertVariable', () => {
  it("kursor joyiga qo'yadi va kursorni o'rinbosardan keyinga suradi", () => {
    const [text, caret] = insertVariable('Salom !', 6, 'guardian')
    expect(text).toBe('Salom ${guardian}!')
    expect(caret).toBe(6 + '${guardian}'.length)
  })

  it("kursor matndan tashqarida bo'lsa oxiriga qo'yadi", () => {
    const [text] = insertVariable('Salom', 99, 'child')
    expect(text).toBe('Salom${child}')
  })
})
