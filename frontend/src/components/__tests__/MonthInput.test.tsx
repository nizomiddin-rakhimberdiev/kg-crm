/**
 * Oy maydoni (audit, 2026-10-21).
 *
 * Native `input[type=month]` oy nomini **brauzer lokali** bo'yicha
 * chiqaradi: butun interfeys o'zbekcha turganda tanlagichda
 * "October 2026" yozilardi. `DateInput` da bu savol allaqachon hal
 * qilingan (Q12) — oy uchun ham o'sha javob: ko'rinish bizda.
 */

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MonthInput } from '../ui/MonthInput'

const show = (value = '2026-10', onChange = vi.fn()) => {
  render(<MonthInput value={value} onChange={onChange} label="Oy" />)
  return {
    onChange,
    month: screen.getByLabelText('Oy') as HTMLSelectElement,
    year: screen.getByLabelText('Yil') as HTMLSelectElement,
  }
}

describe('MonthInput', () => {
  it('oyni oʻzbekcha nomi bilan koʻrsatadi', () => {
    const { month, year } = show()
    expect(month.value).toBe('10')
    expect(year.value).toBe('2026')
    expect(screen.getByRole('option', { name: 'Oktabr' })).toBeTruthy()
    expect(screen.queryByRole('option', { name: 'October' })).toBeNull()
  })

  it('oy tanlanganda yyyy-mm qaytaradi', () => {
    const { month, onChange } = show()
    fireEvent.change(month, { target: { value: '3' } })
    expect(onChange).toHaveBeenCalledWith('2026-03')
  })

  it('yil tanlanganda oy saqlanadi', () => {
    const { year, onChange } = show()
    fireEvent.change(year, { target: { value: '2025' } })
    expect(onChange).toHaveBeenCalledWith('2025-10')
  })

  it('min va max oraligʻidan tashqari yil taklif qilinmaydi', () => {
    render(<MonthInput value="2026-10" onChange={vi.fn()} label="Oy" min="2026-01" max="2026-12" />)
    const years = screen.getByLabelText('Yil') as HTMLSelectElement
    expect([...years.options].map((option) => option.value)).toEqual(['2026'])
  })

  it('chegaradan tashqaridagi oy tanlanmaydi', () => {
    render(<MonthInput value="2026-10" onChange={vi.fn()} label="Oy" max="2026-10" />)
    const months = screen.getByLabelText('Oy') as HTMLSelectElement
    const disabled = [...months.options].filter((option) => option.disabled)
    expect(disabled.map((option) => option.value)).toEqual(['11', '12'])
  })
})
