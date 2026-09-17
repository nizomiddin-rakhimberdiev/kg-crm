import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { marketingApi } from '../api'
import { copy } from '../content'
import { MarketingPage } from './MarketingPage'

vi.mock('../api', () => ({
  marketingApi: { pricing: vi.fn(), createLead: vi.fn() },
}))

/** Backend `pricing.quote()` ning 50 va 60 bola uchun haqiqiy javobi (ADR-12). */
const pricingFor = (children: number) => {
  const steps = Math.max(0, Math.ceil((children - 50) / 10))
  const monthly = 400_000 + steps * 50_000
  const before = monthly * 12
  return {
    children,
    currency: 'UZS',
    monthly: { total_amount: `${monthly}.00` },
    annual: { total_amount: `${before * 0.75}.00` },
    annual_before_discount: `${before}.00`,
    annual_saving: `${before * 0.25}.00`,
    plan: { included_children: 50, overage_step_children: 10, overage_step_price: '50000.00' },
  }
}

function renderPage(locale: 'uz' | 'ru' = 'uz') {
  vi.mocked(marketingApi.pricing).mockImplementation(async (children) => pricingFor(children))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <MarketingPage locale={locale} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const section = (id: string) => document.getElementById(id) as HTMLElement

describe('MarketingPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders the Uzbek page with one H1 and the live base price in the hero', async () => {
    renderPage('uz')
    const headings = screen.getAllByRole('heading', { level: 1 })
    expect(headings).toHaveLength(1)
    expect(headings[0]).toHaveTextContent(copy.uz.hero.title)
    // Narx trust-point'i hero'da, API'dan (brif §3).
    expect(await screen.findByText(/50 bolagacha — 400 000 so‘m\/oydan/)).toBeInTheDocument()
    expect(marketingApi.pricing).toHaveBeenCalledWith(50)
  })

  it('renders Russian content and offers a language switch', () => {
    renderPage('ru')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(copy.ru.hero.title)
    // Til almashtirgich header'da ham, footer'da ham — ikkalasi /uz ga.
    const switches = screen.getAllByRole('link', { name: 'O‘zbekcha' })
    expect(switches.length).toBeGreaterThanOrEqual(2)
    for (const link of switches) expect(link).toHaveAttribute('href', '/uz')
  })

  it('shows the calculator quote and requests a fresh one when children change', async () => {
    renderPage()
    const pricing = section('pricing')
    expect(await within(pricing).findByText('400 000')).toBeInTheDocument()

    fireEvent.change(within(pricing).getByLabelText('Bolalar soni'), { target: { value: '60' } })
    await waitFor(() => expect(marketingApi.pricing).toHaveBeenCalledWith(60))
    expect(await within(pricing).findByText('450 000')).toBeInTheDocument()
  })

  it('switches between monthly and annual and shows the 25% saving', async () => {
    const user = userEvent.setup()
    renderPage()
    const pricing = section('pricing')
    await within(pricing).findByText('400 000')

    await user.click(within(pricing).getByRole('button', { name: /Yillik/ }))
    expect(await within(pricing).findByText('3 600 000')).toBeInTheDocument()
    expect(within(pricing).getByText('25% chegirma')).toBeInTheDocument()
    // Chegirmasiz summa chizilgan holda ko'rinadi, tejov aniq.
    expect(within(pricing).getByText('4 800 000 so‘m')).toHaveClass('line-through')
    expect(within(pricing).getByText(/Yillik to‘lovda tejaysiz: 1 200 000 so‘m/)).toBeInTheDocument()
  })

  it('requires privacy consent and submits only after consent is given', async () => {
    const user = userEvent.setup()
    vi.mocked(marketingApi.createLead).mockResolvedValue({ id: 'lead-id', status: 'new' })
    renderPage()
    const form = section('demo')

    await user.type(within(form).getByLabelText('Ismingiz'), 'Dilshod')
    await user.type(within(form).getByLabelText('Telefon raqam'), '901234567')
    await user.type(within(form).getByLabelText('Bog‘cha nomi'), 'Mehrjon')
    await user.type(within(form).getByLabelText('Bolalar soni'), '60')
    await user.type(within(form).getByLabelText('Shahar / hudud'), 'Toshkent')

    await user.click(within(form).getByRole('button', { name: 'Demo so‘rash' }))
    expect(marketingApi.createLead).not.toHaveBeenCalled()

    await user.click(within(form).getByRole('checkbox'))
    await user.click(within(form).getByRole('button', { name: 'Demo so‘rash' }))
    await waitFor(() => expect(marketingApi.createLead).toHaveBeenCalledOnce())
    expect(await screen.findByRole('status')).toHaveTextContent('So‘rovingiz qabul qilindi')
  })

  it('opens the mobile navigation with the demo CTA first', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: 'Menyuni ochish' }))
    const mobileNav = screen.getByRole('navigation', { name: 'Mobil navigatsiya' })
    expect(within(mobileNav).getByRole('link', { name: 'Demo olish' })).toBeInTheDocument()
    expect(within(mobileNav).getByRole('link', { name: 'Narxlar' })).toBeInTheDocument()
  })

  // Ikki sotuv modeli (ADR-13) — sahifadagi eng muhim tijorat bloki.
  it('offers both delivery models, with the one-off licence priced on request', () => {
    renderPage('uz')
    const delivery = section('delivery')
    expect(within(delivery).getByText('Bulutli obuna')).toBeInTheDocument()
    expect(within(delivery).getByText('Alohida o‘rnatma')).toBeInTheDocument()
    expect(within(delivery).getByText('Kelishuv asosida')).toBeInTheDocument()
  })

  it('shows only real roles in "who is it for"', () => {
    renderPage('uz')
    // Tizimdagi haqiqiy rollar (apps/accounts/constants.py). "Administrator"
    // degan rol yo'q va u sahifada ham bo'lmasligi kerak.
    for (const role of ['Bog‘cha egasi', 'Direktor', 'Kassir', 'Menejer']) {
      expect(screen.getByRole('heading', { name: role })).toBeInTheDocument()
    }
    expect(screen.queryByText('Administrator')).not.toBeInTheDocument()
  })

  it('makes no unverifiable social-proof or security claims', () => {
    renderPage('uz')
    const text = document.body.textContent ?? ''
    for (const banned of ['500+', '10 000+', '99.9', '100% xavfsiz', 'bank darajasi']) {
      expect(text).not.toContain(banned)
    }
  })

  // RU sahifada o'zbekcha, UZ sahifada ruscha so'z qolmasligi kerak.
  it('keeps each language pure', () => {
    renderPage('ru')
    const ru = document.body.textContent ?? ''
    expect(ru).not.toMatch(/bog‘cha|so‘m|Demo olish|Kirish/i)

    document.body.innerHTML = ''
    renderPage('uz')
    const uz = document.body.textContent ?? ''
    expect(uz).not.toMatch(/детск|сум\b|Получить демо/i)
  })
})
