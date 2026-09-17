/**
 * Narx kalkulyatori.
 *
 * Raqamlar BACKENDDAN keladi (`/api/v1/public/pricing`), kodda
 * qotirilmaydi. Sabab tarixiy: ADR-12 da narx o'zgarganda kodga yozib
 * qo'yilgan qiymatlar yetti joyda eskirib qolgan edi va ularni testlar
 * ushlagan. Kalkulyator amaldagi `SubscriptionPlan` bilan bir manbadan
 * oziqlanishi shart — aks holda sayt bir narxni, hisob-faktura
 * boshqasini ko'rsatardi.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { marketingApi } from '../api'
import { Reveal } from '../components/Motion'
import { copy, type Locale } from '../content'

// CRM ichidagi `formatUZS()` bu yerga mos emas: u vergul bilan ajratadi
// va "UZS" qo'shadi ("400,000 UZS") — bu ichki boshqaruv panelining
// formati. Public sahifadagi matn (content.ts) esa bo'sh joy bilan
// ajratadi va "so'm"/"сум" so'zini ishlatadi.
const CURRENCY_WORD: Record<Locale, string> = { uz: 'so‘m', ru: 'сум' }
const groupThousands = (value: number) =>
  Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ')

const amount = (value: string | undefined, locale: Locale) =>
  value ? `${groupThousands(Number(value))} ${CURRENCY_WORD[locale]}` : '—'

export function Pricing({ locale }: { locale: Locale }) {
  const t = copy[locale].pricing
  const [children, setChildren] = useState(50)

  const quote = useQuery({
    queryKey: ['public-pricing', children],
    queryFn: () => marketingApi.pricing(children),
    staleTime: 60_000,
  })
  const data = quote.data

  return (
    <section id="pricing" className="scroll-mt-24 bg-slate-950 py-20 text-white lg:py-28">
      <div className="mx-auto grid max-w-7xl gap-12 px-5 lg:grid-cols-[0.9fr_1.1fr] lg:items-end lg:px-8">
        <Reveal>
          <p className="eyebrow !text-brand-300">{t.eyebrow}</p>
          <h2 className="mt-4 text-balance text-3xl font-bold tracking-[-0.035em] sm:text-4xl">
            {t.title}
          </h2>
          <p className="mt-5 max-w-xl leading-7 text-slate-300">{t.text}</p>
          <div className="mt-8 border-l-2 border-brand-400 pl-4 text-sm leading-6 text-slate-300">
            {t.policy}
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="rounded-[28px] bg-white p-5 text-slate-900 shadow-2xl shadow-black/30 sm:p-8">
            <label className="text-sm font-bold" htmlFor="children-count">
              {t.children}
            </label>

            <div className="mt-4 flex items-center gap-4">
              <input
                id="children-count"
                className="w-28 rounded-xl border border-slate-300 px-3 py-2.5 text-lg font-bold tabular-nums outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10"
                type="number"
                min="1"
                max="10000"
                value={children}
                onChange={(event) =>
                  setChildren(Math.max(1, Math.min(10000, Number(event.target.value) || 1)))
                }
              />
              <span className="text-sm text-slate-500">
                {locale === 'uz' ? 'bola' : 'детей'}
              </span>
            </div>

            <input
              className="mt-6 h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-brand-600"
              type="range"
              min="1"
              max="500"
              value={Math.min(children, 500)}
              onChange={(event) => setChildren(Number(event.target.value))}
              aria-label={
                locale === 'uz'
                  ? 'Bolalar sonini slayder bilan sozlash'
                  : 'Настроить количество детей ползунком'
              }
            />

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              <PriceCell
                label={t.monthly}
                value={quote.isLoading ? t.loading : amount(data?.monthly.total_amount, locale)}
              />
              <PriceCell
                label={t.annual}
                value={quote.isLoading ? t.loading : amount(data?.annual.total_amount, locale)}
                highlight
              />
              <PriceCell
                label={t.saving}
                value={quote.isLoading ? t.loading : amount(data?.annual_saving, locale)}
              />
            </div>

            <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-xs text-slate-500">
              <span>{t.before}</span>
              <strong className="tabular-nums text-slate-700">
                {quote.isLoading ? '—' : amount(data?.annual_before_discount, locale)}
              </strong>
            </div>

            {quote.isError && (
              <p role="alert" className="mt-3 text-xs text-red-600">
                {locale === 'uz'
                  ? 'Hisobni yuklab bo‘lmadi. Qayta urinib ko‘ring.'
                  : 'Не удалось загрузить расчёт. Попробуйте ещё раз.'}
              </p>
            )}

            <p className="mt-5 text-xs leading-5 text-slate-400">{t.disclaimer}</p>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function PriceCell({
  label,
  value,
  highlight = false,
}: {
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div
      className={cn(
        'rounded-2xl p-4 transition',
        highlight ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20' : 'bg-slate-50',
      )}
    >
      <p className={cn('text-xs font-medium', highlight ? 'text-brand-100' : 'text-slate-500')}>
        {label}
      </p>
      <p className="mt-2 text-lg font-bold tracking-tight tabular-nums">{value}</p>
    </div>
  )
}
