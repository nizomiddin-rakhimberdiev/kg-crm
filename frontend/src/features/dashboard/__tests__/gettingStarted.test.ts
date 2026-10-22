/**
 * Birinchi kun zanjiri (audit, 2026-10-21).
 *
 * Boʻsh akkauntda boshqaruv paneli nollar koʻrsatadi: "0 soʻm tushum,
 * 0 soʻm qarz, 0 % davomat". Bu sotuvdan keyingi birinchi taassurot va
 * u mahsulotni kuchsiz koʻrsatadi. Auditning javobi: raqam oʻrniga
 * KEYINGI QADAM tursin — "Tarif yarating → bola qoʻshing → faktura
 * chiqaring". Tartib majburiy: tarifsiz bolaga faktura chiqmaydi, va
 * buni auditor faqat urinib koʻrgandan keyin bildi.
 */

import { describe, expect, it } from 'vitest'
import { nextStep, STEPS } from '@/features/dashboard/gettingStarted'

describe('nextStep', () => {
  it('hech narsa yoʻq — birinchi qadam tarif', () => {
    expect(nextStep({ hasTariff: false, hasChildren: false, hasInvoice: false })).toBe('tariff')
  })

  it('tarif bor, bola yoʻq — bola qoʻshish', () => {
    expect(nextStep({ hasTariff: true, hasChildren: false, hasInvoice: false })).toBe('child')
  })

  it('tarif va bola bor, faktura yoʻq — faktura chiqarish', () => {
    expect(nextStep({ hasTariff: true, hasChildren: true, hasInvoice: false })).toBe('invoice')
  })

  it('hammasi bor — zanjir koʻrinmaydi', () => {
    expect(nextStep({ hasTariff: true, hasChildren: true, hasInvoice: true })).toBeNull()
  })

  it('bola tarifdan oldin qoʻshilgan boʻlsa ham tartib buzilmaydi', () => {
    // Bola importdan tarifsiz kelishi mumkin — keyingi qadam tarif.
    expect(nextStep({ hasTariff: false, hasChildren: true, hasInvoice: false })).toBe('tariff')
  })

  it('uchta qadam, har birida havola va matn bor', () => {
    expect(STEPS.map((step) => step.key)).toEqual(['tariff', 'child', 'invoice'])
    for (const step of STEPS) {
      expect(step.title.length).toBeGreaterThan(0)
      expect(step.to.startsWith('/')).toBe(true)
    }
  })
})
