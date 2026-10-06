/**
 * Radix Intelligence V1 (ADR-14) — qoidaga asoslangan xulosa, dalili bilan.
 *
 * Bu yerda "sun'iy intellekt" so'zi ataylab ehtiyot ishlatiladi:
 * mahsulotda LLM yo'q, xulosa qoidadan chiqadi va har bir xulosa o'z
 * dalilini olib yuradi. Sahifada ham shu ko'rsatiladi — chiroyli
 * va'da emas, kartaning o'zi: nima topildi, nega, va qayerga olib boradi.
 */

import { ArrowRight, Check, Sparkles } from 'lucide-react'
import { copy, type Locale } from '../content'
import { Reveal } from '../motion'

export function Intelligence({ locale }: { locale: Locale }) {
  const t = copy[locale].intelligence
  const ui = copy[locale].ui.intelligence

  return (
    <section data-nav-dark className="bg-ildiz-900 py-16 text-white lg:py-28">
      <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:items-center lg:gap-16">
          <div>
            <Reveal>
              <p className="inline-flex items-center gap-1.5 text-[13px] font-bold uppercase tracking-[0.16em] text-brand-400">
                <Sparkles className="h-3.5 w-3.5" />
                {t.eyebrow}
              </p>
              <h2 className="mt-2 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-white sm:text-[2rem] lg:mt-3">
                {t.title}
              </h2>
              <p className="mt-3 text-base leading-7 text-slate-300 lg:text-lg">{t.text}</p>
            </Reveal>
            <ul className="mt-6 grid gap-2.5">
              {t.points.map((point, i) => (
                <Reveal key={point} delay={i * 0.05}>
                  <li className="flex items-start gap-2.5 text-[15px] leading-6 text-slate-200">
                    <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-500/20 text-brand-300">
                      <Check className="h-3 w-3" strokeWidth={3} />
                    </span>
                    {point}
                  </li>
                </Reveal>
              ))}
            </ul>
          </div>

          <Reveal delay={0.08}>
            {/* Xulosa kartasi — mahsulotdagi "Kunlik xulosa" ko'rinishi. */}
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5 lg:p-6">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-orik-100 px-2.5 py-0.5 text-[12px] font-bold text-orik-800">
                  {ui.severity}
                </span>
                <p className="text-[15px] font-bold tracking-tight text-white">{ui.kind}</p>
              </div>
              <p className="mt-4 text-[13px] font-semibold uppercase tracking-wider text-slate-400">
                {ui.why}
              </p>
              <ul className="mt-2 grid gap-2">
                {ui.evidence.map((line) => (
                  <li
                    key={line}
                    className="rounded-xl bg-white/[0.04] px-3 py-2.5 text-[14px] leading-5 text-slate-200"
                  >
                    {line}
                  </li>
                ))}
              </ul>
              <p className="mt-4 inline-flex items-center gap-1.5 text-[14px] font-semibold text-brand-300">
                {ui.action}
                <ArrowRight className="h-4 w-4" />
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
