/**
 * Oy maydoni (audit, 2026-10-21).
 *
 * Native `input[type=month]` oy nomini **brauzer lokali** boʻyicha
 * chiqaradi: butun interfeys oʻzbekcha turganda tanlagichda
 * "October 2026" yozilardi. `DateInput` da bu savol allaqachon hal
 * qilingan (Q12) — oy uchun ham oʻsha javob: koʻrinish bizda.
 *
 * 2026-10-23 dan beri tanlagichning roʻyxati ham bizniki
 * (`ui/Select`), shuning uchun test endi koʻrinadigan matn va
 * ochilgan roʻyxat bilan ishlaydi — DOM `value` bilan emas.
 */

import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MonthInput } from '../ui/MonthInput'

const show = (value = '2026-10', onChange = vi.fn()) => {
  render(<MonthInput value={value} onChange={onChange} label="Oy" />)
  return {
    onChange,
    month: screen.getByRole('combobox', { name: 'Oy' }),
    year: screen.getByRole('combobox', { name: 'Yil' }),
  }
}

describe('MonthInput', () => {
  it('oyni oʻzbekcha nomi bilan koʻrsatadi', () => {
    const { month, year } = show()
    expect(month).toHaveTextContent('Oktabr')
    expect(year).toHaveTextContent('2026')
  })

  it('oy tanlanganda yyyy-mm qaytaradi', () => {
    const { month, onChange } = show()
    fireEvent.click(month)
    fireEvent.click(screen.getByRole('option', { name: 'Mart' }))
    expect(onChange).toHaveBeenCalledWith('2026-03')
  })

  it('yil tanlanganda oy saqlanadi', () => {
    const { year, onChange } = show()
    fireEvent.click(year)
    fireEvent.click(screen.getByRole('option', { name: '2025' }))
    expect(onChange).toHaveBeenCalledWith('2025-10')
  })

  it('min va max oraligʻidan tashqari yil taklif qilinmaydi', () => {
    render(<MonthInput value="2026-10" onChange={vi.fn()} label="Oy" min="2026-01" max="2026-12" />)
    fireEvent.click(screen.getByRole('combobox', { name: 'Yil' }))
    const list = screen.getByRole('listbox')
    expect(
      within(list)
        .getAllByRole('option')
        .map((item) => item.textContent),
    ).toEqual(['2026'])
  })

  it('chegaradan tashqaridagi oy tanlanmaydi', () => {
    render(<MonthInput value="2026-10" onChange={vi.fn()} label="Oy" max="2026-10" />)
    fireEvent.click(screen.getByRole('combobox', { name: 'Oy' }))
    for (const name of ['Noyabr', 'Dekabr']) {
      expect(screen.getByRole('option', { name })).toHaveAttribute('aria-disabled', 'true')
    }
    expect(screen.getByRole('option', { name: 'Sentabr' })).not.toHaveAttribute('aria-disabled')
  })
})
