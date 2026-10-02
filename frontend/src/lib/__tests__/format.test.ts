/**
 * Formatlash (Q12, PLAN 4.1).
 *
 * Auditda har sahifa o'zining `money()` ini yozib olgan edi — o'n
 * yettita nusxa, va ular bir-biridan farq qilardi. Shu testlar
 * yagona uyning xatti-harakatini qotiradi.
 *
 * Til `@/lib/i18n` dan keladi va testda sukut (`uz`) ishlatiladi:
 * guruhlash belgisi til bo'yicha o'zgaradi, shuning uchun uni
 * tekshirish `locale` ni almashtirishni talab qiladi — buni
 * `i18n.test.ts` qiladi.
 */

import { describe, expect, it } from 'vitest'
import {
  CURRENCY,
  compact,
  formatDate,
  formatDateTime,
  isoDate,
  money,
  number,
  parseLocalDate,
  percent,
  quantity,
  signed,
  som,
  toLocalDate,
} from '../format'

const NBSP = ' '

describe('number', () => {
  it("minglarni bo'linmaydigan bo'shliq bilan guruhlaydi", () => {
    expect(number(1500000)).toBe(`1${NBSP}500${NBSP}000`)
    expect(number('1500000')).toBe(`1${NBSP}500${NBSP}000`)
    expect(number(999)).toBe('999')
  })

  it("ma'lumot yo'qligi nol EMAS", () => {
    // Hisobotda "0" va "ma'lumot yo'q" ni aralashtirish eng yomon
    // joyda chiqadi.
    expect(number(null)).toBe('—')
    expect(number(undefined)).toBe('—')
    expect(number('')).toBe('—')
    expect(number('abc')).toBe('—')
    expect(number(0)).toBe('0')
  })

  it('manfiy son tipografik minus bilan', () => {
    expect(number(-1500)).toBe(`−1${NBSP}500`)
  })
})

describe('som', () => {
  it("valyuta bo'linmaydigan bo'shliq bilan qo'shiladi", () => {
    expect(som(1500000)).toBe(`1${NBSP}500${NBSP}000${NBSP}${CURRENCY.uz}`)
  })

  it("o'zbekcha valyutada apostrof U+02BB (Q11)", () => {
    expect(CURRENCY.uz).toBe('soʻm')
    expect(CURRENCY.uz).not.toContain("'")
  })

  it("bo'sh qiymat uchun tire, '0 so'm' emas", () => {
    expect(som(null)).toBe('—')
  })
})

describe('money va signed', () => {
  it('money — valyutasiz', () => {
    expect(money(2000)).toBe(`2${NBSP}000`)
  })

  it('signed — musbatga plus, manfiyga minus', () => {
    expect(signed(250000)).toBe(`+250${NBSP}000`)
    expect(signed(-450000)).toBe(`−450${NBSP}000`)
    expect(signed(0)).toBe('0')
  })
})

describe('compact', () => {
  it('grafik o‘qlari uchun qisqartiradi', () => {
    expect(compact(485200000)).toBe('485.2M')
    expect(compact(1500)).toBe('1.5K')
    expect(compact(999)).toBe('999')
  })
})

describe('quantity', () => {
  it("birlik qo'shiladi va raqamdan ajralmaydi", () => {
    expect(quantity(12, 'dona')).toBe(`12${NBSP}dona`)
    expect(quantity(1200, 'kg')).toBe(`1${NBSP}200${NBSP}kg`)
  })

  it('kasr qism faqat bor bo‘lsa ko‘rinadi', () => {
    expect(quantity(3, 'kg')).toBe(`3${NBSP}kg`)
    expect(quantity(3.5, 'kg')).toBe(`3.5${NBSP}kg`)
  })

  it('birliksiz ham ishlaydi', () => {
    expect(quantity(7)).toBe('7')
  })
})

describe('percent', () => {
  it('bitta kasr xona bilan', () => {
    expect(percent(92)).toBe(`92.0${NBSP}%`)
    expect(percent(92.44, 0)).toBe(`92${NBSP}%`)
  })
})

describe('sana', () => {
  it('uch tilda ham dd.mm.yyyy (Q12)', () => {
    expect(formatDate('2023-09-14')).toBe('14.09.2023')
    expect(formatDate(new Date(2026, 0, 5))).toBe('05.01.2026')
  })

  it("bo'sh yoki buzuq sana uchun tire", () => {
    expect(formatDate(null)).toBe('—')
    expect(formatDate('kecha')).toBe('—')
  })

  it('vaqt bilan', () => {
    expect(formatDateTime(new Date(2026, 8, 14, 10, 35))).toBe('14.09.2026, 10:35')
  })

  it("isoDate UTC'ga o'girmaydi — Toshkentda kun surilmasin", () => {
    // `toISOString()` 00:30 da sanani bir kun orqaga surardi.
    expect(isoDate(new Date(2026, 9, 2, 0, 30))).toBe('2026-10-02')
  })
})

describe('parseLocalDate', () => {
  it("dd.mm.yyyy ni ISO'ga o'giradi", () => {
    expect(parseLocalDate('02.10.2026')).toBe('2026-10-02')
    expect(parseLocalDate('2.10.2026')).toBe('2026-10-02')
    expect(parseLocalDate('02/10/2026')).toBe('2026-10-02')
  })

  it('mavjud bo‘lmagan sanani RAD etadi', () => {
    // `new Date(2026, 1, 31)` jimgina 3-martga suriladi.
    expect(parseLocalDate('31.02.2026')).toBeNull()
    expect(parseLocalDate('2026-10-02')).toBeNull()
    expect(parseLocalDate('bugun')).toBeNull()
  })

  it('teskari yo‘nalish', () => {
    expect(toLocalDate('2026-10-02')).toBe('02.10.2026')
    expect(toLocalDate('')).toBe('')
  })
})
