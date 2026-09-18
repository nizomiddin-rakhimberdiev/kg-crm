/**
 * Bosh sahifa — radix-crm.uz (`/uz`, `/ru`).
 *
 * Scroll-hikoya: har bo'lim o'z faylida (`../sections/`), tartib shu yerda.
 * Onest shrifti faqat shu marshrutda yuklanadi — CRM ilovasi Inter'da
 * qoladi. Meta/OG/JSON-LD — `../seo.tsx`.
 */

import { useEffect } from 'react'
import { type Locale } from '../content'
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
import { LandingSeo } from '../seo'
import '../landing.css'

const FONT_HREF =
  'https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700;800&display=swap'

function useFont() {
  useEffect(() => {
    if (document.head.querySelector(`link[href="${FONT_HREF}"]`)) return
    const font = document.createElement('link')
    font.rel = 'stylesheet'
    font.href = FONT_HREF
    document.head.appendChild(font)
  }, [])
}

export function LandingPage({ locale }: { locale: Locale }) {
  useFont()
  return (
    <div className="marketing rx bg-white text-slate-900">
      <LandingSeo locale={locale} />
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
