/**
 * Savollar — scroll qilgan sari navbatdagisi ochiladi, oldingisi yopiladi.
 *
 * Pinned sahna: 7 savol = 7 qadam. Bosish ham ishlaydi (qo'lda tanlov
 * scroll keyingi qadamga o'tguncha turadi). Reduced-motion: oddiy
 * akkordeon, hammasi bosish bilan.
 */

import { useRef, useState } from 'react'
import { useMotionValueEvent, useTransform } from 'framer-motion'
import { Plus } from 'lucide-react'
import { copy, type Locale } from '../content'
import { Reveal, useScene, useStaticScene } from '../motion'

export function Faq({ locale }: { locale: Locale }) {
  const t = copy[locale].faq
  const ref = useRef<HTMLElement>(null)
  const progress = useScene(ref)
  const isStatic = useStaticScene()
  const steps = t.items.length
  const [step, setStep] = useState(0)
  const [manual, setManual] = useState<number | null>(null)

  const stepMv = useTransform(progress, (p) => Math.min(steps - 1, Math.floor(p * steps)))
  useMotionValueEvent(stepMv, 'change', (v) => {
    setStep(v)
    setManual(null)
  })
  const open = manual ?? step

  const heading = (
    <div>
      <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
        {t.eyebrow}
      </p>
      <h2 className="mt-2 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900 sm:text-[2rem] lg:mt-3">
        {t.title}
      </h2>
    </div>
  )

  const list = (
    <div className="divide-y divide-slate-200 rounded-[28px] border border-slate-200 bg-white px-4 sm:px-8">
      {t.items.map((item, i) => {
        const on = open === i
        return (
          <div key={item.q} className="py-0.5">
            <button
              type="button"
              aria-expanded={on}
              onClick={() => setManual(on ? -1 : i)}
              className="flex min-h-[52px] w-full items-center justify-between gap-4 py-3 text-left text-[15px] font-semibold text-slate-900 sm:text-[17px] lg:min-h-[56px]"
            >
              <span className="flex items-center gap-3">
                <span
                  className={`hidden text-[12px] tabular-nums sm:block ${on ? 'text-brand-700' : 'text-slate-500'}`}
                >
                  {/* `0{i + 1}` 10-savolda "010" berardi (audit 2026-11-12). */}
                  {String(i + 1).padStart(2, '0')}
                </span>
                {item.q}
              </span>
              <Plus
                className={`h-5 w-5 shrink-0 text-slate-500 transition-transform duration-300 ${on ? 'rotate-45' : ''}`}
              />
            </button>
            <div
              className="grid transition-[grid-template-rows] duration-300 ease-out"
              style={{ gridTemplateRows: on ? '1fr' : '0fr' }}
            >
              <p className="overflow-hidden pr-9 text-[14px] leading-6 text-slate-600 sm:pl-8 sm:text-[15px] sm:leading-7">
                <span
                  className={`block pb-4 transition-opacity duration-300 ${on ? 'opacity-100' : 'opacity-0'}`}
                >
                  {item.a}
                </span>
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )

  if (isStatic) {
    return (
      <section ref={ref} id="faq" className="scroll-mt-16 bg-slate-50 py-14 lg:py-32">
        <div className="mx-auto grid max-w-[1280px] gap-10 px-5 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:px-8">
          <Reveal>{heading}</Reveal>
          <Reveal delay={0.06}>{list}</Reveal>
        </div>
      </section>
    )
  }

  return (
    <section
      ref={ref}
      id="faq"
      className="relative bg-slate-50"
      style={{ height: `${steps * 45}vh` }}
    >
      <div className="sticky top-0 flex h-screen flex-col overflow-hidden pt-[76px]">
        <div className="mx-auto grid w-full max-w-[1280px] flex-1 content-center gap-5 px-5 py-6 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-10 lg:px-8">
          {heading}
          {list}
        </div>
      </div>
    </section>
  )
}
