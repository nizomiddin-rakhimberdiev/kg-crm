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
 * **Uch tilda birga**: manzil notoʻgʻri boʻlsa, uning tili ham
 * nomaʼlum. Oʻzbekcha birinchi — sukut til (ADR-16).
 */

import { Logo } from '@/components/brand/Logo'
import { copy, type Locale } from '../content'

const ORDER: Locale[] = ['uz', 'ru', 'en']

export function NotFoundPage() {
  return (
    <div className="marketing flex min-h-screen items-center justify-center bg-sut px-5 py-16">
      <main className="w-full max-w-lg">
        <a href="/uz" aria-label="Radix CRM" className="inline-block">
          <Logo height={36} />
        </a>
        <p className="mt-10 text-sm font-semibold tabular-nums text-tosh-500">404</p>

        {/*
          Sarlavha BITTA `h1` — uch tilda uchta `h1` boʻlsa, sahifa
          tuzilishi ekran oʻquvchi uchun uch marta boshlanardi.
          Qolgan ikkitasi — `h2`.
        */}
        <div className="mt-4 space-y-8">
          {ORDER.map((locale, i) => {
            const text = copy[locale].notFound
            const Heading = i === 0 ? 'h1' : 'h2'
            return (
              <section key={locale} lang={locale}>
                <Heading className="text-2xl font-semibold text-tosh-900">{text.title}</Heading>
                <p className="mt-2 text-base text-tosh-600">{text.text}</p>
                <a
                  href={`/${locale}`}
                  className="mt-2 inline-flex min-h-[44px] items-center text-sm font-semibold text-nihol-700 underline-offset-2 hover:underline"
                >
                  {text.home} →
                </a>
              </section>
            )
          })}
        </div>
      </main>
    </div>
  )
}
