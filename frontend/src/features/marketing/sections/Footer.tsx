/**
 * Footer — minimal, lekin to'liq: navigatsiya, til, huquqiy sahifalar,
 * CRM'ga kirish. Kontakt (telefon, manzil, email) ATAYLAB yo'q —
 * rasmiy aloqa kanali hali e'lon qilinmagan, uydirma raqam esa
 * ishonchni oshirmaydi, yo'qotadi.
 */

import { Link } from 'react-router-dom'
import { env } from '@/config/env'
import { Brand } from '../components/Brand'
import { copy, type Locale } from '../content'

export function Footer({ locale }: { locale: Locale }) {
  const t = copy[locale]
  const switchTo = locale === 'uz' ? 'ru' : 'uz'

  const nav = [
    ['#product', t.nav.product],
    ['#capabilities', t.nav.capabilities],
    ['#pricing', t.nav.pricing],
    ['#faq', t.nav.faq],
  ] as const

  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto grid max-w-7xl gap-8 px-5 py-10 sm:gap-10 sm:py-12 md:grid-cols-[1.4fr_1fr_1fr] lg:px-8">
        <div>
          <Brand />
          <p className="mt-4 max-w-sm text-sm leading-6 text-slate-500">{t.footer.product}</p>
        </div>

        <nav aria-label={t.nav.product} className="grid content-start gap-0.5 text-sm font-medium text-slate-600 sm:gap-2.5">
          {nav.map(([href, label]) => (
            <a key={href} className="inline-flex min-h-[44px] items-center transition hover:text-slate-950 sm:min-h-0" href={href}>
              {label}
            </a>
          ))}
        </nav>

        <div className="grid content-start gap-0.5 text-sm font-medium text-slate-600 sm:gap-2.5">
          <a className="inline-flex min-h-[44px] items-center transition hover:text-slate-950 sm:min-h-0" href={env.loginUrl}>
            {t.footer.login}
          </a>
          <Link className="inline-flex min-h-[44px] items-center transition hover:text-slate-950 sm:min-h-0" to={`/${switchTo}`}>
            {t.nav.switchLabel}
          </Link>
          <Link className="inline-flex min-h-[44px] items-center transition hover:text-slate-950 sm:min-h-0" to={`/${locale}/privacy`}>
            {t.footer.privacy}
          </Link>
          <Link className="inline-flex min-h-[44px] items-center transition hover:text-slate-950 sm:min-h-0" to={`/${locale}/terms`}>
            {t.footer.terms}
          </Link>
        </div>
      </div>
      <div className="mx-auto max-w-7xl border-t border-slate-100 px-5 py-5 text-xs text-slate-400 lg:px-8">
        {t.footer.copyright}
      </div>
    </footer>
  )
}
