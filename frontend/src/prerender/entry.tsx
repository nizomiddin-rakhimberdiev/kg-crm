/**
 * Build vaqtidagi prerender — public sahifalarning TAYYOR HTML'i.
 *
 * Nega: SPA serverdan bo'sh qobiq qaytaradi (1.8 KB, 42 so'z), kontentni
 * brauzer chizadi. Google JS'ni kechikib ishga tushiradi; ChatGPT,
 * Telegram/WhatsApp preview, Yandex botlari umuman ishga tushirmaydi —
 * ular uchun sayt bo'm-bo'sh edi. Endi `/uz`, `/ru`, `/en` va huquqiy sahifalar
 * `dist/<yo'l>/index.html` bo'lib yoziladi: matn, meta, JSON-LD — hammasi
 * javobning ichida. React keyin ustidan o'zi chizadi.
 *
 * Bu fayl `vite build --ssr` bilan alohida yig'iladi (scripts/prerender.mjs
 * uni import qiladi). Brauzer bundle'iga kirmaydi.
 */

import { StrictMode } from 'react'
import { renderToString } from 'react-dom/server'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { copy, type Locale } from '@/features/landing/content'
import { LandingPage } from '@/features/landing/pages/LandingPage'
import { landingJsonLd, landingMeta } from '@/features/landing/seo'
import { LegalPage } from '@/features/marketing/pages/MarketingPage'
import { LOCALES, buildPageMeta, headHtml, legalMeta } from '@/features/marketing/seo'

export interface PrerenderedPage {
  /** `/uz`, `/ru/privacy`, `/en/terms` … */
  path: string
  lang: Locale
  head: string
  body: string
}

/**
 * Narx kalkulyatori birinchi kadrda «…» emas, raqam ko'rsatsin: kesh
 * content.ts'dagi misollar bilan to'ldiriladi (50 bolagacha — 400 000;
 * yillik ×12×0,75). Bu ADR-12 formulasi bilan bir xil ekanini test
 * tekshiradi; jonli qiymat baribir API'dan keladi (brauzerda).
 */
function seededClient(locale: Locale): QueryClient {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  })
  const base = copy[locale].pricing.examples[0]
  for (const children of [20, 50]) {
    client.setQueryData(['public-pricing', children], {
      children,
      currency: 'UZS',
      monthly: { total_amount: String(base.monthly) },
      annual: { total_amount: String(base.monthly * 12 * 0.75) },
      annual_before_discount: String(base.monthly * 12),
      annual_saving: String(base.monthly * 12 * 0.25),
      plan: { included_children: 50, overage_step_children: 10, overage_step_price: '50000' },
    })
  }
  return client
}

function render(path: string, locale: Locale, element: React.ReactNode): string {
  return renderToString(
    <StrictMode>
      <QueryClientProvider client={seededClient(locale)}>
        <MemoryRouter initialEntries={[path]}>{element}</MemoryRouter>
      </QueryClientProvider>
    </StrictMode>,
  )
}

export function prerenderPages(): PrerenderedPage[] {
  const pages: PrerenderedPage[] = []
  for (const [locale] of LOCALES) {
    pages.push({
      path: `/${locale}`,
      lang: locale,
      head: headHtml(buildPageMeta(landingMeta(locale)), landingJsonLd(locale)),
      body: render(`/${locale}`, locale, <LandingPage locale={locale} />),
    })
    for (const page of ['privacy', 'terms'] as const) {
      pages.push({
        path: `/${locale}/${page}`,
        lang: locale,
        head: headHtml(buildPageMeta(legalMeta(locale, page))),
        body: render(`/${locale}/${page}`, locale, <LegalPage locale={locale} page={page} />),
      })
    }
  }
  return pages
}
