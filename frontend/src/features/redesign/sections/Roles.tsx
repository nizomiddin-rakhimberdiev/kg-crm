/**
 * "Radix kimlar uchun?" — rol tanlanganda panel konteksti almashadi.
 *
 * Hover/klik (sensorli ekranda — tap). Rollar RBAC'dagi haqiqiy
 * rollar: ega, direktor, kassir, administrator.
 */

import { useState } from 'react'
import { copy, type Locale, type RoleCopy } from '../content'
import { Reveal, useCompact } from '../motion'
import { Bars, Frame, Kpi, Pill, Row } from '../ui/Mock'

function RoleView({ role, locale }: { role: RoleCopy['id']; locale: Locale }) {
  const t = copy[locale].demo
  const uz = locale === 'uz'
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
            <p className="text-[11px] font-semibold text-slate-800">
              {uz ? 'Filiallar' : 'Филиалы'}
            </p>
            <Row
              name={uz ? 'Chilonzor' : 'Чиланзар'}
              meta="68 · 94 %"
              right={<Pill tone="ok">46 800 000</Pill>}
              avatar={false}
            />
            <Row
              name={uz ? 'Yunusobod' : 'Юнусабад'}
              meta="60 · 93 %"
              right={<Pill tone="ok">39 600 000</Pill>}
              avatar={false}
            />
          </div>
          <div className="rounded-xl border border-slate-200/80 p-3">
            <p className="text-[11px] font-semibold text-slate-800">{t.chartTitle}</p>
            <Bars values={[61, 68, 72, 70, 79, 86]} labels={t.months} className="mt-2" />
          </div>
        </div>
      </>
    )
  }
  if (role === 'director') {
    return (
      <>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {[t.kpis[1], t.kpis[0], t.kpis[4]].map((kpi, i) => (
            <Kpi key={kpi.label} kpi={kpi} index={[1, 0, 4][i]} />
          ))}
        </div>
        <div className="mt-3 rounded-xl border border-slate-200/80 p-3">
          <p className="text-[11px] font-semibold text-slate-800">
            {uz ? 'Bugungi vazifalar' : 'Задачи на сегодня'}
          </p>
          <Row
            name={
              uz
                ? 'Kamalak guruhi davomati belgilanmagan'
                : 'Группа Kamalak — посещаемость не отмечена'
            }
            right={<Pill tone="wait">08:40</Pill>}
            avatar={false}
          />
          <Row
            name={
              uz ? '2 ta yangi bola — guruhga biriktirish' : '2 новых ребёнка — зачислить в группу'
            }
            right={<Pill tone="neutral">{uz ? 'bugun' : 'сегодня'}</Pill>}
            avatar={false}
          />
          <Row
            name={uz ? 'Oshpaz — avans so‘rovi' : 'Повар — запрос аванса'}
            right={<Pill tone="neutral">400 000</Pill>}
            avatar={false}
          />
        </div>
      </>
    )
  }
  if (role === 'cashier') {
    return (
      <>
        <div className="grid grid-cols-3 gap-2">
          {[
            [uz ? 'Bugun qabul qilindi' : 'Принято сегодня', '4 500 000', 'text-emerald-700'],
            [uz ? 'Kutilmoqda' : 'Ожидает', '18 000 000', 'text-amber-700'],
            [uz ? 'Qarzdorlik' : 'Долг', '12 450 000', 'text-red-700'],
          ].map(([l, v, c]) => (
            <div key={l} className="rounded-xl border border-slate-200/80 p-2.5">
              <p className="text-[10px] text-slate-500">{l}</p>
              <p className={`text-[13px] font-bold tabular-nums ${c}`}>{v}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 rounded-xl border border-slate-200/80 p-3">
          <p className="text-[11px] font-semibold text-slate-800">
            {uz ? 'To‘lov qabul qilish' : 'Приём оплаты'}
          </p>
          <Row
            name="Karimov Ali"
            meta={uz ? 'Sentabr · 1 500 000' : 'Сентябрь · 1 500 000'}
            right={<Pill tone="ok">{uz ? 'naqd' : 'наличные'}</Pill>}
          />
          <Row
            name="Tursunova Malika"
            meta={uz ? 'Sentabr · 1 500 000' : 'Сентябрь · 1 500 000'}
            right={<Pill tone="wait">{uz ? 'kutilmoqda' : 'ожидает'}</Pill>}
          />
          <Row
            name="Abdullayev Otabek"
            meta={uz ? 'Avgust · 600 000' : 'Август · 600 000'}
            right={<Pill tone="debt">{uz ? 'qarz' : 'долг'}</Pill>}
          />
        </div>
      </>
    )
  }
  return (
    <>
      <div className="grid grid-cols-3 gap-2">
        {[
          [uz ? 'Bolalar' : 'Дети', '128'],
          [uz ? 'Guruhlar' : 'Группы', '6'],
          [uz ? 'Bugun belgilangan' : 'Отмечено сегодня', '5 / 6'],
        ].map(([l, v]) => (
          <div key={l} className="rounded-xl border border-slate-200/80 p-2.5">
            <p className="text-[10px] text-slate-500">{l}</p>
            <p className="text-[13px] font-bold tabular-nums text-slate-900">{v}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 rounded-xl border border-slate-200/80 p-3">
        <p className="text-[11px] font-semibold text-slate-800">{uz ? 'Guruhlar' : 'Группы'}</p>
        {[
          ['Quyosh', '20 / 20', 'ok'],
          ['Yulduzcha', '19 / 20', 'ok'],
          ['Kamalak', '18 / 20', 'wait'],
        ].map(([n, c, tone]) => (
          <Row
            key={n}
            name={n}
            meta={uz ? 'davomat belgilangan' : 'посещаемость отмечена'}
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
  const [role, setRole] = useState<RoleCopy['id']>('owner')
  const compact = useCompact()
  const active = t.roles.items.find((r) => r.id === role) ?? t.roles.items[0]

  return (
    <section className="bg-slate-50 py-16 lg:py-28">
      <div className="mx-auto max-w-[1280px] px-5 lg:px-8">
        <Reveal>
          <div className="max-w-3xl">
            <p className="text-[13px] font-bold uppercase tracking-[0.16em] text-brand-700">
              {t.roles.eyebrow}
            </p>
            <h2 className="mt-3 text-balance text-3xl font-extrabold !leading-[1.08] tracking-[-0.03em] text-slate-950 sm:text-4xl lg:text-[3.4rem]">
              {t.roles.title}
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-600 lg:text-lg">{t.roles.text}</p>
          </div>
        </Reveal>

        <div className="mt-8 grid gap-6 lg:mt-12 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-10">
          <div
            role="tablist"
            aria-label={t.roles.eyebrow}
            className="-mx-5 flex snap-x gap-2 overflow-x-auto px-5 pb-1 lg:mx-0 lg:grid lg:overflow-visible lg:px-0"
          >
            {t.roles.items.map((item) => {
              const on = item.id === role
              return (
                <button
                  key={item.id}
                  role="tab"
                  aria-selected={on}
                  type="button"
                  onMouseEnter={() => !compact && setRole(item.id)}
                  onFocus={() => setRole(item.id)}
                  onClick={() => setRole(item.id)}
                  className={`min-w-[220px] snap-start rounded-2xl border p-4 text-left transition-all duration-300 lg:min-w-0 lg:p-5 ${
                    on
                      ? 'border-slate-950 bg-white shadow-[0_20px_50px_-30px_rgba(11,23,48,0.35)]'
                      : 'border-slate-200 bg-white/60 hover:border-slate-300'
                  }`}
                >
                  <p className="text-[12px] font-bold uppercase tracking-wider text-brand-700">
                    {item.title}
                  </p>
                  <p className="mt-1.5 text-[15px] font-semibold leading-snug text-slate-900 lg:text-base">
                    {item.text}
                  </p>
                  <p
                    className={`mt-2 text-[13px] leading-5 text-slate-500 transition-opacity ${on ? 'opacity-100' : 'opacity-70'}`}
                  >
                    {item.focus}
                  </p>
                </button>
              )
            })}
          </div>
          <div>
            <Frame
              demo={t.demo}
              compact={compact}
              active={role === 'owner' ? 0 : role === 'director' ? 5 : role === 'cashier' ? 3 : 1}
              className="rx-fade"
              key={role}
            >
              <div className="mb-3 flex items-center gap-2">
                <span className="grid h-7 w-7 place-items-center rounded-full bg-amber-100 text-[10px] font-bold text-amber-800">
                  {active.title.slice(0, 1)}
                </span>
                <div>
                  <p className="text-[12px] font-bold text-slate-900">{active.title}</p>
                  <p className="text-[10px] text-slate-500">{active.focus}</p>
                </div>
              </div>
              <RoleView role={role} locale={locale} />
            </Frame>
          </div>
        </div>
      </div>
    </section>
  )
}
