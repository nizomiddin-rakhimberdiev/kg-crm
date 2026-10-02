import { describe, expect, it } from 'vitest'
import { priceFromChild, priceToPayload } from '../price'

describe('priceToPayload', () => {
  it('tarif rejimi — individual narx tozalanadi', () => {
    expect(priceToPayload({ tariffId: 't1', monthlyFee: null })).toEqual({
      payload: { tariff_id: 't1', monthly_fee: null },
      error: null,
    })
  })

  it('individual narx — tarif tozalanadi, ajratuvchilar olib tashlanadi', () => {
    expect(priceToPayload({ tariffId: null, monthlyFee: '1 250 000' })).toEqual({
      payload: { tariff_id: null, monthly_fee: '1250000' },
      error: null,
    })
  })

  it("individual rejimda summa yo'q yoki 0 — so'rov yuborilmaydi", () => {
    expect(priceToPayload({ tariffId: null, monthlyFee: '' }).error).toBeTruthy()
    expect(priceToPayload({ tariffId: null, monthlyFee: '0' }).error).toBeTruthy()
  })

  it('narxsiz bola — ikkala maydon ham bo‘sh', () => {
    expect(priceToPayload({ tariffId: null, monthlyFee: null }).payload).toEqual({
      tariff_id: null,
      monthly_fee: null,
    })
  })
})

describe('priceFromChild', () => {
  it('individual narx serverdan butun so‘m bo‘lib keladi', () => {
    expect(priceFromChild({ tariff: null, monthly_fee: '1250000.00' })).toEqual({
      tariffId: null,
      monthlyFee: '1250000',
    })
  })

  it('tarifli bola — tarif rejimi', () => {
    expect(priceFromChild({ tariff: 't1', monthly_fee: null })).toEqual({
      tariffId: 't1',
      monthlyFee: null,
    })
  })
})
