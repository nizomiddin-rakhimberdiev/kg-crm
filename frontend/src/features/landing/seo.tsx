/**
 * Bosh sahifa SEO'si (docs: title/description content.ts dan, FAQ JSON-LD
 * sahifada ko'rinib turgan savol-javoblardan). Yordamchilar —
 * `features/marketing/seo.tsx`.
 */

import { useEffect } from 'react'
import { applyPageMeta, upsertJsonLd } from '@/features/marketing/seo'
import { copy, type Locale } from './content'

export function LandingSeo({ locale }: { locale: Locale }) {
  const t = copy[locale]
  useEffect(() => {
    applyPageMeta({ locale, title: t.seo.title, description: t.seo.description, path: '' })
    upsertJsonLd('faq', {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: t.faq.items.map((item) => ({
        '@type': 'Question',
        name: item.q,
        acceptedAnswer: { '@type': 'Answer', text: item.a },
      })),
    })
  }, [locale, t])
  return null
}
