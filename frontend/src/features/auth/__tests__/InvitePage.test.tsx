/**
 * Taklif havolasi sahifasi (PLAN 5.5).
 *
 * Yangi bogʻcha egasi tizimni birinchi marta shu sahifada ochadi,
 * shuning uchun tekshiriladigan narsalar ham oʻsha: havola toʻliqmi,
 * parol takrori mos keladimi, va "parolni biz bilmaymiz" degan gap
 * koʻrinadimi — u mijozning birinchi savolini oldini oladi.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { authApi } from '../api'
import InvitePage from '../pages/InvitePage'

vi.mock('../api', () => ({
  authApi: { acceptInvite: vi.fn() },
}))

const show = (query: string) =>
  render(
    <MemoryRouter initialEntries={[`/invite${query}`]}>
      <InvitePage />
    </MemoryRouter>,
  )

describe('InvitePage', () => {
  it('token bilan forma koʻrsatiladi va parol bizda yoʻqligi aytiladi', () => {
    show('?token=abc')
    expect(screen.getByLabelText('Parol')).toBeInTheDocument()
    expect(screen.getByText(/biz uni bilmaymiz/)).toBeInTheDocument()
  })

  it('tokensiz forma koʻrsatilmaydi', () => {
    show('')
    expect(screen.queryByLabelText('Parol')).not.toBeInTheDocument()
    expect(screen.getByText(/toʻliq emas/)).toBeInTheDocument()
  })

  it('parollar mos kelmasa yuborilmaydi', () => {
    show('?token=abc')
    fireEvent.change(screen.getByLabelText('Parol'), { target: { value: 'Birinchi-2026' } })
    fireEvent.change(screen.getByLabelText('Parolni takrorlang'), {
      target: { value: 'Ikkinchi-2026' },
    })
    expect(screen.getByText('Parollar mos kelmadi.')).toBeInTheDocument()
    expect(authApi.acceptInvite).not.toHaveBeenCalled()
  })

  it('muvaffaqiyatdan keyin kirishga taklif qiladi', async () => {
    vi.mocked(authApi.acceptInvite).mockResolvedValue({ detail: 'ok' })
    show('?token=abc')
    fireEvent.change(screen.getByLabelText('Parol'), { target: { value: 'Birinchi-Parol-2026' } })
    fireEvent.change(screen.getByLabelText('Parolni takrorlang'), {
      target: { value: 'Birinchi-Parol-2026' },
    })
    fireEvent.click(screen.getByText('Parolni oʻrnatish'))

    await waitFor(() =>
      expect(screen.getByText('Parol oʻrnatildi. Endi kirishingiz mumkin.')).toBeInTheDocument(),
    )
    expect(authApi.acceptInvite).toHaveBeenCalledWith('abc', 'Birinchi-Parol-2026')
  })
})
