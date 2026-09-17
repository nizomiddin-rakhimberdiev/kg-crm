/**
 * Public sahifalarning meta ma'lumotlari.
 *
 * SPA'da `<title>` va meta teglar qo'lda yangilanadi: `index.html` dagi
 * qiymat barcha marshrutlar uchun bitta bo'lib qolardi, va ulashilgan
 * havola qaysi sahifa bo'lishidan qat'i nazar bir xil ko'rinardi.
 */

import { useEffect } from 'react'
import { copy, type Locale } from './content'

type Page = 'home' | 'privacy' | 'terms'

function upsertMeta(
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

function upsertLink(rel: string, href: string, hreflang?: string) {
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

export function PublicSeo({ locale, page = 'home' }: { locale: Locale; page?: Page }) {
  const t = copy[locale]

  useEffect(() => {
    const suffix =
      page === 'privacy' ? t.legal.privacy : page === 'terms' ? t.legal.terms : t.hero.title
    const title = `Radix CRM — ${suffix}`
    const description = page === 'home' ? t.hero.text : `${suffix} — Radix CRM.`
    const path = page === 'home' ? '' : `/${page}`

    document.title = title
    document.documentElement.lang = locale

    upsertMeta('meta[name="description"]', 'name', 'description', description)
    upsertMeta('meta[property="og:title"]', 'property', 'og:title', title)
    upsertMeta('meta[property="og:description"]', 'property', 'og:description', description)
    upsertMeta('meta[property="og:type"]', 'property', 'og:type', 'website')
    upsertMeta('meta[property="og:locale"]', 'property', 'og:locale', locale === 'uz' ? 'uz_UZ' : 'ru_RU')
    upsertMeta('meta[name="twitter:card"]', 'name', 'twitter:card', 'summary_large_image')

    upsertLink('canonical', `https://radix-crm.uz/${locale}${path}`)
    // Ikki tilli sayt uchun `hreflang` — qidiruv tizimi bir xil sahifaning
    // ikki versiyasini nusxa deb hisoblamasligi uchun.
    upsertLink('alternate', `https://radix-crm.uz/uz${path}`, 'uz')
    upsertLink('alternate', `https://radix-crm.uz/ru${path}`, 'ru')
    upsertLink('alternate', `https://radix-crm.uz/uz${path}`, 'x-default')
  }, [locale, page, t])

  return null
}
