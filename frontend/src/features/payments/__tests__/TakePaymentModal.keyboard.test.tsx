/**
 * Toʻlov oynasi klaviatura bilan (PLAN 4.8).
 *
 * Kassir kun boʻyi klaviatura bilan ishlaydi: summani yozib, Enter
 * bosadi. Sichqonchaga oʻtish har toʻlovda bir necha soniya, kunda
 * yuzlab marta. Oyna avval `form` emas edi — Enter hech narsa
 * qilmasdi.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const SOURCE = readFileSync(resolve(__dirname, '../components/TakePaymentModal.tsx'), 'utf8')

describe('TakePaymentModal — klaviatura', () => {
  it('oyna `form` ichida — Enter yuboradi', () => {
    expect(SOURCE).toMatch(/<form\s/)
    expect(SOURCE).toMatch(/onSubmit=\{/)
  })

  it('qabul qilish tugmasi `type="submit"`', () => {
    expect(SOURCE).toMatch(/type="submit"/)
  })

  it('ichidagi boshqa tugmalar formani YUBORMAYDI', () => {
    // `type` yozilmagan tugma HTML'da `submit` boʻladi: usul tanlash
    // yoki hisob-faktura tanlash tasodifan toʻlovni yozib yuborardi.
    const buttons = SOURCE.split('<button').slice(1)
    const untyped = buttons.filter((part) => {
      const head = part.slice(0, part.indexOf('>'))
      return !head.includes('type=')
    })
    expect(untyped).toEqual([])
  })

  it('Esc — `Modal` ning oʻzida', () => {
    const modal = readFileSync(resolve(__dirname, '../../../components/ui/Modal.tsx'), 'utf8')
    expect(modal).toMatch(/Escape/)
  })
})
