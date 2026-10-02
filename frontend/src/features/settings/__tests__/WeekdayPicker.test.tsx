/**
 * Ish kunlari katakchalari (PLAN 4.2).
 *
 * Auditda bu sozlama `1,2,3,4,5` deb erkin matnda turardi. Saqlanadigan
 * shakl oʻzgarmadi — faqat koʻrinish, shuning uchun test ikkisini ham
 * tekshiradi: ekranda kun nomlari, saqlashda ISO raqamlar.
 */

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { WeekdayPicker, formatWeekdays, parseWeekdays } from '../components/WeekdayPicker'

describe('parseWeekdays', () => {
  it('ISO raqamlarni oʻqiydi', () => {
    expect(parseWeekdays('1,2,3,4,5')).toEqual([1, 2, 3, 4, 5])
    expect(parseWeekdays('1, 6')).toEqual([1, 6])
  })

  it('chegaradan tashqaridagi qiymatni tashlaydi', () => {
    // `0` va `8` hafta kuni emas — ular hisobni jimgina buzardi.
    expect(parseWeekdays('0,1,8,x')).toEqual([1])
    expect(parseWeekdays(null)).toEqual([])
  })

  it('tartiblab va takrorsiz yozadi', () => {
    expect(formatWeekdays([5, 1, 1, 3])).toBe('1,3,5')
  })
})

describe('WeekdayPicker', () => {
  it('tanlangan kunlar belgilangan', () => {
    render(<WeekdayPicker value="1,2,3,4,5" onChange={vi.fn()} />)
    expect((screen.getByLabelText('Dushanba') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByLabelText('Shanba') as HTMLInputElement).checked).toBe(false)
  })

  it('kun qoʻshilganda ISO shaklda saqlanadi', () => {
    const onChange = vi.fn()
    render(<WeekdayPicker value="1,2,3,4,5" onChange={onChange} />)
    fireEvent.click(screen.getByLabelText('Shanba'))
    expect(onChange).toHaveBeenCalledWith('1,2,3,4,5,6')
  })

  it('oxirgi kunni olib tashlashga yoʻl qoʻymaydi', () => {
    // Ish kuni nol boʻlsa kunlik toʻlov nolga boʻlinadi.
    const onChange = vi.fn()
    render(<WeekdayPicker value="1" onChange={onChange} />)
    fireEvent.click(screen.getByLabelText('Dushanba'))
    expect(onChange).not.toHaveBeenCalled()
  })
})
