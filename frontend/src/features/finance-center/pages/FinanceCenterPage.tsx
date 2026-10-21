/**
 * Moliya markazi (Bosqich 13.4, brif §5.1–5.2, §7).
 *
 * Uchta koʻrinish, avval mobil uchun:
 * - **Bugun** — egasining oltita doimiy savoliga oltita karta: raqam,
 *   holat rangi, bir qatorlik izoh; bosilsa — tafsilot sahifasi.
 * - **Kun** — bugungi tushum usullar boʻyicha, xarajatlar, sanoq,
 *   topshirishlar, yangi qarzlar, "Diqqat".
 * - **Nazorat** — tekshiruvlar (yashil/qizil) va "Diqqat" roʻyxati, avval
 *   jiddiylari.
 *
 * Raqamlar serverdan: karta va hisobot bir xil funksiyani oʻqiydi.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Info, MinusCircle, XCircle } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { DateInput } from '@/components/ui/DateInput'
import { QueryError } from '@/components/ui/QueryError'
import {
  reportsApi,
  type AttentionItem,
  type CardStatus,
  type HomeCard,
} from '@/features/dashboard/api'
import { MonthlyPack } from '@/features/finance-center/components/MonthlyPack'
import { PlanTab } from '@/features/finance-center/components/PlanTab'
import { TaxTab } from '@/features/finance-center/components/TaxTab'
import { paymentMethodLabel } from '@/features/payments/methods'
import { formatDate, som, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { MonthInput } from '@/components/ui/MonthInput'

type Tab = 'today' | 'day' | 'control' | 'pack' | 'plan' | 'tax'

const STATUS_STYLE: Record<CardStatus, string> = {
  ok: 'border-l-emerald-500',
  warning: 'border-l-orik-500',
  critical: 'border-l-red-500',
}

const STATUS_DOT: Record<CardStatus, string> = {
  ok: 'bg-emerald-500',
  warning: 'bg-orik-500',
  critical: 'bg-red-500',
}

const CARD_LINK: Record<HomeCard['key'], string> = {
  money: '/cash',
  debts: '/debtors',
  spending: '/expenses',
  profit: '/reports',
  checks: '/finance?tab=control',
  growth: '/children',
}

/** Har kartaning taʼrifi — (i) belgisida (brif §6). */
const DEFINITION: Record<HomeCard['key'], string> = {
  money: t('Naqd kassa + bank (tushgan) + yoʻldagi pul, bugungi holat.'),
  debts: t('Ota-onalar qarzi — bolalar jurnalidagi musbat qoldiqlar yigʻindisi.'),
  spending: t('Shu oy tasdiqlangan xarajatlar; solishtirma — oʻtgan oyning shu kunigacha.'),
  profit: t('Operatsion foyda = daromad − tegishli oy xarajatlari, oylik va amortizatsiya.'),
  checks: t('Qizil tekshiruvlar va "Diqqat" holatlari soni.'),
  growth: t('Faol bolalar; bandlik = faol bolalar ÷ guruhlar sigʻimi.'),
}

function cardValue(card: HomeCard): string {
  if (card.key === 'checks' || card.key === 'growth') return String(card.value)
  return som(card.value)
}

function TodayTab() {
  const organizationId = useOrganizationId()
  const home = useQuery({
    queryKey: ['org', organizationId, 'reports', 'home'],
    queryFn: () => reportsApi.home(),
  })
  if (home.isError) return <QueryError error={home.error} onRetry={() => void home.refetch()} />
  const data = home.data
  if (!data) return null
  return (
    <div className="space-y-4">
      {data.all_clear && (
        <p className="flex items-center gap-2 rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800">
          <CheckCircle2 className="h-5 w-5" />
          {t('Hammasi joyida')}
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {data.cards.map((card) => (
          <Link
            key={card.key}
            to={CARD_LINK[card.key]}
            className={cn(
              'block rounded-2xl border border-l-4 border-slate-200 bg-white p-4 transition hover:border-slate-300',
              STATUS_STYLE[card.status],
            )}
          >
            <p className="flex items-center justify-between gap-2 text-sm font-medium text-slate-600">
              {card.title}
              <span
                title={DEFINITION[card.key]}
                aria-label={DEFINITION[card.key]}
                className="text-slate-400"
              >
                <Info className="h-4 w-4" />
              </span>
            </p>
            <p className="mt-1 flex items-center gap-2 text-2xl font-bold tabular-nums text-slate-900">
              <span className={cn('h-2.5 w-2.5 rounded-full', STATUS_DOT[card.status])} />
              {cardValue(card)}
              {card.key === 'growth' && card.occupancy !== null && card.occupancy !== undefined && (
                <span className="text-sm font-medium text-slate-500">
                  {t('bandlik {p}%', { p: card.occupancy })}
                </span>
              )}
            </p>
            <p className="mt-1 text-sm text-slate-600">{card.note}</p>
            {card.detail && (
              <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
                <div>
                  <dt className="text-slate-500">{t('Naqd')}</dt>
                  <dd className="font-semibold tabular-nums">{som(card.detail.cash)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('Bank')}</dt>
                  <dd className="font-semibold tabular-nums">{som(card.detail.bank)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{t('Yoʻlda')}</dt>
                  <dd className="font-semibold tabular-nums">{som(card.detail.in_transit)}</dd>
                </div>
              </dl>
            )}
            {card.top && card.top.length > 0 && (
              <ul className="mt-2 space-y-0.5 text-xs text-slate-600">
                {card.top.map((row) => (
                  <li key={row.category} className="flex justify-between gap-2">
                    <span className="truncate">{row.category}</span>
                    <span className="tabular-nums">{som(row.total)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Link>
        ))}
      </div>
    </div>
  )
}

const SEVERITY_ICON = {
  critical: <XCircle className="h-4 w-4 text-red-600" />,
  warning: <AlertTriangle className="h-4 w-4 text-orik-600" />,
  info: <Info className="h-4 w-4 text-slate-500" />,
}

function AttentionList({ items }: { items: AttentionItem[] }) {
  if (items.length === 0)
    return <p className="text-sm text-slate-500">{t('Gʻayrioddiy holat yoʻq.')}</p>
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((item, index) => (
        <li key={`${item.rule}-${index}`} className="flex gap-2 py-2 text-sm">
          <span className="mt-0.5 shrink-0">{SEVERITY_ICON[item.severity]}</span>
          <span className="min-w-0 flex-1">
            <span className="block font-medium text-slate-900">{item.title}</span>
            <span className="text-slate-600">{item.message}</span>
          </span>
          {item.link && (
            <Link to={item.link} className="shrink-0 text-xs font-medium text-brand-700">
              {t('Ochish')}
            </Link>
          )}
        </li>
      ))}
    </ul>
  )
}

function DayTab() {
  const organizationId = useOrganizationId()
  const [day, setDay] = useState(today())
  const daily = useQuery({
    queryKey: ['org', organizationId, 'reports', 'daily', day],
    queryFn: () => reportsApi.daily(day),
  })
  const data = daily.data
  return (
    <div className="space-y-4">
      <div className="max-w-[12rem]">
        <label htmlFor="day-date" className="mb-1 block text-xs font-medium text-slate-600">
          {t('Kun')}
        </label>
        <DateInput id="day-date" value={day} onChange={(iso) => setDay(iso || today())} />
      </div>
      {daily.isError && <QueryError error={daily.error} onRetry={() => void daily.refetch()} />}
      {data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-200 bg-white p-4">
            <h2 className="flex justify-between text-sm font-semibold text-slate-900">
              {t('Tushum')}
              <span className="tabular-nums">{som(data.receipts.total)}</span>
            </h2>
            <ul className="mt-2 space-y-1 text-sm">
              {data.receipts.by_method.map((row) => (
                <li key={row.method} className="flex justify-between">
                  <span className="text-slate-600">{paymentMethodLabel(row.method)}</span>
                  <span className="tabular-nums">{som(row.total)}</span>
                </li>
              ))}
            </ul>
            {data.new_debts.count > 0 && (
              <p className="mt-2 text-xs text-orik-700">
                {t('Yangi qarzlar: {n} ta, {money}', {
                  n: data.new_debts.count,
                  money: som(data.new_debts.total),
                })}
              </p>
            )}
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-4">
            <h2 className="flex justify-between text-sm font-semibold text-slate-900">
              {t('Chiqimlar')}
              <span className="tabular-nums">{som(data.expenses.total)}</span>
            </h2>
            <ul className="mt-2 divide-y divide-slate-100 text-sm">
              {data.expenses.items.map((row) => (
                <li key={row.id} className="flex justify-between gap-2 py-1.5">
                  <span className="min-w-0 truncate text-slate-700">
                    {row.category}
                    {row.description && (
                      <span className="text-slate-500"> — {row.description}</span>
                    )}
                    {!row.has_receipt && (
                      <span className="ml-1 text-xs text-orik-700">{t('chek yoʻq')}</span>
                    )}
                  </span>
                  <span className="shrink-0 tabular-nums">{som(row.amount)}</span>
                </li>
              ))}
            </ul>
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-slate-900">{t('Kassa va topshirish')}</h2>
            {data.counts.length === 0 && data.handovers.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">{t('Bu kun kassa yopilmagan.')}</p>
            ) : (
              <ul className="mt-2 space-y-1 text-sm">
                {data.counts.map((row, index) => (
                  <li key={`c-${index}`} className="flex justify-between gap-2">
                    <span className="text-slate-600">
                      {row.pot} — {t('sanoq')}
                    </span>
                    <span
                      className={cn(
                        'tabular-nums',
                        Number(row.difference) < 0 ? 'text-red-700' : 'text-slate-900',
                      )}
                    >
                      {Number(row.difference) === 0 ? t('Toʻgʻri') : som(row.difference)}
                    </span>
                  </li>
                ))}
                {data.handovers.map((row, index) => (
                  <li key={`h-${index}`} className="flex justify-between gap-2">
                    <span className="text-slate-600">
                      {row.from} → {row.to}
                    </span>
                    <span className="tabular-nums">{som(row.amount)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="rounded-2xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold text-slate-900">{t('Diqqat')}</h2>
            <div className="mt-1">
              <AttentionList items={data.attention} />
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

function ControlTab() {
  const organizationId = useOrganizationId()
  const [period, setPeriod] = useState(today().slice(0, 7))
  const [year, month] = period.split('-').map(Number)
  const checks = useQuery({
    queryKey: ['org', organizationId, 'reports', 'checks', period],
    queryFn: () => reportsApi.checks(year, month),
  })
  const attention = useQuery({
    queryKey: ['org', organizationId, 'reports', 'attention', period],
    queryFn: () => reportsApi.attention(year, month),
  })
  return (
    <div className="space-y-4">
      <MonthInput id="control-month" label={t('Oy')} value={period} onChange={setPeriod} />
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">{t('Tekshiruvlar')}</h2>
          <ul className="mt-2 divide-y divide-slate-100 text-sm">
            {(checks.data ?? []).map((row) => (
              <li key={row.id} className="flex items-start gap-2 py-2">
                {row.status === 'ok' ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                ) : row.status === 'fail' ? (
                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
                ) : (
                  <MinusCircle className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                )}
                <span className="min-w-0 flex-1">
                  <span className="block text-slate-900">{row.title}</span>
                  {row.detail && <span className="text-xs text-slate-600">{row.detail}</span>}
                </span>
                {row.link && row.status === 'fail' && (
                  <Link to={row.link} className="text-xs font-medium text-brand-700">
                    {t('Ochish')}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">
            {t('Diqqat — {n}', { n: attention.data?.count ?? 0 })}
          </h2>
          <div className="mt-1">
            <AttentionList items={attention.data?.items ?? []} />
          </div>
        </section>
      </div>
    </div>
  )
}

export default function FinanceCenterPage() {
  const initial = new URLSearchParams(window.location.search).get('tab')
  const [tab, setTab] = useState<Tab>(
    ['control', 'day', 'pack', 'plan', 'tax'].includes(initial ?? '') ? (initial as Tab) : 'today',
  )
  const tabs: Array<[Tab, string]> = [
    ['today', t('Bugun')],
    ['day', t('Kun')],
    ['control', t('Nazorat')],
    ['pack', t('Oylik hisobot')],
    ['plan', t('Reja va prognoz')],
    ['tax', t('Soliq')],
  ]
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Moliya markazi')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('Pul qayerda, kim qarz, nima gʻayrioddiy — bir qarashda.')}
        </p>
      </div>
      <div
        role="tablist"
        aria-label={t('Moliya markazi')}
        className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1"
      >
        {tabs.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={cn(
              'flex-1 shrink-0 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition',
              tab === key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600',
            )}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'today' && <TodayTab />}
      {tab === 'day' && <DayTab />}
      {tab === 'control' && <ControlTab />}
      {tab === 'pack' && <MonthlyPack />}
      {tab === 'plan' && <PlanTab />}
      {tab === 'tax' && <TaxTab />}
      <p className="text-xs text-slate-500">{formatDate(today())}</p>
    </div>
  )
}
