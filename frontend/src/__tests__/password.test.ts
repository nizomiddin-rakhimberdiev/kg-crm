/**
 * Frontend va backend bitta raqamni bilsin (PLAN 11.10).
 *
 * Uchta raqam yashagan edi: Django sukuti 8, profil sahifasida 10,
 * qolgan ekranlarda hech narsa. Foydalanuvchi uchun bu shunday
 * koʻrinadi — UI ruxsat beradi, server rad etadi, sabab esa
 * tushunarsiz.
 *
 * Shuning uchun raqam ikki joyda yozilsa ham, u bitta boʻlishi kerak,
 * va buni test ushlab turadi.
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { MIN_PASSWORD_LENGTH, passwordTooShort } from '../lib/password'

describe('parol uzunligi', () => {
  it('backend sozlamasi bilan bir xil', () => {
    const settings = readFileSync(
      resolve(__dirname, '../../../backend/config/settings/base.py'),
      'utf8',
    )
    const match = /"min_length":\s*(\d+)/.exec(settings)
    expect(match, '`MinimumLengthValidator` da `min_length` topilmadi').toBeTruthy()
    expect(Number(match?.[1])).toBe(MIN_PASSWORD_LENGTH)
  })

  it('boʻsh maydon "kalta" deb belgilanmaydi', () => {
    // Aks holda forma ochilishi bilan qizil xato chiqardi.
    expect(passwordTooShort('')).toBe(false)
  })

  it('kalta va yetarli parollarni ajratadi', () => {
    expect(passwordTooShort('qisqa')).toBe(true)
    expect(passwordTooShort('bahorbogchasi2026')).toBe(false)
  })
})
