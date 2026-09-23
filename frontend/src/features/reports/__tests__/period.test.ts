import { describe, expect, it } from 'vitest'
import {
  bucketLabel,
  groupByFor,
  periodDays,
  periodFor,
  periodLabel,
  shiftPeriod,
  toISODate,
} from '../period'

// 2026-09-18 — juma.
const anchor = new Date(2026, 8, 18)

describe('periodFor', () => {
  it('kun — bitta sana', () => {
    expect(periodFor('day', anchor)).toEqual({
      preset: 'day',
      from: '2026-09-18',
      to: '2026-09-18',
    })
  })

  it('hafta dushanbadan yakshanbagacha (ISO)', () => {
    expect(periodFor('week', anchor)).toEqual({
      preset: 'week',
      from: '2026-09-14',
      to: '2026-09-20',
    })
    // Yakshanba ham o'sha haftaga tushadi, keyingisiga emas.
    expect(periodFor('week', new Date(2026, 8, 20)).from).toBe('2026-09-14')
  })

  it('oy — 1 dan oxirgi kungacha, fevralni ham', () => {
    expect(periodFor('month', anchor)).toEqual({
      preset: 'month',
      from: '2026-09-01',
      to: '2026-09-30',
    })
    expect(periodFor('month', new Date(2028, 1, 10)).to).toBe('2028-02-29')
  })

  it('chorak va yil', () => {
    expect(periodFor('quarter', anchor)).toEqual({
      preset: 'quarter',
      from: '2026-07-01',
      to: '2026-09-30',
    })
    expect(periodFor('year', anchor)).toEqual({
      preset: 'year',
      from: '2026-01-01',
      to: '2026-12-31',
    })
  })
})

describe('shiftPeriod', () => {
  it("oy orqaga — 31 kunlik oydan 30 kunlikka o'tganda sakramaydi", () => {
    const march = periodFor('month', new Date(2026, 2, 31))
    expect(shiftPeriod(march, -1)).toEqual({
      preset: 'month',
      from: '2026-02-01',
      to: '2026-02-28',
    })
  })

  it('chorak va yil oldinga', () => {
    expect(shiftPeriod(periodFor('quarter', anchor), 1).from).toBe('2026-10-01')
    expect(shiftPeriod(periodFor('year', anchor), 1)).toEqual({
      preset: 'year',
      from: '2027-01-01',
      to: '2027-12-31',
    })
  })

  it("ixtiyoriy davr o'z uzunligicha suriladi", () => {
    const custom = { preset: 'custom' as const, from: '2026-09-01', to: '2026-09-10' }
    expect(shiftPeriod(custom, 1)).toEqual({
      preset: 'custom',
      from: '2026-09-11',
      to: '2026-09-20',
    })
    expect(shiftPeriod(custom, -1)).toEqual({
      preset: 'custom',
      from: '2026-08-22',
      to: '2026-08-31',
    })
  })
})

describe('groupByFor', () => {
  it("preset'dan bir pog'ona mayda kesim", () => {
    expect(groupByFor(periodFor('week', anchor))).toBe('day')
    expect(groupByFor(periodFor('month', anchor))).toBe('day')
    expect(groupByFor(periodFor('quarter', anchor))).toBe('week')
    expect(groupByFor(periodFor('year', anchor))).toBe('month')
  })

  it('ixtiyoriy davrda uzunlikka qarab', () => {
    expect(groupByFor({ preset: 'custom', from: '2026-01-01', to: '2026-01-20' })).toBe('day')
    expect(groupByFor({ preset: 'custom', from: '2026-01-01', to: '2026-03-31' })).toBe('week')
    expect(groupByFor({ preset: 'custom', from: '2025-01-01', to: '2026-06-30' })).toBe('month')
    expect(groupByFor({ preset: 'custom', from: '2020-01-01', to: '2026-06-30' })).toBe('year')
  })
})

describe('yorliqlar', () => {
  it('sarlavha', () => {
    expect(periodLabel(periodFor('day', anchor))).toBe('18-sentabr, 2026')
    expect(periodLabel(periodFor('week', anchor))).toBe('14–20 sentabr 2026')
    expect(periodLabel(periodFor('week', new Date(2026, 8, 30)))).toBe('28 sentabr – 4 oktabr 2026')
    expect(periodLabel(periodFor('month', anchor))).toBe('Sentabr 2026')
    expect(periodLabel(periodFor('quarter', anchor))).toBe('III chorak 2026')
    expect(periodLabel(periodFor('year', anchor))).toBe('2026-yil')
  })

  it("grafik o'qi", () => {
    expect(bucketLabel('2026-09-18', 'day')).toBe('18 Sen')
    expect(bucketLabel('2026-09-01', 'month')).toBe('Sen 26')
    expect(bucketLabel('2026-07-01', 'quarter')).toBe('III ch. 2026')
    expect(bucketLabel('2026-01-01', 'year')).toBe('2026')
  })

  it("mahalliy sana — UTC siljishi yo'q", () => {
    expect(toISODate(new Date(2026, 8, 18, 23, 30))).toBe('2026-09-18')
    expect(periodDays(periodFor('month', anchor))).toBe(30)
  })
})
