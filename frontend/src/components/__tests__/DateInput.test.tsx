/**
 * Sana maydoni (Q12, PLAN 4.1).
 *
 * Asosiy savol: xodim `02.10.2026` deb yozsa, tizim buni oktabrning
 * ikkisi deb tushunadimi — brauzer lokalidan qat'i nazar? Native
 * `input[type=date]` da bu kafolat yo'q edi: bir xodimda
 * `02.10.2026`, boshqasida `10/02/2026` chiqardi.
 */

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DateInput } from '../ui/DateInput'

const show = (value = '', onChange = vi.fn()) => {
  const result = render(<DateInput value={value} onChange={onChange} aria-label="Sana" />)
  return { ...result, onChange, field: screen.getByLabelText('Sana') as HTMLInputElement }
}

describe('DateInput', () => {
  it('ISO qiymatni dd.mm.yyyy ko‘rinishida ko‘rsatadi', () => {
    const { field } = show('2026-10-02')
    expect(field.value).toBe('02.10.2026')
  })

  it('yozilgan sanani ISO‘ga o‘giradi', () => {
    const { field, onChange } = show()
    fireEvent.change(field, { target: { value: '02.10.2026' } })
    expect(onChange).toHaveBeenCalledWith('2026-10-02')
  })

  it('nuqtalarni o‘zi qo‘yadi', () => {
    const { field, onChange } = show()
    fireEvent.change(field, { target: { value: '02102026' } })
    expect(field.value).toBe('02.10.2026')
    expect(onChange).toHaveBeenCalledWith('2026-10-02')
  })

  it('mavjud bo‘lmagan sanani yubormaydi', () => {
    const { field, onChange } = show()
    fireEvent.change(field, { target: { value: '31.02.2026' } })
    // `new Date(2026, 1, 31)` jimgina 3-martga suriladi — shuning
    // uchun bunday qiymat umuman uzatilmaydi.
    expect(onChange).not.toHaveBeenCalled()
    expect(field).toHaveAttribute('aria-invalid', 'true')
  })

  it('yarim yozilgan sana maydonda qolmaydi', () => {
    const { field } = show('2026-10-02')
    fireEvent.change(field, { target: { value: '02.1' } })
    fireEvent.blur(field)
    expect(field.value).toBe('02.10.2026')
  })

  it('tozalash bo‘sh qiymat yuboradi', () => {
    const { field, onChange } = show('2026-10-02')
    fireEvent.change(field, { target: { value: '' } })
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('kalendar tugmasi nomlangan', () => {
    show()
    expect(screen.getByLabelText('Kalendardan tanlash')).toBeInTheDocument()
  })
})
