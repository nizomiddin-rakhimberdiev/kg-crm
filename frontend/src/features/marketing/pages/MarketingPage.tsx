/**
 * Public sayt kirish nuqtalari.
 *
 * Bosh sahifa — `features/landing` (scroll-hikoya). Bu faylda faqat
 * ildiz yo'naltiruvchisi va huquqiy sahifalar qoldi.
 */

import { Link, Navigate } from 'react-router-dom'
import { env } from '@/config/env'
import { Brand } from '../components/Brand'
import { fillLegal, legal, type Locale } from '../legal'
import { LegalSeo } from '../seo'

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
  const t = legal[locale]
  const sections = page === 'privacy' ? t.privacySections : t.termsSections
  const title = page === 'privacy' ? t.privacy : t.terms

  return (
    <div className="marketing min-h-screen bg-slate-50">
      <LegalSeo locale={locale} page={page} />
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-[72px] max-w-4xl items-center justify-between px-5">
          {/* Logotip havolasining nomi bo'lishi SHART: ekran o'quvchi
              uchun u "havola" bo'lib qolardi. */}
          <Link to={`/${locale}`} aria-label="Radix CRM">
            <Brand />
          </Link>
          <Link
            className="inline-flex min-h-[44px] items-center text-sm font-semibold text-brand-700"
            to={`/${locale}`}
          >
            {t.back}
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-5 py-14">
        <p className="eyebrow">Radix CRM</p>
        <h1 className="mt-4 text-3xl font-bold tracking-[-0.035em] text-slate-950 sm:text-4xl">
          {title}
        </h1>
        <p className="mt-3 text-sm text-slate-500">{t.updated}</p>

        <div className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 sm:p-9">
          <p className="text-sm text-slate-500">{env.legalEntityName || t.operator}</p>
          <div className="mt-8 space-y-8">
            {sections.map((section) => (
              <section key={section.title}>
                <h2 className="text-lg font-bold text-slate-900">{section.title}</h2>
                {/* Xatboshilar `\n` bilan; `{{…}}` belgilari `.env` dan
                    toʻldiriladi (PLAN 5.8, `legal.ts` izohi). */}
                {fillLegal(section.text)
                  .split('\n')
                  .map((paragraph) => (
                    <p key={paragraph} className="mt-2 leading-7 text-slate-600">
                      {paragraph}
                    </p>
                  ))}
              </section>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
