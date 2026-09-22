import { beforeEach, describe, expect, it } from 'vitest'
import { setCatalogForTests, t } from '..'

describe('t()', () => {
  beforeEach(() => setCatalogForTests({}))

  it("lug'atsiz manba qaytadi — hech qachon bo'sh emas", () => {
    expect(t('Bolalar')).toBe('Bolalar')
  })

  it("lug'at bo'lsa tarjima; o'rinbosarlar to'ldiriladi", () => {
    setCatalogForTests({ 'Jami {total} ta bola': 'Всего детей: {total}' })
    expect(t('Jami {total} ta bola', { total: 12 })).toBe('Всего детей: 12')
  })

  it("noma'lum o'rinbosar ko'rinib qoladi, null bo'sh bo'ladi", () => {
    expect(t('{a} va {b}', { a: null })).toBe(' va {b}')
  })
})
