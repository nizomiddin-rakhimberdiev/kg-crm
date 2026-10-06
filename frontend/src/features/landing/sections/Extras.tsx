/**
 * Mahsulotning qolgan qismi — mock'siz, oddiy kartalar.
 *
 * Har bir imkoniyat uchun jonli panel chizish telefonda sahifani yana
 * bir necha ming piksel cho'zardi, foyda esa oz: bu narsalar sotuvda
 * "bormi?" degan savolga javob, "qanday ko'rinadi?" degan savolga emas.
 */

import { copy, type Locale } from '../content'
import { Reveal } from '../motion'

export function Extras({ locale }: { locale: Locale }) {
  const t = copy[locale].extras

  return (
    <section className="bg-slate-50 py-14 lg:py-24">
      <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
        <Reveal>
          <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
            {t.eyebrow}
          </p>
          <h2 className="mt-2 max-w-2xl text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900 sm:text-[2rem] lg:mt-3">
            {t.title}
          </h2>
        </Reveal>

        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:mt-12 lg:grid-cols-4 lg:gap-4">
          {t.items.map((item, i) => (
            <Reveal key={item.title} delay={(i % 4) * 0.04}>
              <article className="h-full rounded-2xl border border-slate-200 bg-white p-4 lg:p-5">
                <h3 className="text-[15px] font-bold tracking-tight text-slate-950 lg:text-base">
                  {item.title}
                </h3>
                <p className="mt-1.5 text-[14px] leading-6 text-slate-600">{item.text}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
