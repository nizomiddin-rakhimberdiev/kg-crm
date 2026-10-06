/**
 * Mijozlar fikri (PLAN 5.7) — JOY tayyor, maʼlumot qoʻshilmaguncha
 * YASHIRIN.
 *
 * `content.ts` dagi `testimonials.items` boʻsh ekan, komponent hech
 * narsa chizmaydi. Uydirma iqtibos qoʻyilmaydi: bitta soxta "fikr"
 * butun saytga ishonchni yoʻqotadi. Haqiqiy fikr (ruxsat bilan)
 * kelganda uni uch tilda `items` ga qoʻshish kifoya.
 */

import { copy, type Locale } from '../content'
import { Reveal } from '../motion'

export function Testimonials({ locale }: { locale: Locale }) {
  const t = copy[locale].testimonials
  if (t.items.length === 0) return null

  return (
    <section id="testimonials" className="bg-white py-14 lg:py-24">
      <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
        <Reveal>
          <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
            {t.eyebrow}
          </p>
          <h2 className="mt-2 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900 sm:text-[2rem]">
            {t.title}
          </h2>
        </Reveal>
        <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {t.items.map((item) => (
            <figure
              key={item.name}
              className="flex h-full flex-col rounded-2xl border border-slate-200 bg-sut p-6"
            >
              <blockquote className="flex-1 text-[15px] leading-7 text-slate-700">
                “{item.quote}”
              </blockquote>
              <figcaption className="mt-5">
                <p className="text-[15px] font-semibold text-slate-900">{item.name}</p>
                <p className="text-[13px] text-slate-500">{item.role}</p>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  )
}
