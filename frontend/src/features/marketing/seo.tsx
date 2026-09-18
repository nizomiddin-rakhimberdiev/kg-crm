/**
 * Public sahifalarning meta yordamchilari + huquqiy sahifalar SEO'si.
 * Bosh sahifa o'z SEO'sini `features/landing/seo.tsx` da shu yordamchilar
 * bilan tuzadi.
 *
 * SPA'da `<title>` va meta teglar qo'lda yangilanadi: `index.html` dagi
 * qiymat barcha marshrutlar uchun bitta bo'lib qolardi, va ulashilgan
 * havola qaysi sahifa bo'lishidan qat'i nazar bir xil ko'rinardi.
 *
 * `Organization` schema ATAYLAB yo'q — unga manzil, telefon va yuridik
 * nom kerak, ular esa hali e'lon qilinmagan. Uydirma tashkilot ma'lumoti
 * qidiruv tizimi uchun ham, mijoz uchun ham yolg'on.
 */

import { useEffect } from 'react'
import { legal, type Locale } from './legal'

export const ORIGIN = 'https://radix-crm.uz'

export function upsertMeta(
  selector: string,
  attribute: 'name' | 'property',
  key: string,
  value: string,
) {
  let element = document.head.querySelector<HTMLMetaElement>(selector)
  if (!element) {
    element = document.createElement('meta')
    element.setAttribute(attribute, key)
    document.head.appendChild(element)
  }
  element.content = value
}

export function upsertLink(rel: string, href: string, hreflang?: string) {
  const selector = hreflang
    ? `link[rel="${rel}"][hreflang="${hreflang}"]`
    : `link[rel="${rel}"]:not([hreflang])`
  let element = document.head.querySelector<HTMLLinkElement>(selector)
  if (!element) {
    element = document.createElement('link')
    element.rel = rel
    if (hreflang) element.hreflang = hreflang
    document.head.appendChild(element)
  }
  element.href = href
}

export function upsertJsonLd(id: string, data: object | null) {
  let element = document.head.querySelector<HTMLScriptElement>(`script[data-jsonld="${id}"]`)
  if (!data) {
    element?.remove()
    return
  }
  if (!element) {
    element = document.createElement('script')
    element.type = 'application/ld+json'
    element.dataset.jsonld = id
    document.head.appendChild(element)
  }
  element.textContent = JSON.stringify(data)
}

/** Bir sahifaning asosiy meta to'plami — bosh sahifa va huquqiy sahifalar uchun umumiy. */
export function applyPageMeta({
  locale,
  title,
  description,
  path,
}: {
  locale: Locale
  title: string
  description: string
  /** Lokal prefiksdan keyingi yo'l: '' (bosh sahifa) yoki '/privacy'. */
  path: string
}) {
  const canonical = `${ORIGIN}/${locale}${path}`
  document.title = title
  document.documentElement.lang = locale

  upsertMeta('meta[name="description"]', 'name', 'description', description)
  upsertMeta('meta[property="og:title"]', 'property', 'og:title', title)
  upsertMeta('meta[property="og:description"]', 'property', 'og:description', description)
  upsertMeta('meta[property="og:type"]', 'property', 'og:type', 'website')
  upsertMeta('meta[property="og:url"]', 'property', 'og:url', canonical)
  upsertMeta('meta[property="og:site_name"]', 'property', 'og:site_name', 'Radix CRM')
  upsertMeta(
    'meta[property="og:locale"]',
    'property',
    'og:locale',
    locale === 'uz' ? 'uz_UZ' : 'ru_RU',
  )
  upsertMeta('meta[property="og:image"]', 'property', 'og:image', `${ORIGIN}/og-${locale}.png`)
  upsertMeta('meta[property="og:image:width"]', 'property', 'og:image:width', '1200')
  upsertMeta('meta[property="og:image:height"]', 'property', 'og:image:height', '630')
  upsertMeta('meta[name="twitter:card"]', 'name', 'twitter:card', 'summary_large_image')
  upsertMeta('meta[name="twitter:title"]', 'name', 'twitter:title', title)
  upsertMeta('meta[name="twitter:description"]', 'name', 'twitter:description', description)
  upsertMeta('meta[name="twitter:image"]', 'name', 'twitter:image', `${ORIGIN}/og-${locale}.png`)

  upsertLink('canonical', canonical)
  // Ikki tilli sayt uchun `hreflang` — qidiruv tizimi bir xil sahifaning
  // ikki versiyasini nusxa deb hisoblamasligi uchun.
  upsertLink('alternate', `${ORIGIN}/uz${path}`, 'uz')
  upsertLink('alternate', `${ORIGIN}/ru${path}`, 'ru')
  upsertLink('alternate', `${ORIGIN}/uz${path}`, 'x-default')
}

export function LegalSeo({ locale, page }: { locale: Locale; page: 'privacy' | 'terms' }) {
  useEffect(() => {
    const t = legal[locale]
    const title = page === 'privacy' ? t.privacy : t.terms
    applyPageMeta({
      locale,
      title: `${title} — Radix CRM`,
      description: `${title} — Radix CRM.`,
      path: `/${page}`,
    })
    upsertJsonLd('faq', null)
  }, [locale, page])
  return null
}
