/**
 * Ikki yetkazib berish modeli — bulutli obuna va alohida o'rnatma
 * (docs/02 ADR-13, docs/01 §4.7).
 *
 * Ikkala karta ham TENG vizual og'irlikda: biri oq, biri quyuq. Bulutli
 * modelni "tavsiya etiladi" deb ajratib ko'rsatish oson yo'l bo'lardi,
 * lekin alohida o'rnatma — qimmatroq va bir martalik sotuv; uni ikkinchi
 * darajali qilib ko'rsatish o'sha suhbatni boshlanishidan oldin
 * yopib qo'yardi.
 */

import { ArrowRight, Check, Cloud, Server } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Reveal } from '../components/Motion'
import { copy, type DeliveryPlan, type Locale } from '../content'

const ICONS = { cloud: Cloud, onprem: Server } as const

export function DeliveryModels({ locale }: { locale: Locale }) {
  const t = copy[locale].delivery

  return (
    <section id="delivery" className="scroll-mt-24 bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <Reveal className="max-w-3xl">
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="section-title mt-4 text-balance">{t.title}</h2>
          <p className="mt-5 leading-7 text-slate-600">{t.text}</p>
        </Reveal>

        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          {t.plans.map((plan, index) => (
            <Reveal key={plan.id} delay={index * 0.1}>
              <PlanCard plan={plan} />
            </Reveal>
          ))}
        </div>

        <Reveal>
          <p className="mx-auto mt-10 max-w-2xl text-center text-sm leading-6 text-slate-500">
            {t.note}
          </p>
        </Reveal>
      </div>
    </section>
  )
}

function PlanCard({ plan }: { plan: DeliveryPlan }) {
  const Icon = ICONS[plan.id]
  const dark = plan.id === 'onprem'

  return (
    <article
      className={cn(
        'flex h-full flex-col rounded-3xl border p-7 transition duration-300 hover:-translate-y-1 sm:p-9',
        dark
          ? 'border-slate-800 bg-slate-950 text-white shadow-xl shadow-slate-900/20 hover:shadow-2xl'
          : 'border-slate-200 bg-white shadow-card hover:border-brand-200 hover:shadow-xl',
      )}
    >
      <div className="flex items-center justify-between gap-4">
        <span
          className={cn(
            'grid h-12 w-12 place-items-center rounded-2xl',
            dark ? 'bg-white/10 text-brand-300' : 'bg-brand-50 text-brand-700',
          )}
        >
          <Icon className="h-6 w-6" />
        </span>
        <span
          className={cn(
            'rounded-full px-3 py-1 text-[11px] font-bold',
            dark ? 'bg-white/10 text-slate-200' : 'bg-brand-50 text-brand-700',
          )}
        >
          {plan.badge}
        </span>
      </div>

      <h3 className={cn('mt-6 text-xl font-bold tracking-tight', dark && 'text-white')}>
        {plan.name}
      </h3>

      <div className="mt-4">
        <p
          className={cn(
            'text-3xl font-extrabold tracking-[-0.03em]',
            dark ? 'text-white' : 'text-slate-950',
          )}
        >
          {plan.price}
        </p>
        <p className={cn('mt-1 text-sm', dark ? 'text-slate-400' : 'text-slate-500')}>
          {plan.priceNote}
        </p>
      </div>

      <p className={cn('mt-5 leading-7', dark ? 'text-slate-300' : 'text-slate-600')}>
        {plan.text}
      </p>

      <ul className="mt-7 space-y-3.5">
        {plan.points.map((point) => (
          <li key={point} className="flex gap-3">
            <span
              className={cn(
                'mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full',
                dark ? 'bg-brand-500/20 text-brand-300' : 'bg-emerald-50 text-emerald-600',
              )}
            >
              <Check className="h-3 w-3" strokeWidth={3} />
            </span>
            <span className={cn('text-sm leading-6', dark ? 'text-slate-300' : 'text-slate-600')}>
              {point}
            </span>
          </li>
        ))}
      </ul>

      {/* `mt-auto` — ikkala kartadagi tugma bir xil chiziqda tursin,
          ro'yxatlar uzunligi har xil bo'lsa ham. */}
      <div className="mt-auto pt-8">
        <a
          href={plan.href}
          className={cn(
            'group inline-flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-semibold transition',
            dark
              ? 'bg-white text-slate-950 hover:bg-slate-100'
              : 'bg-slate-950 text-white hover:bg-slate-800',
          )}
        >
          {plan.cta}
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </a>
      </div>
    </article>
  )
}
