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

export interface PageMeta {
  locale: Locale
  title: string
  description: string
  canonical: string
  /** [hreflang, href] — uz, ru va x-default. */
  alternates: [string, string][]
  ogImage: string
  ogLocale: string
}

/**
 * Sahifa meta'sining SOF ta'rifi — DOM'siz. Ikki iste'molchi bor: brauzerda
 * `applyPageMeta` (teglarni <head> ga yozadi) va build vaqtidagi prerender
 * (`headHtml` — o'sha teglar matn sifatida, bot JS'siz ham ko'rsin).
 * Ikkalasi bitta manbadan — aks holda bot bilan brauzer boshqa-boshqa
 * sarlavha ko'rardi.
 */
export function buildPageMeta({
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
}): PageMeta {
  return {
    locale,
    title,
    description,
    canonical: `${ORIGIN}/${locale}${path}`,
    alternates: [
      ['uz', `${ORIGIN}/uz${path}`],
      ['ru', `${ORIGIN}/ru${path}`],
      ['x-default', `${ORIGIN}/uz${path}`],
    ],
    ogImage: `${ORIGIN}/og-${locale}.png`,
    ogLocale: locale === 'uz' ? 'uz_UZ' : 'ru_RU',
  }
}

const escapeAttr = (value: string) =>
  value.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** Prerender uchun: <head> ichiga qo'yiladigan teglar (title, meta, link, JSON-LD). */
export function headHtml(meta: PageMeta, jsonLd: object | null = null): string {
  const m = (attr: 'name' | 'property', key: string, value: string) =>
    `<meta ${attr}="${key}" content="${escapeAttr(value)}" />`
  const lines = [
    `<title>${escapeAttr(meta.title)}</title>`,
    m('name', 'description', meta.description),
    m('name', 'robots', 'index,follow'),
    m('property', 'og:type', 'website'),
    m('property', 'og:site_name', 'Radix CRM'),
    m('property', 'og:title', meta.title),
    m('property', 'og:description', meta.description),
    m('property', 'og:url', meta.canonical),
    m('property', 'og:locale', meta.ogLocale),
    m('property', 'og:image', meta.ogImage),
    m('property', 'og:image:width', '1200'),
    m('property', 'og:image:height', '630'),
    m('name', 'twitter:card', 'summary_large_image'),
    m('name', 'twitter:title', meta.title),
    m('name', 'twitter:description', meta.description),
    m('name', 'twitter:image', meta.ogImage),
    `<link rel="canonical" href="${escapeAttr(meta.canonical)}" />`,
    ...meta.alternates.map(
      ([lang, href]) => `<link rel="alternate" hreflang="${lang}" href="${escapeAttr(href)}" />`,
    ),
  ]
  if (jsonLd) {
    // `</script>` ichkarida uchrasa HTML'ni buzadi — `<` ni qochiramiz.
    lines.push(
      `<script type="application/ld+json" data-jsonld="faq">${JSON.stringify(jsonLd).replace(/</g, '\\u003c')}</script>`,
    )
  }
  return lines.join('\n    ')
}

/** Brauzerda: meta'ni <head> ga yozadi (SPA navigatsiyasida ham). */
export function applyPageMeta(input: {
  locale: Locale
  title: string
  description: string
  path: string
}) {
  const meta = buildPageMeta(input)
  document.title = meta.title
  document.documentElement.lang = meta.locale

  upsertMeta('meta[name="description"]', 'name', 'description', meta.description)
  upsertMeta('meta[property="og:title"]', 'property', 'og:title', meta.title)
  upsertMeta('meta[property="og:description"]', 'property', 'og:description', meta.description)
  upsertMeta('meta[property="og:type"]', 'property', 'og:type', 'website')
  upsertMeta('meta[property="og:url"]', 'property', 'og:url', meta.canonical)
  upsertMeta('meta[property="og:site_name"]', 'property', 'og:site_name', 'Radix CRM')
  upsertMeta('meta[property="og:locale"]', 'property', 'og:locale', meta.ogLocale)
  upsertMeta('meta[property="og:image"]', 'property', 'og:image', meta.ogImage)
  upsertMeta('meta[property="og:image:width"]', 'property', 'og:image:width', '1200')
  upsertMeta('meta[property="og:image:height"]', 'property', 'og:image:height', '630')
  upsertMeta('meta[name="twitter:card"]', 'name', 'twitter:card', 'summary_large_image')
  upsertMeta('meta[name="twitter:title"]', 'name', 'twitter:title', meta.title)
  upsertMeta('meta[name="twitter:description"]', 'name', 'twitter:description', meta.description)
  upsertMeta('meta[name="twitter:image"]', 'name', 'twitter:image', meta.ogImage)

  upsertLink('canonical', meta.canonical)
  // Ikki tilli sayt uchun `hreflang` — qidiruv tizimi bir xil sahifaning
  // ikki versiyasini nusxa deb hisoblamasligi uchun.
  for (const [lang, href] of meta.alternates) upsertLink('alternate', href, lang)
}

export function legalMeta(locale: Locale, page: 'privacy' | 'terms') {
  const t = legal[locale]
  const title = page === 'privacy' ? t.privacy : t.terms
  return {
    locale,
    title: `${title} — Radix CRM`,
    description: `${title} — Radix CRM.`,
    path: `/${page}`,
  }
}

export function LegalSeo({ locale, page }: { locale: Locale; page: 'privacy' | 'terms' }) {
  useEffect(() => {
    applyPageMeta(legalMeta(locale, page))
    upsertJsonLd('faq', null)
  }, [locale, page])
  return null
}
