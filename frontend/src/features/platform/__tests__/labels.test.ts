/**
 * Konsoldagi xom enum nomlari (PLAN 5.12).
 */

import { describe, expect, it } from 'vitest'
import { INVOICE_STATUS, PAYMENT_TERM, label } from '../labels'

describe('konsol yorliqlari', () => {
  it('kod nomi oʻrniga oʻzbekcha nom', () => {
    expect(label(PAYMENT_TERM, 'semiannual')).toBe('Yarim yillik')
    expect(label(INVOICE_STATUS, 'overdue')).toBe('Muddati oʻtgan')
  })

  it('nomaʼlum qiymat yoʻqolmaydi — oʻzi koʻrinadi', () => {
    // Yangi holat qoʻshilganda ekran boʻsh qolmasin.
    expect(label(PAYMENT_TERM, 'quarterly')).toBe('quarterly')
    expect(label(PAYMENT_TERM, null)).toBe('—')
  })
})
