import { describe, expect, it } from 'vitest'
import { fill, ru, uz } from '../content'
import { isPaymentDelayEvidence, paymentDelayReason } from '../severity'
import type { PaymentDelayEvidence } from '@/lib/api/types'

const evidence: PaymentDelayEvidence = {
  as_of: '2026-09-17',
  overdue_days_threshold: 15,
  children_count: 24,
  active_children: 105,
  critical_days_threshold: 45,
  critical_children_threshold: 11,
  total_overdue: '21758500.00',
  average_days_overdue: 61,
  max_days_overdue: 160,
  children: [],
}

describe('fill', () => {
  it('evidence raqamlaridan jumla tuzadi', () => {
    expect(fill(uz.titles.payment_delay, { ...evidence })).toBe(
      '24 ta bola bo‘yicha to‘lov 15 kundan ortiq kechikmoqda',
    )
  })

  it("yo'q kalitni yashirmaydi — ko'rinib turadi", () => {
    expect(fill('{a} va {b}', { a: 1 })).toBe('1 va {b}')
  })

  it('UZ va RU bir xil kalitlarga ega', () => {
    const keys = (o: object): string[] =>
      Object.entries(o).flatMap(([k, v]) =>
        v && typeof v === 'object' ? keys(v).map((x) => `${k}.${x}`) : [k],
      )
    expect(keys(ru).sort()).toEqual(keys(uz).sort())
  })

  it("matnda bashorat so'zlari yo'q — faqat fakt (docs/07 §7)", () => {
    const all = JSON.stringify(uz).toLowerCase()
    for (const banned of ["to'lamaydi", 'to‘lamaydi', 'xavf ostida', 'ehtimol', 'bashorat']) {
      expect(all).not.toContain(banned)
    }
  })
})

describe('paymentDelayReason', () => {
  it('ikkala chegara oshgan — both', () => {
    expect(paymentDelayReason(evidence, 'critical')).toBe('both')
  })
  it('faqat kun bo‘yicha', () => {
    expect(paymentDelayReason({ ...evidence, children_count: 3 }, 'critical')).toBe('days')
  })
  it('faqat son bo‘yicha', () => {
    expect(paymentDelayReason({ ...evidence, max_days_overdue: 20 }, 'critical')).toBe('count')
  })
  it('warning — sabab yo‘q', () => {
    expect(paymentDelayReason(evidence, 'warning')).toBe('none')
  })
  it("backend bilan mos kelmasa yolg'on sabab yozmaydi", () => {
    expect(
      paymentDelayReason({ ...evidence, children_count: 3, max_days_overdue: 20 }, 'critical'),
    ).toBe('none')
  })
})

describe('isPaymentDelayEvidence', () => {
  it('v1 sxemani taniydi, boshqasini rad etadi', () => {
    expect(isPaymentDelayEvidence(evidence)).toBe(true)
    expect(isPaymentDelayEvidence({ drop_points: 12 })).toBe(false)
    expect(isPaymentDelayEvidence(null)).toBe(false)
  })
})
