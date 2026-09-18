/**
 * "Radix bilan bir kun" — vaqt scroll bilan o'tadi.
 *
 * Soat 08:00 dan 17:00 gacha progressga bog'liq (uzluksiz), bosqichlar
 * vaqt chegarasidan o'tganda almashadi, o'ngdagi panel esa shu bosqichning
 * ekranini ko'rsatadi. Mobil: vertikal vaqt chizig'i, kartalar.
 */

import { useRef, useState } from 'react'
import { motion, useMotionValue, useMotionValueEvent, useTransform } from 'framer-motion'
import { copy, type Locale } from '../content'
import { Reveal, useCompact, useScene, useStatic } from '../motion'
import { Frame, Pill, Row } from '../ui/Mock'
import { AttendanceUi, PaymentsUi, ReportsUi, StaffUi } from './Modules'

const START = 8 * 60
const END = 17 * 60
const TIMES = [8 * 60, 9 * 60 + 30, 12 * 60, 15 * 60, 17 * 60]

const clock = (minutes: number) => {
  const m = Math.round(minutes)
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
}

function GroupsUi({ locale }: { locale: Locale }) {
  const uz = locale === 'uz'
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="rounded-xl border border-slate-200/80 p-3">
        <p className="text-[11px] font-semibold text-slate-800">{uz ? 'Guruhlar' : 'Группы'}</p>
        {[
          ['Quyosh', '20 / 20', 'neutral'],
          ['Yulduzcha', '19 / 20', 'ok'],
          ['Kamalak', '18 / 20', 'neutral'],
        ].map(([n, c, tone]) => (
          <Row
            key={n}
            name={n}
            meta={uz ? '3–4 yosh' : '3–4 года'}
            right={<Pill tone={tone as 'ok' | 'neutral'}>{c}</Pill>}
            avatar={false}
            active={n === 'Yulduzcha'}
          />
        ))}
      </div>
      <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">
          {uz ? 'Yangi bola' : 'Новый ребёнок'}
        </p>
        <p className="mt-1 text-[12px] font-bold text-slate-900">Nazarova Madina</p>
        <p className="text-[10px] text-slate-500">
          {uz ? 'Yulduzcha guruhiga biriktirildi' : 'Зачислена в группу Yulduzcha'}
        </p>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-emerald-100">
          <div className="h-full w-[95%] rounded-full bg-emerald-500" />
        </div>
        <p className="mt-1 text-[10px] text-slate-500">
          {uz ? 'Sig‘im 19 / 20' : 'Заполненность 19 / 20'}
        </p>
      </div>
    </div>
  )
}

export function Workflow({ locale }: { locale: Locale }) {
  const t = copy[locale]
  const ref = useRef<HTMLElement>(null)
  const progress = useScene(ref)
  const compact = useCompact()
  const isStatic = useStatic()
  const one = useMotionValue(1)

  const minutes = useTransform(progress, [0.06, 0.9], [START, END], { clamp: true })
  const label = useTransform(minutes, clock)
  const markerTop = useTransform(progress, [0.06, 0.9], ['0%', '100%'], { clamp: true })
  const stepMv = useTransform(minutes, (m) => {
    let s = 0
    TIMES.forEach((time, i) => {
      if (m >= time - 1) s = i
    })
    return s
  })
  const [step, setStep] = useState(0)
  useMotionValueEvent(stepMv, 'change', (v) => setStep(v))

  const heading = (
    <div className="max-w-3xl">
      <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
        {t.workflow.eyebrow}
      </p>
      <h2 className="mt-3 text-balance text-3xl font-extrabold !leading-[1.08] tracking-[-0.03em] text-slate-950 sm:text-4xl lg:text-[3.4rem]">
        {t.workflow.title}
      </h2>
      <p className="mt-4 text-base leading-7 text-slate-600 lg:text-lg">{t.workflow.text}</p>
    </div>
  )

  if (isStatic) {
    return (
      <section ref={ref} className="bg-white py-16 lg:py-24">
        <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
          <Reveal>{heading}</Reveal>
          <ol className="relative mt-8 space-y-4 border-l-2 border-slate-200 pl-6">
            {t.workflow.steps.map((s, i) => (
              <Reveal key={s.time} delay={i * 0.04}>
                <li className="relative">
                  <span className="absolute -left-[31px] top-1.5 grid h-3 w-3 place-items-center rounded-full bg-brand-600 ring-4 ring-white" />
                  <p className="text-[13px] font-bold tabular-nums text-brand-700">{s.time}</p>
                  <h3 className="mt-0.5 text-lg font-bold tracking-tight text-slate-950">
                    {s.title}
                  </h3>
                  <p className="mt-1 text-[15px] leading-6 text-slate-600">{s.text}</p>
                </li>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>
    )
  }

  const views = [
    <AttendanceUi key="a" local={one} locale={locale} compact={compact} />,
    <GroupsUi key="g" locale={locale} />,
    <PaymentsUi key="p" local={one} locale={locale} compact={compact} />,
    <StaffUi key="s" local={one} locale={locale} compact={compact} />,
    <ReportsUi key="r" local={one} locale={locale} compact={compact} />,
  ]

  if (compact) {
    const current = t.workflow.steps[step]
    return (
      <section ref={ref} className="relative bg-white" style={{ height: '300vh' }}>
        <div className="sticky top-0 flex h-screen flex-col overflow-hidden pt-[76px]">
          <div className="px-5 pt-3">
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
              {t.workflow.eyebrow}
            </p>
            <h2 className="mt-1.5 text-balance text-[1.6rem] font-extrabold !leading-[1.08] tracking-[-0.03em] text-slate-950">
              {t.workflow.title}
            </h2>
            <div className="mt-3 flex items-baseline gap-2">
              <motion.span className="text-4xl font-extrabold tabular-nums tracking-tight text-slate-950">
                {label}
              </motion.span>
              <span className="text-[12px] text-slate-400">{t.demo.today}</span>
            </div>
            {/* Gorizontal vaqt chizig'i — marker scroll bilan yuradi. */}
            <div className="relative mt-3 h-1 rounded-full bg-slate-200">
              <motion.span
                aria-hidden="true"
                style={{ left: markerTop }}
                className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand-600 ring-4 ring-white"
              />
            </div>
            <ol className="mt-2 flex justify-between">
              {t.workflow.steps.map((s, i) => (
                <li
                  key={s.time}
                  className={`text-[11px] font-semibold tabular-nums transition-colors ${i === step ? 'text-brand-700' : 'text-slate-400'}`}
                >
                  {s.time}
                </li>
              ))}
            </ol>
          </div>
          <div className="mt-3 px-5">
            <Frame
              demo={t.demo}
              compact
              active={[5, 2, 3, 6, 0][step]}
              className="rx-fade"
              key={step}
            >
              {views[step]}
            </Frame>
          </div>
          <div className="px-5 pt-3">
            <h3 className="text-lg font-bold tracking-tight text-slate-950">{current.title}</h3>
            <p className="mt-1 line-clamp-2 text-[14px] leading-6 text-slate-600">{current.text}</p>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section ref={ref} className="relative bg-white" style={{ height: '320vh' }}>
      <div className="sticky top-0 flex h-screen items-center overflow-hidden pt-[76px]">
        <div className="mx-auto grid w-full max-w-[1280px] grid-cols-[minmax(0,5fr)_minmax(0,7fr)] items-center gap-12 px-8">
          <div>
            {heading}
            <div className="mt-8 flex items-baseline gap-3">
              <motion.span className="text-5xl font-extrabold tabular-nums tracking-tight text-slate-950">
                {label}
              </motion.span>
              <span className="text-sm font-medium text-slate-400">{t.demo.today}</span>
            </div>
            <ol className="relative mt-6 border-l-2 border-slate-200 pl-6">
              <motion.span
                aria-hidden="true"
                style={{ top: markerTop }}
                className="absolute -left-[7px] h-3 w-3 -translate-y-1/2 rounded-full bg-brand-600 ring-4 ring-white"
              />
              {t.workflow.steps.map((s, i) => {
                const on = i === step
                return (
                  <li
                    key={s.time}
                    className={`py-2 transition-opacity duration-300 ${on ? 'opacity-100' : 'opacity-45'}`}
                  >
                    <div className="flex items-baseline gap-3">
                      <span className="w-12 text-[13px] font-bold tabular-nums text-brand-700">
                        {s.time}
                      </span>
                      <span className="text-lg font-bold tracking-tight text-slate-950">
                        {s.title}
                      </span>
                    </div>
                    <div
                      className="grid transition-[grid-template-rows] duration-300"
                      style={{ gridTemplateRows: on ? '1fr' : '0fr' }}
                    >
                      <p className="overflow-hidden pl-[60px] text-[15px] leading-6 text-slate-600">
                        {s.text}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ol>
          </div>
          <div>
            <Frame demo={t.demo} active={[5, 2, 3, 6, 0][step]} className="rx-fade" key={step}>
              {views[step]}
            </Frame>
          </div>
        </div>
      </div>
    </section>
  )
}
