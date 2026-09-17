/**
 * Public sayt — radix-crm.uz.
 *
 * Sahifa bo'limlarga bo'lingan (`../sections/`), chunki u mahsulot
 * o'sgani sayin o'sadi: bitta faylda u tez orada ochib bo'lmaydigan
 * darajaga yetardi. Bu fayl faqat TARTIBNI belgilaydi — nima qaysi
 * ketma-ketlikda ko'rinadi.
 *
 * Bo'limlar tartibi sotuv mantiqiga bo'ysunadi:
 *   va'da → tanish muammo → yechim → mahsulot → QANDAY SOTIB OLINADI
 *   → narx → ishonch → harakat.
 */

import { Navigate, Link } from 'react-router-dom'
import { env } from '@/config/env'
import { Brand } from '../components/Brand'
import { copy, type Locale } from '../content'
import { PublicSeo } from '../seo'
import { Capabilities, Faq, Problems, Proof, Roles, Security, Steps } from '../sections/Content'
import { DeliveryModels } from '../sections/DeliveryModels'
import { Footer } from '../sections/Footer'
import { Header } from '../sections/Header'
import { Hero } from '../sections/Hero'
import { LeadForm } from '../sections/LeadForm'
import { Pricing } from '../sections/Pricing'
import { ProductPreview } from '../sections/ProductPreview'

export function MarketingPage({ locale }: { locale: Locale }) {
  return (
    <div className="marketing bg-white text-slate-900">
      <PublicSeo locale={locale} />
      <Header locale={locale} />
      <main>
        <Hero locale={locale} />
        <Proof locale={locale} />
        <Problems locale={locale} />
        <Capabilities locale={locale} />
        <ProductPreview locale={locale} />
        <Roles locale={locale} />
        <DeliveryModels locale={locale} />
        <Steps locale={locale} />
        <Pricing locale={locale} />
        <Security locale={locale} />
        <Faq locale={locale} />
        <LeadForm locale={locale} />
      </main>
      <Footer locale={locale} />
    </div>
  )
}

/**
 * Ildiz manzili (`/`) kimga tegishli.
 *
 * Public domenda — sotuv sayti; boshqa har qanday hostda (masalan
 * mijozning o'z domenida yoki lokal ishlab chiqishda) — CRM'ning o'zi.
 */
export function MarketingEntry() {
  const host = window.location.hostname
  return host === env.publicHost || host === `www.${env.publicHost}` ? (
    <Navigate replace to="/uz" />
  ) : (
    <Navigate replace to="/dashboard" />
  )
}

export function LegalPage({ locale, page }: { locale: Locale; page: 'privacy' | 'terms' }) {
  const t = copy[locale]
  const sections = page === 'privacy' ? t.legal.privacySections : t.legal.termsSections
  const title = page === 'privacy' ? t.legal.privacy : t.legal.terms

  return (
    <div className="marketing min-h-screen bg-slate-50">
      <PublicSeo locale={locale} page={page} />
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-[72px] max-w-4xl items-center justify-between px-5">
          <Link to={`/${locale}`}>
            <Brand />
          </Link>
          <Link className="text-sm font-semibold text-brand-700" to={`/${locale}`}>
            {t.legal.back}
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-5 py-14">
        <p className="eyebrow">Radix CRM</p>
        <h1 className="mt-4 text-3xl font-bold tracking-[-0.035em] text-slate-950 sm:text-4xl">
          {title}
        </h1>
        <p className="mt-3 text-sm text-slate-500">{t.legal.updated}</p>

        <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 sm:p-9">
          <p className="text-sm text-slate-500">{env.legalEntityName || t.legal.operator}</p>
          <div className="mt-8 space-y-8">
            {sections.map((section) => (
              <section key={section.title}>
                <h2 className="text-lg font-bold text-slate-900">{section.title}</h2>
                <p className="mt-2 leading-7 text-slate-600">{section.text}</p>
              </section>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
