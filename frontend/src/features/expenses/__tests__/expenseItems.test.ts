/** Chiqim qatorlari — hisob va yuborish qoidalari (PLAN 7.5). */

import { describe, expect, it } from 'vitest'
import { EMPTY_ITEM, itemsTotal, lineTotal, usableItems } from '../components/ExpenseItemsEditor'

const potato = { name: 'Kartoshka', quantity: '50', unit: 'kg', unit_price: '3000', note: '' }

describe('qator summasi', () => {
  it('egasining misoli: 50 kg × 3 000 = 150 000', () => {
    expect(lineTotal(potato)).toBe(150000)
  })

  it('vergul ham nuqta kabi ishlaydi', () => {
    expect(lineTotal({ ...potato, quantity: '2,5', unit_price: '95000' })).toBe(237500)
  })

  it('toʻldirilmagan qator nol', () => {
    expect(lineTotal(EMPTY_ITEM)).toBe(0)
    expect(lineTotal({ ...potato, unit_price: '' })).toBe(0)
  })
})

describe('jami', () => {
  it('qatorlar qoʻshiladi', () => {
    expect(itemsTotal([potato, { ...potato, quantity: '4', unit_price: '28500' }])).toBe(264000)
  })

  it('boʻsh qatorlar jamini buzmaydi', () => {
    expect(itemsTotal([potato, { ...EMPTY_ITEM }])).toBe(150000)
  })
})

describe('serverga yuboriladigan qatorlar', () => {
  it('faqat toʻldirilganlari ketadi', () => {
    expect(usableItems([potato, { ...EMPTY_ITEM }])).toEqual([potato])
  })

  it('nomsiz qator yuborilmaydi', () => {
    expect(usableItems([{ ...potato, name: '  ' }])).toEqual([])
  })

  it('nol summali qator yuborilmaydi', () => {
    expect(usableItems([{ ...potato, unit_price: '0' }])).toEqual([])
  })
})
