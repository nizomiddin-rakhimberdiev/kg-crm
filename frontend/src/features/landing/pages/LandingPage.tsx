/**
 * Bosh sahifa — radix-crm.uz (`/uz`, `/ru`).
 *
 * Scroll-hikoya: har bo'lim o'z faylida (`../sections/`), tartib shu yerda.
 * Shriftlar (Onest, Golos Text, JetBrains Mono) `index.html` da — ular
 * endi ilovaning o'ziga ham kerak. Meta/OG/JSON-LD — `../seo.tsx`.
 */

import { type Locale } from '../content'
import { DeepDive } from '../sections/DeepDive'
import { Extras } from '../sections/Extras'
import { Faq } from '../sections/Faq'
import { Final } from '../sections/Final'
import { Finance } from '../sections/Finance'
import { Hero } from '../sections/Hero'
import { Intelligence } from '../sections/Intelligence'
import { Lead } from '../sections/Lead'
import { Modules } from '../sections/Modules'
import { Nav } from '../sections/Nav'
import { OneSystem } from '../sections/OneSystem'
import { Parents } from '../sections/Parents'
import { Pricing } from '../sections/Pricing'
import { Problem } from '../sections/Problem'
import { Roles } from '../sections/Roles'
import { Testimonials } from '../sections/Testimonials'
import { Workflow } from '../sections/Workflow'
import { LandingSeo } from '../seo'
import '../landing.css'

export function LandingPage({ locale }: { locale: Locale }) {
  return (
    // Sut — asosiy fon (brendbuk 04: har sahifada 60 %).
    <div className="marketing rx bg-sut text-tosh-900">
      <LandingSeo locale={locale} />
      <Nav locale={locale} />
      <main>
        <Hero locale={locale} />
        <Problem locale={locale} />
        <OneSystem locale={locale} />
        <Modules locale={locale} />
        <DeepDive locale={locale} />
        {/* Ota-onalar kanali — sotuvdagi birinchi savol (ADR-23). */}
        <Parents locale={locale} />
        <Roles locale={locale} />
        <Workflow locale={locale} />
        <Finance locale={locale} />
        <Intelligence locale={locale} />
        <Extras locale={locale} />
        <Pricing locale={locale} />
        {/* Ma'lumot qo'shilmaguncha hech narsa chizmaydi (PLAN 5.7). */}
        <Testimonials locale={locale} />
        <Faq locale={locale} />
        <Lead locale={locale} />
      </main>
      <Final locale={locale} />
    </div>
  )
}
