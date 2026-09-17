import { Link } from 'react-router-dom'
import { env } from '@/config/env'
import { Brand } from '../components/Brand'
import { copy, type Locale } from '../content'

export function Footer({ locale }: { locale: Locale }) {
  const t = copy[locale].footer

  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-8 px-5 py-12 sm:flex-row sm:items-end sm:justify-between lg:px-8">
        <div>
          <Brand />
          <p className="mt-4 max-w-sm text-sm leading-6 text-slate-500">{t.product}</p>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-3 text-sm font-medium text-slate-600">
          <Link className="transition hover:text-slate-950" to={`/${locale}/privacy`}>
            {t.privacy}
          </Link>
          <Link className="transition hover:text-slate-950" to={`/${locale}/terms`}>
            {t.terms}
          </Link>
          <a className="transition hover:text-slate-950" href={env.appUrl}>
            {t.login}
          </a>
        </div>
      </div>
      <div className="mx-auto max-w-7xl border-t border-slate-100 px-5 py-5 text-xs text-slate-400 lg:px-8">
        {t.copyright}
      </div>
    </footer>
  )
}
