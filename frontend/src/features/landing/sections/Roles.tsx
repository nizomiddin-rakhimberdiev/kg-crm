/**
 * "Radix kimlar uchun?" — pinned: scroll rolni almashtiradi.
 *
 * To'rt qadam (ega → direktor → kassir → administrator). Hover/tap rolni
 * VAQTINCHA tanlaydi — scroll keyingi qadamga o'tganda yana scroll'niki.
 * Mobil: rollar gorizontal chip qatori, panel ostida, matn panel tagida.
 */

import { useRef, useState } from 'react'
import { useMotionValueEvent, useTransform } from 'framer-motion'
import { copy, type Locale, type RoleCopy } from '../content'
import { centerInStrip, Reveal, useCompact, useScene, useStatic } from '../motion'
import { Bars, Frame, Kpi, Pill, Row } from '../ui/Mock'

const STEPS = 4
const SIDEBAR: Record<RoleCopy['id'], number> = { owner: 0, director: 5, cashier: 3, admin: 1 }

function RoleView({ role, locale }: { role: RoleCopy['id']; locale: Locale }) {
  const t = copy[locale].demo
  const ui = copy[locale].ui.roles
  if (role === 'owner') {
    return (
      <>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[t.kpis[3], t.kpis[2], t.kpis[0], t.kpis[4]].map((kpi, i) => (
            <Kpi key={kpi.label} kpi={kpi} index={[3, 2, 0, 4][i]} money={kpi.value > 999} />
          ))}
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200/80 p-3">
            <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">{ui.branches}</p>
            <Row
              name={ui.chilonzor}
              meta="68 · 94 %"
              right={<Pill tone="ok">46 800 000</Pill>}
              avatar={false}
            />
            <Row
              name={ui.yunusobod}
              meta="60 · 93 %"
              right={<Pill tone="ok">39 600 000</Pill>}
              avatar={false}
            />
          </div>
          <div className="hidden rounded-xl border border-slate-200/80 p-3 sm:block">
            <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">
              {t.chartTitle}
            </p>
            <Bars values={[61, 68, 72, 70, 79, 86]} labels={t.months} className="mt-2" />
          </div>
        </div>
      </>
    )
  }
  if (role === 'director') {
    return (
      <>
        <div className="grid grid-cols-3 gap-2">
          {[t.kpis[1], t.kpis[0], t.kpis[4]].map((kpi, i) => (
            <Kpi key={kpi.label} kpi={kpi} index={[1, 0, 4][i]} />
          ))}
        </div>
        <div className="mt-3 rounded-xl border border-slate-200/80 p-3">
          <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">{ui.tasks}</p>
          <Row name={ui.attendanceMissing} right={<Pill tone="wait">08:40</Pill>} avatar={false} />
          <Row
            name={ui.newChildren}
            right={<Pill tone="neutral">{ui.today}</Pill>}
            avatar={false}
          />
          <Row name={ui.cookAdvance} right={<Pill tone="neutral">400 000</Pill>} avatar={false} />
        </div>
      </>
    )
  }
  if (role === 'cashier') {
    return (
      <>
        <div className="grid grid-cols-3 gap-2">
          {[
            [ui.acceptedToday, '4 500 000', 'text-emerald-700'],
            [ui.waiting, '18 000 000', 'text-amber-700'],
            [ui.debt, '12 450 000', 'text-red-700'],
          ].map(([l, v, c]) => (
            <div key={l} className="min-w-0 rounded-xl border border-slate-200/80 p-2.5">
              <p className="truncate text-[11px] lg:text-[10px] text-slate-500">{l}</p>
              <p
                className={`whitespace-nowrap text-[12px] font-bold tabular-nums sm:text-[13px] ${c}`}
              >
                {v}
              </p>
            </div>
          ))}
        </div>
        <div className="mt-3 rounded-xl border border-slate-200/80 p-3">
          <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">
            {ui.acceptPayment}
          </p>
          <Row
            name="Karimov Ali"
            meta={ui.septemberInvoice}
            right={<Pill tone="ok">{ui.cash}</Pill>}
          />
          <Row
            name="Tursunova Malika"
            meta={ui.septemberInvoice}
            right={<Pill tone="wait">{ui.wait}</Pill>}
          />
          <Row
            name="Abdullayev Otabek"
            meta={ui.augustInvoice}
            right={<Pill tone="debt">{ui.debtPill}</Pill>}
          />
        </div>
      </>
    )
  }
  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        {[
          [ui.children, '128'],
          [ui.groups, '6'],
          [ui.marked, '5 / 6'],
        ].map(([l, v]) => (
          <div key={l} className="min-w-0 rounded-xl border border-slate-200/80 p-2.5">
            <p className="truncate text-[11px] lg:text-[10px] text-slate-500">{l}</p>
            <p className="text-[13px] font-bold tabular-nums text-slate-900">{v}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 rounded-xl border border-slate-200/80 p-3">
        <p className="text-[12px] lg:text-[11px] font-semibold text-slate-800">{ui.groups}</p>
        {[
          ['Quyosh', '20 / 20', 'ok'],
          ['Yulduzcha', '19 / 20', 'ok'],
          ['Kamalak', '18 / 20', 'wait'],
        ].map(([n, c, tone]) => (
          <Row
            key={n}
            name={n}
            meta={ui.attendanceMarked}
            right={<Pill tone={tone as 'ok' | 'wait'}>{c}</Pill>}
            avatar={false}
          />
        ))}
      </div>
    </>
  )
}

export function Roles({ locale }: { locale: Locale }) {
  const t = copy[locale]
  const ref = useRef<HTMLElement>(null)
  const progress = useScene(ref)
  const compact = useCompact()
  const isStatic = useStatic()
  const [step, setStep] = useState(0)
  const [hover, setHover] = useState<RoleCopy['id'] | null>(null)

  const stepMv = useTransform(progress, (p) => Math.min(STEPS - 1, Math.floor(p * STEPS)))
  useMotionValueEvent(stepMv, 'change', (v) => {
    setStep(v)
    setHover(null) // scroll keyingi qadamga o'tdi — hover tanlovi bekor
  })

  const role: RoleCopy['id'] = hover ?? t.roles.items[step].id
  const active = t.roles.items.find((r) => r.id === role) ?? t.roles.items[0]

  const heading = (
    <div className="max-w-3xl">
      <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
        {t.roles.eyebrow}
      </p>
      <h2 className="mt-2 text-balance text-[1.75rem] font-extrabold !leading-[1.08] tracking-[-0.03em] text-slate-950 sm:text-4xl lg:mt-3 lg:text-[2.75rem]">
        {t.roles.title}
      </h2>
      <p className="mt-3 hidden text-base leading-7 text-slate-600 sm:block lg:text-lg">
        {t.roles.text}
      </p>
    </div>
  )

  const panel = (
    <Frame demo={t.demo} compact={compact} active={SIDEBAR[role]} className="rx-fade" key={role}>
      <div className="mb-3 flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-full bg-amber-100 text-[11px] lg:text-[10px] font-bold text-amber-800">
          {active.title.slice(0, 1)}
        </span>
        <div className="min-w-0">
          <p className="text-[12px] font-bold text-slate-900">{active.title}</p>
          <p className="truncate text-[11px] lg:text-[10px] text-slate-500">{active.focus}</p>
        </div>
      </div>
      <RoleView role={role} locale={locale} />
    </Frame>
  )

  const tabs = (
    <div
      role="tablist"
      aria-label={t.roles.eyebrow}
      className="-mx-5 flex snap-x gap-2 overflow-x-auto px-5 pb-1 [scrollbar-width:none] lg:mx-0 lg:grid lg:overflow-visible lg:px-0"
    >
      {t.roles.items.map((item, i) => {
        const on = item.id === role
        return (
          <button
            key={item.id}
            role="tab"
            aria-selected={on}
            type="button"
            onMouseEnter={() => !compact && setHover(item.id)}
            onMouseLeave={() => !compact && setHover(null)}
            onFocus={() => setHover(item.id)}
            onClick={() => setHover(item.id)}
            ref={(el) => compact && on && centerInStrip(el)}
            className={`min-w-[200px] shrink-0 snap-start rounded-2xl border p-3 text-left transition-all duration-300 lg:min-w-0 lg:p-5 ${
              on
                ? 'border-slate-950 bg-white shadow-[0_20px_50px_-30px_rgba(11,23,48,0.35)]'
                : 'border-slate-200 bg-white/60 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <p className="text-[12px] font-bold uppercase tracking-wider text-brand-700">
                {item.title}
              </p>
              <span
                className={`text-[12px] lg:text-[11px] font-semibold tabular-nums ${on ? 'text-slate-900' : 'text-slate-300'}`}
              >
                0{i + 1}
              </span>
            </div>
            <p className="mt-1.5 text-[14px] font-semibold leading-snug text-slate-900 lg:text-base">
              {item.text}
            </p>
            <p
              className={`mt-2 hidden text-[13px] leading-5 text-slate-500 transition-opacity lg:block ${on ? 'opacity-100' : 'opacity-70'}`}
            >
              {item.focus}
            </p>
          </button>
        )
      })}
    </div>
  )

  if (isStatic) {
    return (
      <section ref={ref} className="bg-slate-50 py-16 lg:py-28">
        <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
          <Reveal>{heading}</Reveal>
          <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-10">
            {tabs}
            <div>{panel}</div>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section
      ref={ref}
      className="relative bg-slate-50"
      style={{ height: compact ? `${STEPS * 60}vh` : `${STEPS * 70}vh` }}
    >
      <div className="sticky top-0 flex h-screen flex-col overflow-hidden pt-[76px]">
        <div className="mx-auto flex w-full max-w-[1280px] flex-1 flex-col px-5 pt-4 lg:justify-center lg:px-8 lg:pt-0">
          {heading}
          <div className="mt-4 grid gap-4 lg:mt-8 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-10">
            {tabs}
            <div>{panel}</div>
          </div>
          {compact && (
            <p className="mt-3 text-[13px] leading-5 text-slate-500 [@media(max-height:780px)]:hidden">
              {active.focus}
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
