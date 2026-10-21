/**
 * Guruhning yosh oraligʻi (audit, 2026-10-21).
 *
 * Guruhda 1–3 yosh yozilgan boʻlsa ham 4 yoshli bola muammosiz
 * qoʻshilardi, ya'ni maydon hech narsa qilmasdi va "yosh oraligʻi nima
 * uchun kerak?" degan savol javobsiz qolardi. Javob: u BLOKLAMAYDI —
 * bogʻchada istisno koʻp — lekin ogohlantiradi.
 */

import { describe, expect, it } from 'vitest'
import { ageOutsideGroup, ageOnDate } from '@/features/children/ageFit'

const group = (age_min: number | null, age_max: number | null) => ({
  id: 'g1',
  name: 'Kichik guruh',
  age_min,
  age_max,
})

describe('ageOnDate', () => {
  it('tugʻilgan kun oʻtmagan boʻlsa yosh bir kam', () => {
    expect(ageOnDate('2021-12-31', new Date('2026-10-21'))).toBe(4)
    expect(ageOnDate('2021-01-01', new Date('2026-10-21'))).toBe(5)
  })

  it('sana boʻsh — yosh nomaʼlum', () => {
    expect(ageOnDate('', new Date('2026-10-21'))).toBeNull()
  })
})

describe('ageOutsideGroup', () => {
  it('oraliqdan tashqarida — ogohlantiradi', () => {
    expect(ageOutsideGroup(group(1, 3), '2021-01-01', new Date('2026-10-21'))).toEqual({
      age: 5,
      min: 1,
      max: 3,
    })
  })

  it('oraliq ichida — jim', () => {
    expect(ageOutsideGroup(group(1, 6), '2021-01-01', new Date('2026-10-21'))).toBeNull()
  })

  it('chegaraning oʻzi oraliq ichida', () => {
    expect(ageOutsideGroup(group(5, 5), '2021-01-01', new Date('2026-10-21'))).toBeNull()
  })

  it('bitta chegara — ikkinchisi cheklamaydi', () => {
    expect(ageOutsideGroup(group(null, 3), '2021-01-01', new Date('2026-10-21'))).toEqual({
      age: 5,
      min: null,
      max: 3,
    })
    expect(ageOutsideGroup(group(6, null), '2021-01-01', new Date('2026-10-21'))).toEqual({
      age: 5,
      min: 6,
      max: null,
    })
  })

  it('oraliq yoʻq yoki sana yoʻq — ogohlantirish ham yoʻq', () => {
    expect(ageOutsideGroup(group(null, null), '2021-01-01', new Date('2026-10-21'))).toBeNull()
    expect(ageOutsideGroup(group(1, 3), '', new Date('2026-10-21'))).toBeNull()
  })
})
