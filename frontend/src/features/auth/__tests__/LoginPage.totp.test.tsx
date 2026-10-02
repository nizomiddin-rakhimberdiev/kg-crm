/**
 * Kirishda ikkinchi omil (PLAN 5.4).
 *
 * Tekshiriladigan ikki narsa — ikkalasi ham shu sahifaning ustuvor
 * xulqi:
 *
 * * kod maydoni **oldindan koʻrinmaydi** — u server `TOTP_REQUIRED`
 *   deganidan keyin ochiladi, chunki maydonning oʻzi "bu hisobda 2FA
 *   yoqilgan" degan maʼlumotni begonaga aytib qoʻyardi;
 * * `TOTP_REQUIRED` **xato sifatida koʻrsatilmaydi** — u bosqich.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api/types'
import { authApi } from '../api'
import LoginPage from '../pages/LoginPage'

vi.mock('../api', () => ({
  authApi: { login: vi.fn(), selectOrganization: vi.fn(), requestPasswordReset: vi.fn() },
}))

const applySession = vi.fn()
vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => ({ applySession }),
}))

const show = () =>
  render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>,
  )

const fillCredentials = () => {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'ega@bogcha.uz' } })
  fireEvent.change(screen.getByLabelText('Parol'), { target: { value: 'Juda-Kuchli-2026' } })
  fireEvent.click(screen.getByText('Kirish'))
}

describe('LoginPage — ikkinchi omil', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('kod maydoni sukut boʻyicha yoʻq', () => {
    show()
    expect(screen.queryByLabelText('Authenticator kodi')).not.toBeInTheDocument()
  })

  it('server soʻraganda maydon ochiladi va xato koʻrsatilmaydi', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce(
      new ApiError('TOTP_REQUIRED', 'Authenticator kodini kiriting.', null, 401),
    )
    show()
    fillCredentials()

    await waitFor(() => expect(screen.getByLabelText('Authenticator kodi')).toBeInTheDocument())
    // Bu xato emas, bosqich.
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('kiritilgan kod soʻrovga qoʻshiladi', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce(
      new ApiError('TOTP_REQUIRED', 'Authenticator kodini kiriting.', null, 401),
    )
    show()
    fillCredentials()
    await waitFor(() => expect(screen.getByLabelText('Authenticator kodi')).toBeInTheDocument())

    vi.mocked(authApi.login).mockResolvedValueOnce({
      access: 'a',
      user: {},
      subscription: {},
    } as never)
    fireEvent.change(screen.getByLabelText('Authenticator kodi'), { target: { value: '123456' } })
    fireEvent.click(screen.getByText('Kirish'))

    await waitFor(() =>
      expect(authApi.login).toHaveBeenLastCalledWith('ega@bogcha.uz', 'Juda-Kuchli-2026', '123456'),
    )
    expect(applySession).toHaveBeenCalled()
  })

  it('haqiqiy xato esa koʻrsatiladi', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce(
      new ApiError('AUTHENTICATION_REQUIRED', 'Email yoki parol notoʻgʻri.', null, 401),
    )
    show()
    fillCredentials()

    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Email yoki parol notoʻgʻri.'),
    )
    expect(screen.queryByLabelText('Authenticator kodi')).not.toBeInTheDocument()
  })
})
