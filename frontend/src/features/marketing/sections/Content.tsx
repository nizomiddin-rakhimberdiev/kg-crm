/**
 * Matnga asoslangan bo'limlar: ishonch qatori, muammolar, modullar,
 * qadamlar va savollar.
 *
 * Bittada, chunki ular bir xil naqshda qurilgan — sarlavha, ochuvchi
 * animatsiya, kartalar to'ri. Alohida fayllarga bo'lish shu naqshni
 * beshta joyga nusxalardi.
 */

import {
  Boxes,
  CalendarCheck,
  ChevronDown,
  ClipboardList,
  FileBarChart,
  UsersRound,
  WalletCards,
} from 'lucide-react'
import { Reveal } from '../components/Motion'
import { copy, type Locale } from '../content'

const featureIcons = [UsersRound, WalletCards, CalendarCheck, ClipboardList, Boxes, FileBarChart]

export function Proof({ locale }: { locale: Locale }) {
  return (
    <div className="border-y border-slate-100 bg-slate-50/70">
      <p className="mx-auto max-w-7xl px-5 py-5 text-center text-sm font-medium text-slate-600 lg:px-8">
        {copy[locale].proof}
      </p>
    </div>
  )
}

export function Problems({ locale }: { locale: Locale }) {
  const t = copy[locale].problems
  return (
    <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8 lg:py-28">
      <Reveal>
        <p className="eyebrow">{t.eyebrow}</p>
        <h2 className="section-title mt-4 max-w-3xl text-balance">{t.title}</h2>
      </Reveal>

      <div className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 md:grid-cols-2">
        {t.items.map((problem, index) => (
          <Reveal key={problem} delay={index * 0.06} className="bg-white">
            <div className="h-full p-7">
              {/* Raqamlash shu yerda MA'NOLI: bular ketma-ket bosqich emas,
                  lekin ro'yxat — o'quvchi nechtasini ko'rganini biladi. */}
              <span className="text-xs font-bold tabular-nums text-brand-600">
                {String(index + 1).padStart(2, '0')}
              </span>
              <p className="mt-3 leading-7 text-slate-600">{problem}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  )
}

export function Capabilities({ locale }: { locale: Locale }) {
  const t = copy[locale]
  return (
    <section id="capabilities" className="scroll-mt-24 bg-slate-50 py-20 lg:py-28">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <Reveal>
          <p className="eyebrow">{t.solution.eyebrow}</p>
          <div className="mt-4 grid gap-5 lg:grid-cols-2">
            <h2 className="section-title text-balance">{t.solution.title}</h2>
            <p className="max-w-xl self-end leading-7 text-slate-600">{t.solution.text}</p>
          </div>
        </Reveal>

        <Reveal>
          <h3 className="mt-16 text-xl font-bold tracking-tight text-slate-900">
            {t.featureTitle}
          </h3>
        </Reveal>

        <div className="mt-7 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {t.features.map((feature, index) => {
            const Icon = featureIcons[index]
            return (
              <Reveal key={feature.title} delay={(index % 3) * 0.07}>
                <article className="group h-full rounded-2xl border border-slate-200 bg-white p-7 shadow-card transition duration-300 hover:-translate-y-1 hover:border-brand-200 hover:shadow-lg">
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-700 transition group-hover:bg-brand-600 group-hover:text-white">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h4 className="mt-5 font-bold text-slate-900">{feature.title}</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{feature.text}</p>
                </article>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export function Steps({ locale }: { locale: Locale }) {
  const t = copy[locale].steps
  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <Reveal>
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="section-title mt-4 text-balance">{t.title}</h2>
        </Reveal>

        <div className="relative mt-12">
          {/* Bog'lovchi chiziq — bu HAQIQATAN ketma-ketlik, shuning uchun
              vizual bog'lanish ma'noni ifodalaydi, bezak emas. */}
          <div
            aria-hidden="true"
            className="absolute left-0 right-0 top-[27px] hidden h-px bg-gradient-to-r from-brand-200 via-brand-300 to-transparent xl:block"
          />
          <ol className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {t.items.map((step, index) => (
              <Reveal key={step.title} delay={index * 0.08}>
                <li className="relative">
                  <span className="relative z-10 grid h-14 w-14 place-items-center rounded-2xl border border-brand-100 bg-white text-lg font-bold tabular-nums text-brand-700 shadow-card">
                    {index + 1}
                  </span>
                  <p className="mt-5 font-bold text-slate-900">
                    {step.title.replace(/^\d+\s*—\s*/, '')}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{step.text}</p>
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}

export function Faq({ locale }: { locale: Locale }) {
  const t = copy[locale].faq
  return (
    <section id="faq" className="scroll-mt-24 bg-slate-50 py-20 lg:py-28">
      <div className="mx-auto max-w-4xl px-5 lg:px-8">
        <Reveal>
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="section-title mt-4 text-balance">{t.title}</h2>
        </Reveal>

        <div className="mt-10 space-y-3">
          {t.items.map((item, index) => (
            <Reveal key={item.title} delay={index * 0.04}>
              {/* `<details>` — JS'siz ishlaydi, klaviatura bilan ochiladi
                  va skrin-riderga tanish. Qo'lda yozilgan akkordeon shu
                  uchtasini ham qaytadan qurishni talab qilardi. */}
              <details className="group rounded-2xl border border-slate-200 bg-white px-6 transition hover:border-slate-300">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-5 py-5 font-bold text-slate-900">
                  {item.title}
                  <ChevronDown className="h-5 w-5 shrink-0 text-slate-400 transition-transform duration-300 group-open:rotate-180" />
                </summary>
                <p className="pb-5 leading-7 text-slate-600">{item.text}</p>
              </details>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
