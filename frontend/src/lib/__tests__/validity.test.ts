/**
 * Brauzerning oʻz validatsiya xabarlari (audit, 2026-10-21).
 *
 * Bolani qoʻshayotgan xodim "Bizni qayerdan eshitgan?" ni tanlamasa,
 * ekranda **brauzerning** xabari chiqardi: "Please select an item in
 * the list" — inglizcha, boshqa shriftda, tizim uslubidan tashqarida.
 * Butun interfeys oʻzbekcha turganda bu xabar mahsulotni yarim
 * tarjima qilingan qilib koʻrsatadi.
 *
 * Yechim bitta joyda: `installValidationMessages()` hujjat darajasida
 * `invalid` hodisasini tutadi va xabarni oʻzimiz yozamiz. 39 faylga
 * tegmaydi — yangi forma ham bepul shu xabarni oladi.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { installValidationMessages, messageFor } from '@/lib/forms/validity'

function field(html: string): HTMLInputElement | HTMLSelectElement {
  document.body.innerHTML = `<form>${html}</form>`
  return document.body.querySelector('input, select') as HTMLInputElement | HTMLSelectElement
}

describe('messageFor', () => {
  it('toʻldirilmagan maydon — oʻzimizning xabar', () => {
    expect(messageFor(field('<input required />'))).toBe('Bu maydonni toʻldiring.')
  })

  it('tanlanmagan roʻyxat — tanlashga chaqiradi', () => {
    const select = field('<select required><option value="">—</option></select>')
    expect(messageFor(select)).toBe('Roʻyxatdan birini tanlang.')
  })

  it('belgilanmagan katakcha', () => {
    expect(messageFor(field('<input type="checkbox" required />'))).toBe(
      'Bu belgini qoʻyish kerak.',
    )
  })

  it('pochta manzili', () => {
    const input = field('<input type="email" value="ali" />') as HTMLInputElement
    expect(messageFor(input)).toBe('Elektron pochta manzili toʻliq emas.')
  })

  it('toʻgʻri qiymat uchun xabar yoʻq', () => {
    expect(messageFor(field('<input value="Ali" required />'))).toBe('')
  })
})

describe('installValidationMessages', () => {
  let remove: () => void

  beforeEach(() => {
    remove = installValidationMessages()
  })
  afterEach(() => {
    remove()
    document.body.innerHTML = ''
  })

  it('`invalid` hodisasida xabarni oʻzgartiradi', () => {
    const input = field('<input required />')
    input.dispatchEvent(new Event('invalid', { bubbles: false, cancelable: true }))
    expect(input.validationMessage).toBe('Bu maydonni toʻldiring.')
  })

  it('qiymat kiritilgach xabar tozalanadi — maydon yana yaroqli', () => {
    const input = field('<input required />') as HTMLInputElement
    input.dispatchEvent(new Event('invalid', { cancelable: true }))
    input.value = 'Ali'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    expect(input.checkValidity()).toBe(true)
    expect(input.validationMessage).toBe('')
  })
})
