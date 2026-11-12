/**
 * Self-signup form (PLAN 6.7): it sends a request and then only says
 * "check your e-mail" — nothing on the page claims a kindergarten exists.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api/types'
import { signupApi } from '../api'
import SignupPage from '../pages/SignupPage'

vi.mock('../api', () => ({ signupApi: { request: vi.fn(), confirm: vi.fn() } }))

describe('SignupPage', () => {
  it('sends the request with consent, policy version and an empty honeypot', async () => {
    vi.mocked(signupApi.request).mockResolvedValueOnce({ sent: true })
    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    )
    const fill = (label: string, value: string) =>
      fireEvent.change(screen.getByLabelText(label), { target: { value } })
    fill('Bogʻcha nomi', 'Quyoshcha')
    fill('Ismingiz', 'Dilnoza')
    fill('Email', 'egasi@quyosh.uz')
    fill('Telefon', '+998901112233')
    fill('Shahar', 'Toshkent')
    fill('Bolalar soni', '40')
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Bogʻchani ochish' }))

    await waitFor(() => expect(screen.getByText('Pochtangizni tekshiring')).toBeInTheDocument())
    const body = vi.mocked(signupApi.request).mock.calls[0][0]
    expect(body).toMatchObject({
      email: 'egasi@quyosh.uz',
      children_count: 40,
      consent: true,
      website: '',
    })
    expect(body.privacy_policy_version).toBeTruthy()
  })

  it('puts a field error under its field (audit 2026-11-12, J5)', async () => {
    vi.mocked(signupApi.request).mockRejectedValueOnce(
      new ApiError('VALIDATION_ERROR', 'Maʼlumot notoʻgʻri.', {
        email: ['Bu email bilan bogʻcha allaqachon bor.'],
      }),
    )
    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    )
    const fill = (label: string, value: string) =>
      fireEvent.change(screen.getByLabelText(label), { target: { value } })
    fill('Bogʻcha nomi', 'Quyoshcha')
    fill('Ismingiz', 'Dilnoza')
    fill('Email', 'egasi@quyosh.uz')
    fill('Telefon', '+998901112233')
    fill('Shahar', 'Toshkent')
    fill('Bolalar soni', '40')
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: 'Bogʻchani ochish' }))

    const message = await screen.findByText('Bu email bilan bogʻcha allaqachon bor.')
    const email = screen.getByLabelText('Email')
    expect(email).toHaveAttribute('aria-invalid', 'true')
    expect(email.getAttribute('aria-describedby')).toBe(message.id)
  })
})
