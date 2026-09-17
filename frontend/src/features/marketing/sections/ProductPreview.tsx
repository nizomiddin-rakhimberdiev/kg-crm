/**
 * Mahsulot ko'rinishi — brauzer oynasi ichidagi dashboard maketi.
 *
 * Skrinshot EMAS, balki CSS bilan qurilgan: skrinshot birinchi
 * o'zgarishdayoq eskiradi va uni yangilashni hech kim eslamaydi, ustiga
 * u mobil ekranda o'qilmaydigan darajada kichrayadi. Bu maket haqiqiy
 * dashboard tuzilmasini (4 KPI, oylik dinamika, so'nggi to'lovlar) va
 * faqat MAVJUD modullarni ko'rsatadi.
 *
 * Auditdan keyin maket to'liq kenglikka chiqarildi va ichki matn
 * kattalashtirildi — avval desktopda ~55% kenglikda, 9-10px matn bilan
 * turardi va "real dastur" taassurotini bermasdi.
 */

import { BarChart3 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Reveal } from '../components/Motion'
import { copy, type Locale } from '../content'

const BARS = [34, 56, 43, 76, 61, 90, 79, 100]
const RECENT = ['M. Karimova', 'A. Ismoilov', 'N. Rustamov', 'S. Yusupova']

export function ProductPreview({ locale }: { locale: Locale }) {
  const t = copy[locale].preview

  const metrics: Array<[string, string, string]> = [
    [t.revenue, '18 500 000', 'bg-brand-50 text-brand-700'],
    [t.debt, '2 400 000', 'bg-amber-50 text-amber-700'],
    [t.attendance, '91%', 'bg-emerald-50 text-emerald-700'],
    [t.children, '142', 'bg-violet-50 text-violet-700'],
  ]

  return (
    <section id="product" className="scroll-mt-24 bg-slate-50 py-14 sm:py-16 lg:py-28">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <Reveal className="max-w-3xl">
          <p className="eyebrow">{t.eyebrow}</p>
          <h2 className="section-title mt-4 text-balance">{t.title}</h2>
          <p className="mt-4 text-[15px] leading-[1.6] text-slate-600 sm:mt-5 sm:text-base sm:leading-7">{t.text}</p>
        </Reveal>

        <Reveal delay={0.1} className="mt-8 sm:mt-12">
          <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-slate-950 p-2 shadow-2xl shadow-slate-900/20">
            <div className="overflow-hidden rounded-[21px] bg-slate-50">
              <div className="flex h-11 items-center gap-2 border-b border-slate-200 bg-white px-4">
                <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
                <div className="ml-3 truncate rounded-md bg-slate-100 px-3 py-1 text-xs font-medium text-slate-400">
                  radix-crm.uz/dashboard
                </div>
                <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-slate-400">
                  {t.sample}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-[180px_1fr]">
                <aside className="hidden border-r border-slate-200 bg-white p-4 md:block">
                  <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
                    <span className="grid h-6 w-6 place-items-center rounded-md bg-brand-600 text-[11px] text-white">
                      R
                    </span>
                    Radix CRM
                  </div>
                  <div className="mt-7 space-y-1.5">
                    {t.nav.map((label, index) => (
                      <div
                        key={label}
                        className={cn(
                          'rounded-md px-2.5 py-2 text-xs font-medium',
                          index === 0 ? 'bg-brand-50 text-brand-700' : 'text-slate-400',
                        )}
                      >
                        {label}
                      </div>
                    ))}
                  </div>
                </aside>

                <div className="p-4 sm:p-6 lg:p-8">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xl font-bold tracking-tight text-slate-900">{t.live}</p>
                      <p className="mt-1 text-xs text-slate-400">Radix CRM</p>
                    </div>
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
                      ● {t.active}
                    </span>
                  </div>

                  <div className="mt-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
                    {metrics.map(([label, value, color]) => (
                      <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
                        <span className={cn('inline-grid h-8 w-8 place-items-center rounded-lg text-xs', color)}>
                          ●
                        </span>
                        <p className="mt-3 text-xs font-medium text-slate-400">{label}</p>
                        <p className="mt-1 text-base font-bold tabular-nums text-slate-900 sm:text-lg">
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
                    <div className="rounded-xl border border-slate-200 bg-white p-5">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-bold text-slate-800">{t.finance}</p>
                        <BarChart3 className="h-4 w-4 text-brand-600" />
                      </div>
                      <div className="mt-6 flex h-36 items-end gap-2.5">
                        {BARS.map((height, index) => (
                          <span
                            key={index}
                            className={cn(
                              'flex-1 rounded-t',
                              index === BARS.length - 1 ? 'bg-brand-600' : 'bg-brand-100',
                            )}
                            style={{ height: `${height}%` }}
                          />
                        ))}
                      </div>
                    </div>

                    <div className="rounded-xl border border-slate-200 bg-white p-5">
                      <p className="text-sm font-bold text-slate-800">{t.recent}</p>
                      <div className="mt-4 space-y-3.5">
                        {RECENT.map((name) => (
                          <div key={name} className="flex items-center justify-between text-xs">
                            <span className="text-slate-500">{name}</span>
                            <span className="font-semibold tabular-nums text-emerald-700">+ 1 500 000</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
