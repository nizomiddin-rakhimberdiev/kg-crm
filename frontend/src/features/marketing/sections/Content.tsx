/**
 * Matnga asoslangan bo'limlar: ishonch qatori, muammolar, modullar,
 * rollar, qadamlar, xavfsizlik va savollar.
 *
 * Bittada, chunki ular bir xil naqshda qurilgan — sarlavha, ochuvchi
 * animatsiya, kartalar to'ri. Alohida fayllarga bo'lish shu naqshni
 * yettita joyga nusxalardi.
 */

import {
  Boxes,
  Briefcase,
  CalendarCheck,
  ChevronDown,
  ClipboardList,
  Crown,
  FileBarChart,
  KeyRound,
  Landmark,
  ScrollText,
  ShieldCheck,
  UserCog,
  UsersRound,
  Wallet,
  WalletCards,
} from 'lucide-react'
import { Reveal } from '../components/Motion'
import { copy, type Locale } from '../content'

const featureIcons = [UsersRound, WalletCards, CalendarCheck, ClipboardList, Boxes, FileBarChart]
const roleIcons = [Crown, Briefcase, Wallet, UserCog]
const securityIcons = [KeyRound, Landmark, ScrollText]

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
              <span className="text-xs font-bold tabular-nums text-brand-600">
                {String(index + 1).padStart(2, '0')}
              </span>
              <p className="mt-3 leading-7 text-slate-600">{problem}</p>
            </div>
          </Reveal>
        ))}
      </div>

      {/* Muammo → yechim ko'prigi. Kartalar dekoratsiya emas, ular
          KEYINGI bo'limga olib boradi — o'quvchi "xo'sh, nima qilay?"
          degan savol bilan qolmaydi. */}
      <Reveal delay={0.1}>
        <p className="mt-10 text-center text-lg font-semibold tracking-tight text-slate-900 sm:text-xl">
          {t.bridge}
        </p>
      </Reveal>
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
          <h3 className="mt-16 text-xl font-bold tracking-tight text-slate-900">{t.featureTitle}</h3>
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

/**
 * Kimlar uchun — tizimdagi HAQIQIY rollar (apps/accounts/constants.py).
 *
 * "Administrator" degan rol yo'q; uning o'rnida `manager` (Menejer) bor
 * va u aynan shu ishni qiladi: bolalar, guruhlar, davomat, ombor —
 * moliyaga kirmasdan. Uydirma rol ertaga demoda "u qayerda?" degan
 * savolga aylanadi.
 */
export function Roles({ locale }: { locale: Locale }) {
  const t = copy[locale].roles
  return (
    <section className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <Reveal className="max-w-3xl">
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="section-title mt-4 text-balance">{t.title}</h2>
          <p className="mt-5 leading-7 text-slate-600">{t.text}</p>
        </Reveal>

        <div className="mt-12 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {t.items.map((item, index) => {
            const Icon = roleIcons[index]
            return (
              <Reveal key={item.role} delay={index * 0.07}>
                <article className="h-full rounded-2xl border border-slate-200 bg-slate-50/60 p-6 transition duration-300 hover:-translate-y-1 hover:border-brand-200 hover:bg-white hover:shadow-lg">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-white text-brand-700 shadow-card">
                    <Icon className="h-5 w-5" />
                  </span>
                  <h3 className="mt-5 font-bold text-slate-900">{item.role}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{item.text}</p>
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
    <section className="bg-slate-50 py-20 lg:py-28">
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
                  <p className="mt-5 font-bold text-slate-900">{step.title}</p>
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

/**
 * Xavfsizlik — kompakt, faqat REPODA TASDIQLANGAN narsalar:
 * RBAC (apps/accounts), tenant izolyatsiyasi + RLS (docs/03 §6.3),
 * insert-only audit (apps/audit). "Bank darajasi", "100% xavfsiz" kabi
 * tekshirib bo'lmaydigan va'dalar YO'Q.
 */
export function Security({ locale }: { locale: Locale }) {
  const t = copy[locale].security
  return (
    <section className="border-y border-slate-100 bg-white py-16 lg:py-20">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <Reveal>
          <div className="flex items-center gap-3">
            <ShieldCheck className="h-5 w-5 text-brand-600" aria-hidden="true" />
            <p className="eyebrow">{t.eyebrow}</p>
          </div>
          <h2 className="mt-3 text-2xl font-bold tracking-[-0.03em] text-slate-950 sm:text-3xl">
            {t.title}
          </h2>
        </Reveal>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {t.points.map((point, index) => {
            const Icon = securityIcons[index]
            return (
              <Reveal key={point.title} delay={index * 0.07}>
                <div className="flex h-full gap-4 rounded-2xl border border-slate-200 p-5">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-700">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div>
                    <h3 className="font-bold text-slate-900">{point.title}</h3>
                    <p className="mt-1.5 text-sm leading-6 text-slate-600">{point.text}</p>
                  </div>
                </div>
              </Reveal>
            )
          })}
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
                  va skrin-riderga tanish. */}
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
