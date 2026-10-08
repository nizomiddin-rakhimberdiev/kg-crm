/**
 * The parent's payment page (PLAN 6.1): provider buttons for an open
 * invoice, a "paid" state, and a plain message for a dead link.
 */

import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api/types'
import { onlinePaymentsApi, type PublicPayLink } from '../api'
import PayPage from '../pages/PayPage'

vi.mock('../api', async (original) => ({
  ...(await original<typeof import('../api')>()),
  onlinePaymentsApi: { publicLink: vi.fn() },
}))

const LINK: PublicPayLink = {
  kindergarten: 'Alfa Bogʻcha',
  logo_url: null,
  contact_phone: '+998 90 123 45 67',
  child: 'Ali V.',
  invoice: 'INV-2026-09-0001',
  period: '09.2026',
  amount_due: '1500000.00',
  payable: '1500000.00',
  is_paid: false,
  providers: { payme: 'https://checkout.paycom.uz/abc' },
}

const show = () =>
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={['/pay/tok']}>
        <Routes>
          <Route path="/pay/:token" element={<PayPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )

describe('PayPage', () => {
  beforeEach(() => vi.mocked(onlinePaymentsApi.publicLink).mockReset())

  it('shows the bill and a button per connected provider', async () => {
    vi.mocked(onlinePaymentsApi.publicLink).mockResolvedValue(LINK)
    show()
    expect(await screen.findByText('Ali V.')).toBeInTheDocument()
    const button = screen.getByRole('link', { name: /Payme orqali toʻlash/ })
    expect(button).toHaveAttribute('href', LINK.providers.payme)
    expect(screen.queryByText(/Click orqali/)).not.toBeInTheDocument()
  })

  it('a paid invoice shows no buttons', async () => {
    vi.mocked(onlinePaymentsApi.publicLink).mockResolvedValue({
      ...LINK,
      is_paid: true,
      payable: '0.00',
      providers: {},
    })
    show()
    expect(await screen.findByText('Toʻlov qabul qilindi')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /toʻlash/ })).not.toBeInTheDocument()
  })

  it('a dead link says to ask for a new one', async () => {
    vi.mocked(onlinePaymentsApi.publicLink).mockRejectedValueOnce(
      new ApiError('NOT_FOUND', 'Not found', null, 404),
    )
    show()
    expect(await screen.findByText('Havola eskirgan yoki notoʻgʻri')).toBeInTheDocument()
  })
})
