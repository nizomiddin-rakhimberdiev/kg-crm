/**
 * Yangi parol oʻrnatish sahifasi (PLAN 5.2).
 *
 * Havolada `uid` va `token` keladi; ularni oldindan tekshirmaymiz —
 * tekshirish uchun alohida endpoint "bu token haqiqiymi?" degan
 * savolga javob beradigan orakul boʻlib qolardi.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { authApi } from '../api'
import ResetPasswordPage from '../pages/ResetPasswordPage'

vi.mock('../api', () => ({
  authApi: { confirmPasswordReset: vi.fn() },
}))

const show = (query: string) =>
  render(
    <MemoryRouter initialEntries={[`/reset-password${query}`]}>
      <ResetPasswordPage />
    </MemoryRouter>,
  )

describe('ResetPasswordPage', () => {
  it('toʻliq havola bilan forma koʻrsatiladi', () => {
    show('?uid=abc&token=xyz')
    expect(screen.getByLabelText('Yangi parol')).toBeInTheDocument()
    expect(screen.getByLabelText('Parolni takrorlang')).toBeInTheDocument()
  })

  it('havola chala boʻlsa forma koʻrsatilmaydi', () => {
    show('?uid=abc')
    expect(screen.queryByLabelText('Yangi parol')).not.toBeInTheDocument()
    expect(screen.getByText(/toʻliq emas/)).toBeInTheDocument()
  })

  it('parollar mos kelmasa yuborilmaydi', () => {
    show('?uid=abc&token=xyz')
    fireEvent.change(screen.getByLabelText('Yangi parol'), { target: { value: 'Birinchi-2026' } })
    fireEvent.change(screen.getByLabelText('Parolni takrorlang'), {
      target: { value: 'Ikkinchi-2026' },
    })
    expect(screen.getByText('Parollar mos kelmadi.')).toBeInTheDocument()
    // Xato terilgan parol hisobga kirish imkonini YOʻQOTADI.
    expect(authApi.confirmPasswordReset).not.toHaveBeenCalled()
  })

  it('muvaffaqiyatdan keyin sessiyalar yopilgani aytiladi', async () => {
    vi.mocked(authApi.confirmPasswordReset).mockResolvedValue({ detail: 'ok' })
    show('?uid=abc&token=xyz')
    fireEvent.change(screen.getByLabelText('Yangi parol'), {
      target: { value: 'Yangi-Parol-2026' },
    })
    fireEvent.change(screen.getByLabelText('Parolni takrorlang'), {
      target: { value: 'Yangi-Parol-2026' },
    })
    fireEvent.click(screen.getByText('Parolni oʻrnatish'))

    await waitFor(() => expect(screen.getByText(/sessiyalar yopildi/)).toBeInTheDocument())
    expect(authApi.confirmPasswordReset).toHaveBeenCalledWith('abc', 'xyz', 'Yangi-Parol-2026')
  })

  it('parol koʻrsatish tugmasi ishlaydi', () => {
    show('?uid=abc&token=xyz')
    const field = screen.getByLabelText('Yangi parol') as HTMLInputElement
    expect(field.type).toBe('password')
    fireEvent.click(screen.getAllByLabelText('Parolni koʻrsatish')[0])
    expect(field.type).toBe('text')
  })
})
