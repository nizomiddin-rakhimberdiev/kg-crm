import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { marketingApi } from '../api'
import { MarketingPage } from './MarketingPage'

vi.mock('../api', () => ({
  marketingApi: { pricing: vi.fn(), createLead: vi.fn() },
}))

const pricing = {
  children: 50,
  currency: 'UZS',
  monthly: { total_amount: '400000.00' },
  annual: { total_amount: '3600000.00' },
  annual_before_discount: '4800000.00',
  annual_saving: '1200000.00',
  plan: { included_children: 50, overage_step_children: 10, overage_step_price: '50000.00' },
}

function renderPage(locale: 'uz' | 'ru' = 'uz') {
  vi.mocked(marketingApi.pricing).mockResolvedValue(pricing)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><MarketingPage locale={locale} /></MemoryRouter></QueryClientProvider>)
}

describe('MarketingPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the Uzbek public page and its current subscription quote', async () => {
    renderPage('uz')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Bog‘changiz boshqaruvini')
    // Loose `/400 000/` matches BOTH the live monthly quote AND the FAQ
    // paragraph that mentions the same figure in a sentence. Scoping to
    // the pricing calculator section disambiguates without weakening
    // the assertion — it still fails if the calculator itself shows
    // the wrong number.
    const pricingSection = document.getElementById('pricing') as HTMLElement
    expect(await within(pricingSection).findByText(/400 000/)).toBeInTheDocument()
    expect(marketingApi.pricing).toHaveBeenCalledWith(50)
  })

  it('renders Russian content and offers a language switch', () => {
    renderPage('ru')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Соберите управление')
    expect(screen.getByRole('link', { name: 'O‘zbekcha' })).toHaveAttribute('href', '/uz')
  })

  it('requests a fresh server quote when the calculator changes', async () => {
    renderPage()
    const input = screen.getByLabelText('Bog‘changizda nechta bola bor?')
    fireEvent.change(input, { target: { value: '60' } })
    await waitFor(() => expect(marketingApi.pricing).toHaveBeenCalledWith(60))
  })

  it('requires privacy consent and submits only after consent is given', async () => {
    const user = userEvent.setup()
    vi.mocked(marketingApi.createLead).mockResolvedValue({ id: 'lead-id', status: 'new' })
    renderPage()
    await user.type(screen.getByLabelText('Ismingiz'), 'Dilshod')
    await user.type(screen.getByLabelText('Telefon raqam'), '901234567')
    await user.type(screen.getByLabelText('Bog‘cha nomi'), 'Mehrjon')
    await user.type(screen.getByLabelText('Bolalar soni'), '60')
    await user.type(screen.getByLabelText('Shahar / hudud'), 'Toshkent')
    await user.click(screen.getByRole('button', { name: 'Zayavka yuborish' }))
    expect(marketingApi.createLead).not.toHaveBeenCalled()
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Zayavka yuborish' }))
    await waitFor(() => expect(marketingApi.createLead).toHaveBeenCalledOnce())
    expect(await screen.findByRole('status')).toHaveTextContent('Zayavkangiz qabul qilindi')
  })

  it('opens the mobile navigation control', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: 'Open menu' }))
    expect(screen.getAllByRole('link', { name: 'Narxlar' }).length).toBeGreaterThan(1)
  })
})
