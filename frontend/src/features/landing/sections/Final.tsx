/**
 * Yakun — sokin va premium. Bitta gap, bitta CTA, kichik mahsulot ko'rinishi.
 */

import { ArrowRight, ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { env } from '@/config/env'
import { Brand } from '@/features/marketing/components/Brand'
import { copy, type Locale } from '../content'
import { Reveal } from '../motion'
import { Bars, Frame, Kpi } from '../ui/Mock'
import { basePath } from '../paths'
import { ContactList, LegalLine } from '../ui/Contacts'

export function Final({ locale }: { locale: Locale }) {
  const t = copy[locale]
  return (
    <section className="relative overflow-hidden bg-slate-50 pt-16 lg:pt-32">
      <div className="mx-auto max-w-[1280px] px-5 text-center lg:px-8">
        <Reveal>
          <h2 className="mx-auto max-w-3xl text-balance text-[1.875rem] font-bold !leading-[1.12] tracking-[-0.02em] text-tosh-900 sm:text-[2.5rem] lg:text-5xl">
            {t.final.title}
          </h2>
          <p className="mt-4 text-[17px] text-slate-600 sm:mt-5 sm:text-lg lg:text-xl">
            {t.final.text}
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <a
              href={env.signupUrl}
              className="group inline-flex min-h-[54px] items-center justify-center gap-2 rounded-xl bg-brand-600 px-7 text-base font-semibold text-white transition hover:bg-brand-700"
            >
              {t.nav.trial}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </a>
            <a
              href="#demo"
              className="inline-flex min-h-[54px] items-center justify-center rounded-xl border border-slate-200 bg-white px-7 text-base font-semibold text-slate-800 transition hover:border-slate-300"
            >
              {t.final.cta}
            </a>
            <a
              href={env.loginUrl}
              className="inline-flex min-h-[54px] items-center justify-center gap-1.5 rounded-xl px-7 text-base font-semibold text-slate-600 transition hover:text-slate-900"
            >
              {t.final.secondary}
              <ArrowUpRight className="h-4 w-4 text-slate-400" />
            </a>
          </div>
        </Reveal>
        <Reveal
          delay={0.1}
          className="relative mx-auto mt-14 hidden max-w-4xl [perspective:1400px] sm:block"
        >
          <div className="[transform:rotateX(8deg)] origin-bottom">
            <Frame demo={t.demo}>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {t.demo.kpis.slice(0, 4).map((kpi, i) => (
                  <Kpi key={kpi.label} kpi={kpi} index={i} money={kpi.value > 999} />
                ))}
              </div>
              <div className="mt-3 rounded-xl border border-slate-200/80 p-3">
                <p className="text-[12px] font-semibold text-slate-800">{t.demo.chartTitle}</p>
                <Bars values={[61, 68, 72, 70, 79, 86]} labels={t.demo.months} className="mt-2" />
              </div>
            </Frame>
          </div>
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-slate-50 to-transparent"
          />
        </Reveal>
      </div>

      <footer className="relative border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1280px] flex-col gap-6 px-5 py-10 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div className="grid gap-5">
            <Link to={basePath(locale)} aria-label="Radix CRM">
              <Brand />
            </Link>
            {/* Aloqa bloki (PLAN 5.7) — yuridik qator faqat to'ldirilgan
                qismlardan, bo'sh bo'lsa yo'q. */}
            <ContactList locale={locale} />
            <LegalLine locale={locale} />
          </div>
          <nav
            className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600"
            aria-label="Footer"
          >
            <Link to={`/${locale}/privacy`} className="hover:text-slate-950">
              {t.footer.privacy}
            </Link>
            <Link to={`/${locale}/terms`} className="hover:text-slate-950">
              {t.footer.terms}
            </Link>
            <a href={env.loginUrl} className="hover:text-slate-950">
              {t.footer.login}
            </a>
          </nav>
          <p className="text-sm text-slate-400">{t.footer.copyright}</p>
        </div>
      </footer>
    </section>
  )
}
