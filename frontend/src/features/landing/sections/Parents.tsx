/**
 * Ota-onalar kanali — Telegram bot va onlayn toʻlov (ADR-23, ADR-26, ADR-27).
 *
 * Bu bo'lim saytda umuman yo'q edi, holbuki sotuvdagi birinchi savol
 * aynan shu: "ota-onalar bilan qanday ishlaydi?". Chapda — javob matni,
 * o'ngda — telefon ekranidagi suhbat: balans so'raldi, hisob keldi,
 * to'lov tugmasi bosildi, kvitansiya qaytdi.
 *
 * Suhbat BIR MARTA, yuklanganda chiziladi (CSS kechikishlari) — scroll
 * bilan bog'lanmagan: telefonda u sahifani cho'zmasligi kerak.
 */

import { Check, CreditCard, Send } from 'lucide-react'
import { copy, type Copy, type Locale } from '../content'
import { Reveal } from '../motion'

export function Parents({ locale }: { locale: Locale }) {
  const t = copy[locale].parents
  const ui = copy[locale].ui.parents

  return (
    <section id="parents" className="scroll-mt-16 bg-white py-14 lg:py-28">
      <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,6fr)_minmax(0,5fr)] lg:items-center lg:gap-16">
          <div>
            <Reveal>
              <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
                {t.eyebrow}
              </p>
              <h2 className="mt-2 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900 sm:text-[2rem] lg:mt-3">
                {t.title}
              </h2>
              <p className="mt-3 text-base leading-7 text-slate-600 lg:text-lg">{t.text}</p>
            </Reveal>

            <div className="mt-7 grid gap-3 sm:grid-cols-2">
              {t.items.map((item, i) => (
                <Reveal key={item.title} delay={(i % 2) * 0.05}>
                  <article className="h-full rounded-2xl border border-slate-200 bg-white p-4 lg:p-5">
                    <h3 className="text-[15px] font-bold tracking-tight text-slate-950 lg:text-base">
                      {item.title}
                    </h3>
                    <p className="mt-1.5 text-[14px] leading-6 text-slate-600 lg:text-[15px]">
                      {item.text}
                    </p>
                  </article>
                </Reveal>
              ))}
            </div>

            <Reveal delay={0.1}>
              <p className="mt-5 text-[13px] leading-5 text-slate-500">{t.note}</p>
            </Reveal>
          </div>

          <Reveal delay={0.08}>
            <Chat ui={ui} />
          </Reveal>
        </div>
      </div>
    </section>
  )
}

/**
 * Telegram suhbati — HTML bilan chizilgan, skrinshot emas.
 *
 * Shuning uchun u matn sifatida qidiruvga ham, prerender'ga ham tushadi
 * va uch tilda bir xil ishlaydi; rasm bo'lsa, har til uchun alohida
 * fayl kerak bo'lardi va ularning biri doimo eskirib qolardi.
 */
function Chat({ ui }: { ui: Copy['ui']['parents'] }) {
  return (
    <div className="mx-auto w-full max-w-[380px] rounded-[26px] border border-slate-200 bg-ildiz-900/[0.03] p-3 shadow-[0_30px_80px_-40px_rgba(18,53,47,0.35)]">
      <div className="flex items-center gap-2 px-1 pb-3">
        <span className="grid h-8 w-8 place-items-center rounded-full bg-brand-600 text-white">
          <Send className="h-4 w-4" />
        </span>
        <p className="text-[13px] font-semibold text-slate-800">{ui.bot}</p>
      </div>

      <div className="space-y-2">
        {/* Ota-ona tugmani bosdi. */}
        <div className="rx-fade flex justify-end">
          <span className="rounded-2xl rounded-br-md bg-brand-600 px-3.5 py-2 text-[13px] font-medium text-white">
            {ui.askBalance}
          </span>
        </div>

        {/* Bot javobi: bola, oy, summa. */}
        <div className="rx-fade [animation-delay:160ms] rounded-2xl rounded-bl-md bg-white p-3 shadow-[0_10px_30px_-18px_rgba(18,53,47,0.4)]">
          <p className="text-[13px] font-semibold text-slate-900">{ui.answer}</p>
          <p className="mt-1 text-[13px] text-slate-600">{ui.due}</p>
          <div className="mt-2.5 inline-flex items-center gap-1.5 rounded-lg bg-slate-950 px-3 py-2 text-[12px] font-semibold text-white">
            <CreditCard className="h-3.5 w-3.5" />
            {ui.payNow}
          </div>
        </div>

        {/* To'landi — kvitansiya. */}
        <div className="rx-fade [animation-delay:320ms] flex items-center gap-2 rounded-2xl rounded-bl-md bg-white px-3 py-2.5 shadow-[0_10px_30px_-18px_rgba(18,53,47,0.4)]">
          <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-nihol-50 text-nihol-700">
            <Check className="h-3.5 w-3.5" strokeWidth={3} />
          </span>
          <p className="text-[13px] font-medium text-slate-700">{ui.paid}</p>
        </div>
      </div>

      {/* Bot menyusi — to'rtta tugma. */}
      <div className="mt-3 grid grid-cols-2 gap-1.5">
        {[ui.balance, ui.invoices, ui.pay, ui.receipts].map((label) => (
          <span
            key={label}
            className="truncate rounded-lg bg-white px-2.5 py-2 text-center text-[12px] font-semibold text-slate-600 ring-1 ring-slate-200"
          >
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
