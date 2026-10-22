/**
 * Yon menyu boʻlimlari (PLAN 4.5, ADR-45).
 *
 * Oʻn oltita punkt bitta roʻyxatda turganda ular orasida maʼnoviy
 * bogʻlanish koʻrinmaydi. Boʻlimlar modul boʻyicha emas, **ishning
 * chastotasi va roli** boʻyicha: mustaqil auditda (2026-10-21) kassir
 * kuniga 20 marta toʻlov qabul qilishi, lekin "Toʻlovlar" menyuning
 * oʻrtasida turishi yozildi. Kundalik ish yuqorida, oyda bir marta
 * ochiladigani pastda, bir marta sozlanadigani eng pastda.
 *
 * Test boʻlimlarning toʻliqligini ham, TARKIBINI ham qoʻriqlaydi:
 * yangi punkt qoʻshilib boʻlimi yozilmasa, u menyuda koʻrinmay
 * qolardi; eski boʻlimga tushib qolsa esa guruhlash maʼnosini
 * yoʻqotadi.
 */

import { describe, expect, it } from 'vitest'
import { SECTION_LABEL, SECTION_ORDER, navItems } from '../navigation'

const inSection = (section: string) =>
  navItems.filter((item) => item.section === section).map((item) => item.to)

describe('navigatsiya boʻlimlari', () => {
  it('har bir punktning boʻlimi bor va u tartibda sanalgan', () => {
    for (const item of navItems) {
      expect(SECTION_ORDER, `${item.to} boʻlimi roʻyxatda yoʻq`).toContain(item.section)
    }
  })

  it('har bir ishlatilgan boʻlimning nomi bor', () => {
    const used = new Set(navItems.map((item) => item.section))
    for (const section of used) {
      expect(SECTION_LABEL[section], `${section} nomsiz`).toBeTruthy()
    }
  })

  it('oltita boʻlim, chastota tartibida', () => {
    expect(SECTION_ORDER).toEqual(['today', 'children', 'money', 'team', 'analysis', 'setup'])
  })

  it('«Bugun» — kuniga bir necha marta ochiladigani', () => {
    expect(inSection('today')).toEqual(['/dashboard', '/attendance', '/payments'])
  })

  it('«Bolalar» — bola va guruh', () => {
    expect(inSection('children')).toEqual(['/children', '/groups'])
  })

  it('«Pul» — kassa, chiqim, ombor, qarzdorlik', () => {
    // Ombor ALOHIDA boʻlimda turardi: bitta punkt uchun sarlavha
    // menyuni uzaytirib, foyda bermasdi. Ombor — chiqimning davomi.
    expect(inSection('money')).toEqual(['/cash', '/expenses', '/debtors', '/inventory'])
  })

  it('«Jamoa» — xodim va oylik maosh', () => {
    expect(inSection('team')).toEqual(['/staff', '/payroll'])
  })

  it('«Tahlil» — oyda bir marta ochiladigani', () => {
    expect(inSection('analysis')).toEqual(['/finance', '/reports'])
  })

  it('«Sozlash» — bir marta sozlanadigani, hammasi bitta joyda', () => {
    expect(inSection('setup')).toEqual([
      '/notifications',
      '/branches',
      '/billing',
      '/audit',
      '/settings',
    ])
  })
})
