/**
 * Olti modul — yopishqoq ro'yxat + jonli mahsulot paneli.
 *
 * Chap ustunda ro'yxat, o'ngda panel. Har bir modul uchun ekran balandligi
 * bitta "qadam": qadam ichida (local 0 → 1) UI o'z hikoyasini ko'rsatadi —
 * ro'yxat filtrlanadi, to'lov holati o'zgaradi, davomat to'ladi, ombor
 * kamayadi. Planshet: ham pinned — chip qatori + panel + matn.
 *
 * Telefon (PLAN 5.7): pinned EMAS va oltita panel ketma-ket ham EMAS —
 * bitta panel, chiplar bosiladi. Oltita mock ekranni ustma-ust qo'yish
 * telefonda ~4 000 px edi: bir xil ramka olti marta takrorlanardi.
 */

import { useRef, useState, type ReactNode } from 'react'
import { useMotionValue, useMotionValueEvent, useTransform, type MotionValue } from 'framer-motion'
import { Check, ChevronRight } from 'lucide-react'
import { copy, groupThousands, type Locale, type ModuleCopy } from '../content'
import { Reveal, usePhone, useScene, useStaticScene } from '../motion'
import { Bars, Frame, Kpi, Pill, Row } from '../ui/Mock'
import { Num } from '../ui/Num'

const STEPS = 6

/** local (0..1) → 0 | 1 | 2 bosqich. Boshlang'ich qiymat MotionValue'dan — statik holatda darhol yakuniy. */
function usePhase(local: MotionValue<number>, cuts: [number, number]) {
  const toPhase = (v: number): 0 | 1 | 2 => (v < cuts[0] ? 0 : v < cuts[1] ? 1 : 2)
  const [phase, setPhase] = useState<0 | 1 | 2>(() => toPhase(local.get()))
  useMotionValueEvent(local, 'change', (v) => setPhase(toPhase(v)))
  return phase
}

const CHILDREN = [
  ['Karimov Ali', 'Quyosh'],
  ['Yusupova Dilnoza', 'Yulduzcha'],
  ['Rasulov Bekzod', 'Quyosh'],
  ['Tursunova Malika', 'Kamalak'],
  ['Abdullayev Otabek', 'Quyosh'],
  ['Ibragimova Zilola', 'Yulduzcha'],
  ['Umarov Sanjar', 'Quyosh'],
] as const

type UiProps = { local: MotionValue<number>; locale: Locale; compact?: boolean }

export function ChildrenUi({ local, locale, compact = false }: UiProps) {
  const phase = usePhase(local, [0.35, 0.7])
  const ui = copy[locale].ui.children
  const groups = [ui.all, 'Quyosh', 'Yulduzcha', 'Kamalak']
  return (
    <div className="grid gap-3 sm:grid-cols-[1.3fr_1fr]">
      <div>
        <div className="flex gap-1.5">
          {groups.map((g, i) => (
            <span
              key={g}
              className={`rounded-full px-2.5 py-1 text-[12px] font-semibold transition-colors duration-300 ${
                (phase >= 1 ? i === 1 : i === 0)
                  ? 'bg-slate-950 text-white'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              {g}
            </span>
          ))}
        </div>
        <div className="mt-2 space-y-0.5">
          {CHILDREN.slice(0, compact ? (phase === 2 ? 2 : 5) : 7).map(([name, group], i) => (
            <div
              key={name}
              className="transition-all duration-500"
              style={{
                opacity: phase >= 1 && group !== 'Quyosh' ? 0.18 : 1,
                transform: phase >= 1 && group !== 'Quyosh' ? 'translateX(6px)' : 'none',
              }}
            >
              <Row
                name={name}
                meta={group}
                active={phase === 2 && i === 0}
                right={<ChevronRight className="h-3.5 w-3.5 text-slate-300" />}
              />
            </div>
          ))}
        </div>
      </div>
      <div
        className="rounded-xl border border-brand-200 bg-brand-50/40 p-3 transition-all duration-500"
        style={{
          opacity: phase === 2 ? 1 : 0,
          transform: phase === 2 ? 'none' : 'translateX(24px)',
        }}
      >
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-slate-950 text-[12px] font-bold text-white">
            KA
          </span>
          <div>
            <p className="text-[12px] font-bold text-slate-900">Karimov Ali</p>
            <p className="text-[12px] text-slate-500">Quyosh · 4 {ui.age}</p>
          </div>
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-2 gap-y-1.5 text-[12px]">
          <dt className="text-slate-500">{ui.tariff}</dt>
          <dd className="font-semibold text-slate-800">1 500 000</dd>
          <dt className="text-slate-500">{ui.guardian}</dt>
          <dd className="font-semibold text-slate-800">Karimova N.</dd>
          <dt className="text-slate-500">{ui.balance}</dt>
          <dd className="font-semibold text-red-700">−1 500 000</dd>
          <dt className="text-slate-500">{ui.attendance}</dt>
          <dd className="font-semibold text-emerald-700">92 %</dd>
        </dl>
      </div>
    </div>
  )
}

export function PaymentsUi({ local, locale }: UiProps) {
  const phase = usePhase(local, [0.33, 0.66])
  const L = copy[locale].ui.payments
  const rows = [
    ['Karimov Ali', 1_500_000, phase >= 1 ? 'ok' : 'wait'],
    ['Yusupova Dilnoza', 1_500_000, phase >= 1 ? 'ok' : 'wait'],
    ['Rasulov Bekzod', 1_500_000, phase >= 2 ? 'ok' : 'wait'],
    ['Tursunova Malika', 1_500_000, 'wait'],
    ['Abdullayev Otabek', 600_000, phase >= 2 ? 'debt' : 'wait'],
  ] as const
  const paid = rows.filter((r) => r[2] === 'ok').reduce((s, r) => s + r[1], 0)
  const wait = rows.filter((r) => r[2] === 'wait').reduce((s, r) => s + r[1], 0)
  const debt = rows.filter((r) => r[2] === 'debt').reduce((s, r) => s + r[1], 0)
  return (
    <div>
      <div className="grid grid-cols-3 gap-2">
        {[
          [L.paid, paid, 'text-emerald-700'],
          [L.wait, wait, 'text-amber-700'],
          [L.debt, debt, 'text-red-700'],
        ].map(([label, value, cls]) => (
          <div key={String(label)} className="rounded-xl border border-slate-200/80 p-2.5">
            <p className="text-[12px] capitalize text-slate-500">{label}</p>
            <Num value={Number(value)} className={`text-[13px] font-bold tabular-nums ${cls}`} />
          </div>
        ))}
      </div>
      <div className="mt-2 space-y-0.5">
        {rows.map(([name, amount, tone]) => (
          <Row
            key={name}
            name={name}
            meta={groupThousands(amount)}
            right={<Pill tone={tone}>{L[tone === 'ok' ? 'paid' : tone]}</Pill>}
          />
        ))}
      </div>
    </div>
  )
}

export function AttendanceUi({ local, locale }: UiProps) {
  const ui = copy[locale].ui.attendance
  const toMarked = (v: number) => Math.min(19, Math.round(v * 24))
  const [marked, setMarked] = useState(() => toMarked(local.get()))
  useMotionValueEvent(local, 'change', (v) => setMarked(toMarked(v)))
  const present = marked
  const pct = Math.round((present / 20) * 100)
  return (
    <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
      <div>
        <p className="text-[12px] font-semibold text-slate-800">Quyosh · {ui.today}</p>
        <div className="mt-2 grid grid-cols-10 gap-1.5">
          {Array.from({ length: 20 }).map((_, i) => (
            <span
              key={i}
              className={`grid aspect-square place-items-center rounded-md text-[12px] font-bold transition-colors duration-300 ${
                i < present
                  ? 'bg-emerald-500 text-white'
                  : i === 19 && present >= 19
                    ? 'bg-red-100 text-red-600'
                    : 'bg-slate-100 text-slate-400'
              }`}
            >
              {i < present ? (
                <Check className="h-3 w-3" strokeWidth={3} />
              ) : i === 19 && present >= 19 ? (
                '×'
              ) : (
                ''
              )}
            </span>
          ))}
        </div>
      </div>
      <div className="rounded-xl border border-slate-200/80 p-3 sm:w-36">
        <p className="text-[12px] text-slate-500">{ui.title}</p>
        <p className="text-2xl font-bold tabular-nums text-slate-950">
          <Num value={pct} format={(v) => String(Math.round(v))} duration={0.3} />%
        </p>
        <p className="text-[12px] text-slate-500">
          {present} / 20 · {ui.present}
        </p>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-emerald-500 transition-[width] duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  )
}

export function StaffUi({ local, locale }: UiProps) {
  const phase = usePhase(local, [0.35, 0.7])
  const ui = copy[locale].ui.staff
  const rows = [
    ['Rahimova Dilnoza', ui.director, 6_500_000],
    ['Sodiqova Nilufar', ui.teacher, 3_800_000],
    ['Karimova Sevara', ui.teacher, 3_800_000],
    ['Tosheva Gulnora', ui.cashier, 3_200_000],
    ['Aliyev Rustam', ui.cook, 3_000_000],
  ] as const
  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="text-[12px] font-semibold text-slate-800">{ui.title}</p>
        <span
          className="text-[12px] text-slate-500 transition-opacity duration-500"
          style={{ opacity: phase >= 1 ? 1 : 0 }}
        >
          {ui.payroll}
        </span>
      </div>
      <div className="mt-2 space-y-0.5">
        {rows.map(([name, role, salary], i) => (
          <Row
            key={name}
            name={name}
            meta={role}
            right={
              <div className="flex items-center gap-1.5">
                {phase === 2 && i === 4 && <Pill tone="wait">{ui.advance}</Pill>}
                <span
                  className="text-[12px] font-semibold tabular-nums text-slate-800 transition-opacity duration-500"
                  style={{ opacity: phase >= 1 ? 1 : 0 }}
                >
                  {groupThousands(salary)}
                </span>
              </div>
            }
          />
        ))}
      </div>
      <div
        className="mt-2 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 transition-opacity duration-500"
        style={{ opacity: phase === 2 ? 1 : 0 }}
      >
        <span className="text-[12px] text-slate-500">{ui.total}</span>
        <Num value={31_500_000} className="text-[12px] font-bold tabular-nums text-slate-900" />
      </div>
    </div>
  )
}

export function InventoryUi({ local, locale, compact = false }: UiProps) {
  const phase = usePhase(local, [0.4, 0.75])
  const ui = copy[locale].ui.inventory
  const stock = [
    [ui.rice, 'kg', 42, 26],
    [ui.flour, 'kg', 30, 18],
    [ui.oil, 'l', 12, 7],
    [ui.sugar, 'kg', 20, 14],
  ] as const
  const expenses = [
    [ui.food, 2_300_000],
    [ui.utilities, 1_150_000],
    [ui.repair, 480_000],
  ] as const
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="rounded-xl border border-slate-200/80 p-3">
        <p className="text-[12px] font-semibold text-slate-800">{ui.stock}</p>
        <ul className="mt-2 space-y-2">
          {stock.slice(0, compact ? 3 : 4).map(([name, unit, from, to]) => {
            const value = phase === 0 ? from : phase === 1 ? Math.round((from + to) / 2) : to
            return (
              <li key={name}>
                <div className="flex justify-between text-[12px]">
                  <span className="text-slate-600">{name}</span>
                  <span className="font-semibold tabular-nums text-slate-800">
                    <Num value={value} format={(v) => String(Math.round(v))} duration={0.5} />{' '}
                    {unit}
                  </span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-[width] duration-700 ${value / from < 0.6 ? 'bg-amber-500' : 'bg-brand-600'}`}
                    style={{ width: `${(value / from) * 100}%` }}
                  />
                </div>
              </li>
            )
          })}
        </ul>
      </div>
      <div className="rounded-xl border border-slate-200/80 p-3">
        <p className="text-[12px] font-semibold text-slate-800">{ui.expenses}</p>
        <ul className="mt-2 space-y-1">
          {expenses.map(([name, amount], i) => (
            <li
              key={name}
              className="flex items-center justify-between rounded-lg px-2 py-1.5 text-[12px] transition-all duration-500"
              style={{
                opacity: i <= phase ? 1 : 0,
                transform: i <= phase ? 'none' : 'translateY(6px)',
                background: i === phase ? 'rgb(246 247 244)' : 'transparent',
              }}
            >
              <span className="text-slate-700">{name}</span>
              <span className="font-semibold tabular-nums text-slate-900">
                {groupThousands(amount)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export function ReportsUi({ local, locale, compact = false }: UiProps) {
  const phase = usePhase(local, [0.3, 0.6])
  const t = copy[locale].demo
  const spread = ['-14px, -10px', '14px, -8px', '-10px, 10px', '12px, 12px']
  return (
    <div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {t.kpis.slice(0, 4).map((kpi, i) => (
          <div
            key={kpi.label}
            className="transition-transform duration-700"
            style={{
              transform:
                phase === 0 ? `translate(${spread[i]}) rotate(${i % 2 ? 2 : -2}deg)` : 'none',
            }}
          >
            <Kpi kpi={kpi} index={i} money={kpi.value > 999} />
          </div>
        ))}
      </div>
      <div
        className="mt-3 rounded-xl border border-slate-200/80 p-3 transition-opacity duration-500"
        style={{ opacity: phase >= 1 ? 1 : 0.35 }}
      >
        <p className="text-[12px] font-semibold text-slate-800">{t.chartTitle}</p>
        <Bars
          values={[61, 68, 72, 70, 79, 86]}
          labels={t.months}
          progress={phase === 2 ? 1 : phase === 1 ? 0.45 : 0.1}
          className={compact ? 'mt-2 [&>div]:!h-14' : 'mt-2'}
        />
      </div>
    </div>
  )
}

const UI: Record<ModuleCopy['id'], (p: UiProps) => ReactNode> = {
  children: ChildrenUi,
  payments: PaymentsUi,
  attendance: AttendanceUi,
  staff: StaffUi,
  inventory: InventoryUi,
  reports: ReportsUi,
}

export function Modules({ locale }: { locale: Locale }) {
  const t = copy[locale]
  const ref = useRef<HTMLElement>(null)
  const progress = useScene(ref)
  const isStatic = useStaticScene()

  const activeMv = useTransform(progress, (p) => Math.min(STEPS - 1, Math.floor(p * STEPS)))
  const local = useTransform(progress, (p) => {
    const a = Math.min(STEPS - 1, Math.floor(p * STEPS))
    return Math.min(1, Math.max(0, p * STEPS - a))
  })
  const [active, setActive] = useState(0)
  useMotionValueEvent(activeMv, 'change', (v) => setActive(v))
  const one = useMotionValue(1)
  const phone = usePhone()
  const [picked, setPicked] = useState(0)

  if (isStatic && phone) {
    const item = t.modules.items[picked]
    const Ui = UI[item.id]
    return (
      <section ref={ref} id="capabilities" className="bg-slate-50 py-14">
        <div className="px-5">
          <Reveal>
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
              {t.modules.eyebrow}
            </p>
            <h2 className="mt-2 text-balance text-[1.6rem] font-bold !leading-[1.12] tracking-[-0.03em] text-slate-950">
              {t.modules.title}
            </h2>
          </Reveal>
          {/* Chiplar — tugma: telefonda scroll emas, bosish modulni almashtiradi. */}
          <div
            role="tablist"
            aria-label={t.modules.title}
            className="-mx-5 mt-5 flex gap-1.5 overflow-x-auto px-5 pb-1 [scrollbar-width:none]"
          >
            {t.modules.items.map((m, i) => (
              <button
                key={m.id}
                type="button"
                role="tab"
                aria-selected={i === picked}
                onClick={() => setPicked(i)}
                className={`shrink-0 rounded-full px-3 py-1.5 text-[13px] font-semibold transition-colors ${
                  i === picked
                    ? 'bg-slate-950 text-white'
                    : 'bg-white text-slate-600 ring-1 ring-slate-200'
                }`}
              >
                0{i + 1} · {m.title}
              </button>
            ))}
          </div>
          <div className="mt-3" role="tabpanel">
            <Frame demo={t.demo} compact className="rx-fade" key={item.id}>
              <Ui local={one} locale={locale} compact />
            </Frame>
          </div>
          <h3 className="mt-4 text-lg font-bold tracking-tight text-slate-950">{item.title}</h3>
          <p className="mt-1 text-[15px] leading-6 text-slate-600">{item.text}</p>
          <p className="mt-2 text-[12px] text-slate-500">{item.caption}</p>
        </div>
      </section>
    )
  }

  if (isStatic) {
    return (
      <section ref={ref} id="capabilities" className="bg-slate-50 py-14 lg:py-24">
        <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
          <Reveal>
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
              {t.modules.eyebrow}
            </p>
            <h2 className="mt-3 text-balance text-[1.75rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900 sm:text-[2rem]">
              {t.modules.title}
            </h2>
          </Reveal>
          {/*
            Ikki ustun faqat `lg` dan: 768 px da karta 340 px bo'lib
            qolardi va uning ICHIDAGI mahsulot ko'rinishi yana ikkiga
            bo'linib, ustunlar 41 px ga tushardi — "Karimova N." dan
            "Kar…" qolardi.
          */}
          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            {t.modules.items.map((item, i) => {
              const Ui = UI[item.id]
              return (
                <Reveal key={item.id} delay={(i % 2) * 0.06}>
                  <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-5">
                    <span className="text-[12px] font-bold text-brand-700">0{i + 1}</span>
                    <h3 className="mt-1 text-xl font-bold tracking-tight text-slate-950">
                      {item.title}
                    </h3>
                    <p className="mt-2 text-[15px] leading-6 text-slate-600">{item.text}</p>
                    <div className="mt-4 rounded-xl border border-slate-200/80 bg-slate-50/60 p-3">
                      <Ui local={one} locale={locale} />
                    </div>
                    <p className="mt-3 text-[12px] text-slate-400">{item.caption}</p>
                  </article>
                </Reveal>
              )
            })}
          </div>
        </div>
      </section>
    )
  }

  const item = t.modules.items[active]
  const Ui = UI[item.id]

  return (
    <section
      ref={ref}
      id="capabilities"
      className="relative bg-slate-50"
      style={{ height: `${STEPS * 90}vh` }}
    >
      <div className="sticky top-0 flex h-screen items-center overflow-hidden pt-[76px]">
        <div className="mx-auto grid w-full max-w-[1280px] grid-cols-[minmax(0,5fr)_minmax(0,7fr)] items-center gap-12 px-8">
          <div>
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
              {t.modules.eyebrow}
            </p>
            <h2 className="mt-3 text-balance text-[2rem] font-bold !leading-[1.16] tracking-[-0.02em] text-tosh-900">
              {t.modules.title}
            </h2>
            <ol className="mt-8 space-y-1">
              {t.modules.items.map((m, i) => {
                const on = i === active
                return (
                  <li
                    key={m.id}
                    className={`rounded-xl px-4 py-3 transition-colors duration-300 ${on ? 'bg-white shadow-card' : ''}`}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`text-[12px] font-bold tabular-nums ${on ? 'text-brand-700' : 'text-slate-400'}`}
                      >
                        0{i + 1}
                      </span>
                      <span
                        className={`text-lg font-bold tracking-tight ${on ? 'text-slate-950' : 'text-slate-500'}`}
                      >
                        {m.title}
                      </span>
                    </div>
                    <div
                      className="grid transition-[grid-template-rows] duration-400"
                      style={{ gridTemplateRows: on ? '1fr' : '0fr' }}
                    >
                      <p className="overflow-hidden pl-8 text-[15px] leading-6 text-slate-600">
                        <span
                          className={`block pt-1.5 transition-opacity duration-300 ${on ? 'opacity-100' : 'opacity-0'}`}
                        >
                          {m.text}
                        </span>
                      </p>
                    </div>
                  </li>
                )
              })}
            </ol>
          </div>
          <div>
            <Frame
              demo={t.demo}
              active={[1, 3, 5, 6, 7, 8][active]}
              className="rx-fade"
              key={item.id}
            >
              <Ui local={local} locale={locale} />
            </Frame>
            <p className="mt-3 text-center text-[12px] text-slate-400">{item.caption}</p>
          </div>
        </div>
      </div>
    </section>
  )
}
