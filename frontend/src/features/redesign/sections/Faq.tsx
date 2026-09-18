/**
 * Savollar — toza akkordeon. `<details name>` — bir vaqtda bittasi ochiq,
 * JS'siz ham ishlaydi.
 */

import { Plus } from 'lucide-react'
import { copy, type Locale } from '../content'
import { Reveal } from '../motion'

export function Faq({ locale }: { locale: Locale }) {
  const t = copy[locale].faq
  return (
    <section id="faq" className="scroll-mt-16 bg-slate-50 py-20 lg:py-32">
      <div className="mx-auto grid max-w-[1280px] gap-10 px-5 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:px-8">
        <Reveal>
          <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
            {t.eyebrow}
          </p>
          <h2 className="mt-3 text-balance text-3xl font-extrabold !leading-[1.08] tracking-[-0.03em] text-slate-950 sm:text-4xl lg:text-[2.75rem]">
            {t.title}
          </h2>
        </Reveal>
        <Reveal delay={0.06}>
          <div className="divide-y divide-slate-200 rounded-[28px] border border-slate-200 bg-white px-5 sm:px-8">
            {t.items.map((item) => (
              <details key={item.q} name="rx-faq" className="group py-1">
                <summary className="flex min-h-[56px] cursor-pointer list-none items-center justify-between gap-4 py-4 text-left text-[17px] font-semibold text-slate-900 [&::-webkit-details-marker]:hidden">
                  {item.q}
                  <Plus className="h-5 w-5 shrink-0 text-slate-400 transition-transform duration-300 group-open:rotate-45" />
                </summary>
                <p className="pb-5 pr-9 text-[15px] leading-7 text-slate-600">{item.a}</p>
              </details>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
