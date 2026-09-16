/**
 * Token saqlash — kalit MANZIL bilan nomlanadi (P1-003 yonidagi tuzatish).
 *
 * Barcha bog'chalar bitta origin'da yashaydi, ya'ni bitta
 * `localStorage` ni bo'lishadi. Bitta kalit bo'lganda ikki bog'chaga
 * xizmat qiladigan buxgalter ikkinchisiga kirishi bilan birinchisidan
 * chiqib ketardi.
 */

import { beforeEach, describe, expect, it } from 'vitest'
import { tokenStorage } from '../auth/tokenStorage'

beforeEach(() => {
  localStorage.clear()
  tokenStorage.setAccess(null)
})

describe('access token', () => {
  it('faqat xotirada — localStorage ga tushmaydi', () => {
    tokenStorage.setAccess('maxfiy-access')
    expect(tokenStorage.getAccess()).toBe('maxfiy-access')
    // XSS uchun bepul o'lja bo'lmasligi kerak.
    expect(JSON.stringify(localStorage)).not.toContain('maxfiy-access')
  })
})

describe('refresh token', () => {
  it('manzil bo\'yicha ajratiladi', () => {
    tokenStorage.setRefresh('quyosh-token', 'quyosh')
    tokenStorage.setRefresh('bahor-token', 'bahor')

    expect(tokenStorage.getRefresh('quyosh')).toBe('quyosh-token')
    expect(tokenStorage.getRefresh('bahor')).toBe('bahor-token')
  })

  it('ikkinchi bog\'chaga kirish birinchisini chiqarib yubormaydi', () => {
    tokenStorage.setRefresh('quyosh-token', 'quyosh')
    tokenStorage.setRefresh('bahor-token', 'bahor')
    expect(tokenStorage.getRefresh('quyosh')).toBe('quyosh-token')
  })

  it('o\'chirish faqat o\'sha bog\'chaga tegadi', () => {
    tokenStorage.setRefresh('quyosh-token', 'quyosh')
    tokenStorage.setRefresh('bahor-token', 'bahor')
    tokenStorage.setRefresh(null, 'quyosh')

    expect(tokenStorage.getRefresh('quyosh')).toBeNull()
    expect(tokenStorage.getRefresh('bahor')).toBe('bahor-token')
  })
})
