import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, matchRoutes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { routes } from '@/router'
import { marketingApi } from '@/features/marketing/api'
import { copy, groupThousands } from '../content'
import { LandingPage } from '../pages/LandingPage'

vi.mock('@/features/marketing/api', () => ({
  marketingApi: { pricing: vi.fn(), createLead: vi.fn() },
}))

const quote = (children: number) => {
  const extra = Math.max(0, Math.ceil((children - 50) / 10))
  const monthly = 400_000 + extra * 50_000
  return {
    children,
    currency: 'UZS',
    monthly: { total_amount: String(monthly) },
    annual: { total_amount: String(monthly * 12 * 0.75) },
    annual_before_discount: String(monthly * 12),
    annual_saving: String(monthly * 12 * 0.25),
    plan: { included_children: 50, overage_step_children: 10, overage_step_price: '50000' },
  }
}

beforeEach(() => {
  vi.mocked(marketingApi.pricing).mockImplementation(async (children) => quote(children))
})

describe('content', () => {
  it('UZ va RU bir xil kalitlarga ega', () => {
    const keys = (o: object): string[] =>
      Object.entries(o).flatMap(([k, v]) =>
        v && typeof v === 'object' && !Array.isArray(v) ? keys(v).map((x) => `${k}.${x}`) : [k],
      )
    expect(keys(copy.ru).sort()).toEqual(keys(copy.uz).sort())
  })

  it('narx misollari ADR-12 formulasiga mos (400k / 50, +50k / 10, yillik −25 %)', () => {
    for (const locale of ['uz', 'ru'] as const) {
      for (const row of copy[locale].pricing.examples) {
        expect(row.monthly).toBe(Number(quote(row.children).monthly.total_amount))
      }
    }
    expect(copy.uz.pricing.examples.map((r) => r.monthly * 12 * 0.75)).toEqual([
      3_600_000, 4_050_000, 4_500_000, 4_950_000,
    ])
  })

  it('moliya raqamlari bir-biriga mos: to‘lovlar − xarajat − ish haqi = balans', () => {
    for (const locale of ['uz', 'ru'] as const) {
      const m = Object.fromEntries(copy[locale].finance.metrics.map((x) => [x.id, x.value]))
      expect(m.payments - m.expenses - m.salaries).toBe(m.balance)
      expect(m.revenue - m.payments).toBe(m.debt)
    }
  })

  it('uydirma ijtimoiy dalil yo‘q: sharh, mijoz logosi, mukofot', () => {
    const all = JSON.stringify(copy).toLowerCase()
    for (const banned of [
      'award',
      'mukofot',
      'testimonial',
      'sharh',
      '500+ bog',
      'trusted by',
      'клиентов',
    ]) {
      expect(all).not.toContain(banned)
    }
  })
})

describe('marshrut', () => {
  it('/uz va /ru bosh sahifa; eski /test-redesign havolasi yo‘naltiriladi', () => {
    const leaf = (p: string) => {
      const m = matchRoutes(routes, p)
      return m?.[m.length - 1]?.route.path
    }
    expect(leaf('/uz')).toBe('/uz')
    expect(leaf('/ru')).toBe('/ru')
    expect(leaf('/test-redesign')).toBe('/test-redesign')
    expect(leaf('/uz/privacy')).toBe('/uz/privacy')
  })
})

describe('LandingPage', () => {
  it('render bo‘ladi: hero, narx, forma, SEO meta', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/uz']}>
          <LandingPage locale="uz" />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(copy.uz.hero.title)
    expect(await screen.findByText(groupThousands(400_000))).toBeInTheDocument()
    expect(screen.getByRole('button', { name: copy.uz.lead.submit })).toBeInTheDocument()
    expect(document.head.querySelector('meta[name="robots"]')).toBeNull()
    expect(document.title).toBe(copy.uz.seo.title)
    expect(document.head.querySelector('link[rel="canonical"]')?.getAttribute('href')).toBe(
      'https://radix-crm.uz/uz',
    )
    expect(document.head.querySelector('script[data-jsonld="faq"]')?.textContent).toContain(
      'FAQPage',
    )
    // Uzbek apostrophes: faqat ‘ (U+2018) va ’ (U+2019), ASCII ' emas.
    expect(copy.uz.hero.title).not.toContain("'")
  })
})
