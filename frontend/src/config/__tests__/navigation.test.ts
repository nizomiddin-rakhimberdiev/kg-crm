/**
 * Yon menyu boʻlimlari (PLAN 4.5).
 *
 * Oʻn oltita punkt bitta roʻyxatda turganda ular orasida maʼnoviy
 * bogʻlanish koʻrinmaydi: "Qarzdorlar" bilan "Ombor" yonma-yon
 * turardi. Test boʻlimlarning toʻliqligini qoʻriqlaydi — yangi punkt
 * qoʻshilib, boʻlimi yozilmasa, u menyuda umuman koʻrinmay qolardi.
 */

import { describe, expect, it } from 'vitest'
import { SECTION_LABEL, SECTION_ORDER, navItems } from '../navigation'

describe('navigatsiya boʻlimlari', () => {
  it('har bir punktning boʻlimi bor va u tartibda sanalgan', () => {
    for (const item of navItems) {
      expect(SECTION_ORDER, `${item.to} boʻlimi roʻyxatda yoʻq`).toContain(item.section)
    }
  })

  it('har bir ishlatilgan boʻlimning nomi bor', () => {
    const used = new Set(navItems.map((item) => item.section))
    for (const section of used) {
      // `main` ataylab nomsiz: bitta punkt uchun sarlavha shovqin.
      if (section === 'main') continue
      expect(SECTION_LABEL[section], `${section} nomsiz`).toBeTruthy()
    }
  })

  it('moliya boʻlimida pul bilan ishlaydigan sahifalar', () => {
    const finance = navItems.filter((item) => item.section === 'finance').map((item) => item.to)
    expect(finance).toEqual(['/payments', '/debtors', '/expenses', '/reports'])
  })

  it('bolalar boʻlimida kundalik ish', () => {
    const children = navItems.filter((item) => item.section === 'children').map((item) => item.to)
    expect(children).toEqual(['/children', '/groups', '/attendance'])
  })
})
