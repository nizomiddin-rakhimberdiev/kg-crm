/**
 * Bosh sahifa SEO'si: title/description content.ts dan, FAQ JSON-LD
 * sahifada ko'rinib turgan savol-javoblardan. Sof qismlar (`landingMeta`,
 * `landingJsonLd`) prerender'da ham ishlatiladi — bot bilan brauzer bitta
 * narsani ko'radi.
 */

import { useEffect } from 'react'
import { applyPageMeta, upsertJsonLd } from '@/features/marketing/seo'
import { copy, type Locale } from './content'

export function landingMeta(locale: Locale) {
  const t = copy[locale]
  return { locale, title: t.seo.title, description: t.seo.description, path: '' }
}

export function landingJsonLd(locale: Locale) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: copy[locale].faq.items.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  }
}

export function LandingSeo({ locale }: { locale: Locale }) {
  useEffect(() => {
    applyPageMeta(landingMeta(locale))
    upsertJsonLd('faq', landingJsonLd(locale))
  }, [locale])
  return null
}
