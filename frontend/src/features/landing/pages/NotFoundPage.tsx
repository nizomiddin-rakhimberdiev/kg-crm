/**
 * Notoʻgʻri manzil — `dist/404.html` (PLAN 5.6).
 *
 * Ilgari har qanday notoʻgʻri manzil SPA qobigʻini `200` bilan olardi
 * va React Router uni kirish sahifasiga burib yuborardi. Natijada
 * qidiruv tizimi `/wp-admin` ni "mavjud sahifa" deb indekslardi, va
 * havolada xato qilgan odam nima boʻlganini bilmasdi.
 *
 * Endi nginx haqiqiy `404` qaytaradi va shu sahifani beradi. U
 * **statik**: unda SPA skripti yoʻq (`prerender.mjs` uni olib
 * tashlaydi), chunki React ishga tushsa, notoʻgʻri manzilni yana
 * oʻzi "tuzatib", kirish sahifasiga yuborardi.
 *
 * **Bitta tilda** (audit 2026-11-12): uch tilda birga turgan sahifa
 * "qaysi biri meniki?" degan savol bilan ochilardi. Har til o'z
 * faylini oladi (`404-ru.html` …), nginx esa manzil prefiksidan
 * (`/ru/…`) yoki — prefiks bo'lmasa — brauzer tilidan tanlaydi
 * (`$kg_404_page`, `deploy/nginx/tls.conf`).
 */

import { Logo } from '@/components/brand/Logo'
import { copy, type Locale } from '../content'

export function NotFoundPage({ locale = 'uz' }: { locale?: Locale }) {
  const text = copy[locale].notFound
  return (
    <div
      lang={locale}
      className="marketing flex min-h-screen items-center justify-center bg-sut px-5 py-16"
    >
      <main className="w-full max-w-lg">
        <a href={`/${locale}`} aria-label="Radix CRM" className="inline-block">
          <Logo height={36} />
        </a>
        <p className="mt-10 text-sm font-semibold tabular-nums text-tosh-500">404</p>
        <h1 className="mt-4 text-2xl font-semibold text-tosh-900">{text.title}</h1>
        <p className="mt-2 text-base text-tosh-600">{text.text}</p>
        <a
          href={`/${locale}`}
          className="mt-2 inline-flex min-h-[44px] items-center text-sm font-semibold text-nihol-700 underline-offset-2 hover:underline"
        >
          {text.home} →
        </a>
      </main>
    </div>
  )
}
