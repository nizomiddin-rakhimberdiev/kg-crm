/**
 * Sinov sahifasi — `/test-redesign` (UZ) va `/test-redesign/ru`.
 *
 * Asosiy landing'ga TEGMAYDI: alohida feature, alohida CSS, alohida
 * marshrut. Qidiruv tizimlariga `noindex` — bu sahifa ikki nusxa (duplicate)
 * kontent bo'lib qolmasin. Onest shrifti faqat shu marshrutda yuklanadi.
 */

import { useEffect } from 'react'
import { copy, type Locale } from '../content'
import { DeepDive } from '../sections/DeepDive'
import { Faq } from '../sections/Faq'
import { Final } from '../sections/Final'
import { Finance } from '../sections/Finance'
import { Hero } from '../sections/Hero'
import { Lead } from '../sections/Lead'
import { Modules } from '../sections/Modules'
import { Nav } from '../sections/Nav'
import { OneSystem } from '../sections/OneSystem'
import { Pricing } from '../sections/Pricing'
import { Problem } from '../sections/Problem'
import { Roles } from '../sections/Roles'
import { Workflow } from '../sections/Workflow'
import '../redesign.css'

const FONT_HREF =
  'https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700;800&display=swap'

function useHead(locale: Locale) {
  const t = copy[locale].seo
  useEffect(() => {
    document.title = `${t.title} · test`
    document.documentElement.lang = locale

    const robots = document.createElement('meta')
    robots.name = 'robots'
    robots.content = 'noindex, nofollow'
    document.head.appendChild(robots)

    let font = document.head.querySelector<HTMLLinkElement>(`link[href="${FONT_HREF}"]`)
    if (!font) {
      font = document.createElement('link')
      font.rel = 'stylesheet'
      font.href = FONT_HREF
      document.head.appendChild(font)
    }
    return () => {
      robots.remove()
    }
  }, [locale, t.title])
}

export function RedesignPage({ locale }: { locale: Locale }) {
  useHead(locale)
  return (
    <div className="marketing rx bg-white text-slate-900">
      <Nav locale={locale} />
      <main>
        <Hero locale={locale} />
        <Problem locale={locale} />
        <OneSystem locale={locale} />
        <Modules locale={locale} />
        <DeepDive locale={locale} />
        <Roles locale={locale} />
        <Workflow locale={locale} />
        <Finance locale={locale} />
        <Pricing locale={locale} />
        <Faq locale={locale} />
        <Lead locale={locale} />
      </main>
      <Final locale={locale} />
    </div>
  )
}
