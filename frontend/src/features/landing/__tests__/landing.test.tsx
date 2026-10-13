import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, matchRoutes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { routes } from '@/router'
import { marketingApi } from '@/features/marketing/api'
import { legal } from '@/features/marketing/legal'
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
    trial_days: 15,
    monthly: { total_amount: String(monthly), months: 1 },
    semiannual: { total_amount: String(monthly * 6 * 0.85), months: 6 },
    annual: { total_amount: String(monthly * 12 * 0.75), months: 12 },
    annual_before_discount: String(monthly * 12),
    annual_saving: String(monthly * 12 * 0.25),
    plan: { included_children: 50, overage_step_children: 10, overage_step_price: '50000' },
  }
}

beforeEach(() => {
  vi.mocked(marketingApi.pricing).mockImplementation(async (children) => quote(children))
})

describe('content', () => {
  it('UZ, RU va EN bir xil kalitlarga ega (namunaviy ekran yorliqlari ham)', () => {
    const keys = (o: object): string[] =>
      Object.entries(o).flatMap(([k, v]) =>
        v && typeof v === 'object' && !Array.isArray(v) ? keys(v).map((x) => `${k}.${x}`) : [k],
      )
    expect(keys(copy.ru).sort()).toEqual(keys(copy.uz).sort())
    expect(keys(copy.en).sort()).toEqual(keys(copy.uz).sort())
    expect(legal.en.privacySections).toHaveLength(legal.uz.privacySections.length)
    expect(legal.en.termsSections).toHaveLength(legal.uz.termsSections.length)
  })

  it('EN va RU matnida o‘zbekcha qolib ketmagan', () => {
    // O'zbek lotin yozuvining o'ziga xos belgilari: o‘ g‘ va ’ bilan yozilgan so'zlar.
    const uzbek = /\b(bo‘|to‘|so‘m|qarz|davomat|guruh|bola|xodim|hisob|kutilmoqda)/i
    const walk = (o: unknown): string[] =>
      typeof o === 'string' ? [o] : o && typeof o === 'object' ? Object.values(o).flatMap(walk) : []
    for (const locale of ['ru', 'en'] as const) {
      const hits = walk(copy[locale]).filter((s) => uzbek.test(s))
      expect(hits, locale).toEqual([])
    }
  })

  it('narx misollari ADR-12 formulasiga mos (400k / 50, +50k / 10, yillik −25 %)', () => {
    for (const locale of ['uz', 'ru', 'en'] as const) {
      for (const row of copy[locale].pricing.examples) {
        expect(row.monthly).toBe(Number(quote(row.children).monthly.total_amount))
      }
    }
    expect(copy.uz.pricing.examples.map((r) => r.monthly * 12 * 0.75)).toEqual([
      3_600_000, 4_050_000, 4_500_000, 4_950_000,
    ])
  })

  it('moliya raqamlari bir-biriga mos: to‘lovlar − xarajat − ish haqi = balans', () => {
    for (const locale of ['uz', 'ru', 'en'] as const) {
      const m = Object.fromEntries(copy[locale].finance.metrics.map((x) => [x.id, x.value]))
      expect(m.payments - m.expenses - m.salaries).toBe(m.balance)
      expect(m.revenue - m.payments).toBe(m.debt)
    }
  })

  it('uydirma ijtimoiy dalil yo‘q: sharh, mijoz logosi, mukofot', () => {
    // `testimonials` — faqat JOY (PLAN 5.7): sarlavhasi bor, mazmuni
    // yo‘q. Uning o‘z nomi tekshiruvdan chetda; mazmuni esa pastdagi
    // testda — bo‘sh bo‘lishi SHART.
    const withoutSlot = Object.fromEntries(
      Object.entries(copy).map(([locale, c]) => [locale, { ...c, testimonials: undefined }]),
    )
    const all = JSON.stringify(withoutSlot).toLowerCase()
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

  it('“Mijozlar fikri” bloki bo‘sh — haqiqiy fikr qo‘shish ONGLI qaror', () => {
    // Bu test ataylab qattiq: fikr qo‘shilganda u yiqiladi va uni
    // o‘zgartirgan odam shu savolga javob beradi — "bu haqiqiy
    // mijozning, ruxsat bilan olingan so‘zimi?". Uydirma iqtibos butun
    // saytga ishonchni yo‘qotadi.
    for (const locale of ['uz', 'ru', 'en'] as const) {
      expect(copy[locale].testimonials.items).toEqual([])
    }
  })
})

describe('mahsulot bilan mos', () => {
  it('sinov taklifi uchala tilda ham bor va 15 kun deyiladi', () => {
    for (const locale of ['uz', 'ru', 'en'] as const) {
      expect(copy[locale].nav.trial).toBeTruthy()
      expect(copy[locale].hero.trial).toMatch(/15/)
      expect(copy[locale].pricing.trial).toMatch(/15/)
    }
  })

  it('ota-onalar, Radix AI va qoʻshimcha imkoniyatlar bloklari toʻldirilgan', () => {
    for (const locale of ['uz', 'ru', 'en'] as const) {
      expect(copy[locale].parents.items).toHaveLength(4)
      expect(copy[locale].intelligence.points).toHaveLength(3)
      // 12, chunki jonli, lekin sotilmay turgan to'rtta imkoniyat qo'shildi:
      // shartnoma, kassadan ortiq chiqim taqig'i (ADR-29), .xlsx eksport,
      // ixtiyoriy 2FA. Son uchala tilda birga o'zgaradi — testning maqsadi
      // ham shu: biri qo'shilib, ikkinchisi unutilsa, bu yer qizaradi.
      expect(copy[locale].extras.items).toHaveLength(12)
      expect(copy[locale].ui.intelligence.evidence).toHaveLength(3)
    }
  })

  it('FAQ mahsulotning bugungi holatini aytadi (sinov, bot, onlayn toʻlov, 6 oy)', () => {
    const uz = copy.uz.faq.items.map((i) => `${i.q} ${i.a}`).join(' ')
    expect(uz).toMatch(/15 kun/)
    expect(uz).toMatch(/Telegram/)
    expect(uz).toMatch(/Payme/)
    expect(uz).toMatch(/6 oylik/)
    // To'lov kechikса ma'lumot o'chmaydi (invariant 11) — bu va'da
    // sahifada YOZILGAN bo'lishi kerak, chunki xaridor buni so'raydi.
    expect(uz).toMatch(/oʻchirilmaydi/)
    for (const locale of ['uz', 'ru', 'en'] as const) {
      expect(copy[locale].faq.items.length).toBe(copy.uz.faq.items.length)
    }
  })
})

describe('marshrut', () => {
  it('/uz, /ru, /en bosh sahifa; eski /test-redesign havolasi yo‘naltiriladi', () => {
    const leaf = (p: string) => {
      const m = matchRoutes(routes, p)
      return m?.[m.length - 1]?.route.path
    }
    expect(leaf('/uz')).toBe('/uz')
    expect(leaf('/ru')).toBe('/ru')
    expect(leaf('/en')).toBe('/en')
    expect(leaf('/en/terms')).toBe('/en/terms')
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

describe('telefon maketi', () => {
  // `matchMedia` stub'i (src/test/setup.ts) har doim `matches: false`
  // qaytaradi, ya'ni bu testlar AYNAN telefon/planshet yo'lini bosib
  // o'tadi — pinned sahna bo'lmasligi kerak.
  const renderPage = () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/uz']}>
          <LandingPage locale="uz" />
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  it('hech bir boʻlim ekran bo-yiga bogʻlangan (vh) balandlik bermaydi', () => {
    const { container } = renderPage()
    const pinned = [...container.querySelectorAll<HTMLElement>('section')].filter((el) =>
      (el.getAttribute('style') ?? '').includes('vh'),
    )
    expect(pinned.map((el) => el.id || el.className.slice(0, 40))).toEqual([])
  })

  it('birinchi chaqiriq — sinov, va u roʻyxatdan oʻtish sahifasiga olib boradi', () => {
    renderPage()
    const trial = screen.getAllByRole('link', { name: new RegExp(copy.uz.hero.trial, 'i') })
    expect(trial.length).toBeGreaterThan(0)
    expect(trial[0].getAttribute('href')).toMatch(/\/signup$/)
  })

  it('yangi boʻlimlar sahifada chizilgan', () => {
    renderPage()
    expect(screen.getByText(copy.uz.parents.title)).toBeInTheDocument()
    expect(screen.getByText(copy.uz.intelligence.title)).toBeInTheDocument()
    expect(screen.getByText(copy.uz.extras.title)).toBeInTheDocument()
  })

  it('narx uchta muddatni koʻrsatadi va summani SERVERDAN oladi', async () => {
    renderPage()
    const half = await screen.findByRole('tab', { name: new RegExp(copy.uz.pricing.semiannual) })
    expect(half).toBeInTheDocument()
    await userEvent.click(half)
    // 50 bola uchun 6 oylik: 400 000 × 6 × 0,85 = 2 040 000.
    expect(await screen.findByText(groupThousands(2_040_000))).toBeInTheDocument()
  })
})

describe('prerender', () => {
  it('9 sahifa: to‘liq matn, meta va FAQ JSON-LD javobning ichida', async () => {
    const { prerenderPages } = await import('@/prerender/entry')
    const pages = prerenderPages()
    expect(pages.map((p) => p.path)).toEqual([
      '/uz',
      '/uz/privacy',
      '/uz/terms',
      '/ru',
      '/ru/privacy',
      '/ru/terms',
      '/en',
      '/en/privacy',
      '/en/terms',
    ])
    const uz = pages[0]
    expect(uz.body).toContain(copy.uz.hero.title)
    expect(uz.body).toContain(copy.uz.faq.items[6].q)
    expect(uz.body.replace(/<[^>]+>/g, ' ').split(/\s+/).length).toBeGreaterThan(800)
    expect(uz.head).toContain(`<title>${copy.uz.seo.title}</title>`)
    expect(uz.head).toContain('rel="canonical" href="https://radix-crm.uz/uz"')
    expect(uz.head).toContain('hreflang="ru" href="https://radix-crm.uz/ru"')
    expect(uz.head).toContain('hreflang="en" href="https://radix-crm.uz/en"')
    expect(uz.head).toContain('hreflang="x-default" href="https://radix-crm.uz/uz"')
    const en = pages[6]
    expect(en.lang).toBe('en')
    expect(en.body).toContain(copy.en.hero.title)
    expect(en.body).toContain(copy.en.ui.hero.alert)
    expect(en.body).toContain(copy.en.ui.roles.branches)
    expect(en.head).toContain('og:locale" content="en_US"')
    expect(en.head).toContain('og-en.png')
    expect(uz.head).toContain('"@type":"FAQPage"')
    // Narx birinchi kadrda «…» emas — kesh content.ts misolidan to‘ldirilgan.
    expect(uz.body).toContain('400 000')
    // Reveal serverda yashirmaydi: kontent JS'siz ko‘rinadi.
    expect(uz.body).not.toContain('reveal-pending')
  })
})
