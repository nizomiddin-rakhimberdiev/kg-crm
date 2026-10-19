/**
 * Davr kesimi — hisobotning raqamli qismi.
 *
 * Server davrning HAR BIR kuni (haftasi, oyi) uchun qator qaytaradi, va
 * oddiy jadvalda 31 qatorning 29 tasi "0 0 0" edi: ish boʻlgan ikki kun
 * nollar orasida yoʻqolib ketardi. Endi:
 *
 * - harakatsiz davrlar sukut boʻyicha yashirin, soni aytiladi va bir
 *   bosishda ochiladi;
 * - nol — xira "—", raqam emas: koʻz faqat haqiqiy summaga tushadi;
 * - tushum va chiqim ostida ingichka chiziq — eng katta kun bir qarashda
 *   koʻrinadi (rang yolgʻiz emas: raqam yonida turadi);
 * - sof natija ishora va rang bilan;
 * - kun qisqa yoziladi ("13 okt") va hafta kuni bilan — yil sarlavhada bor.
 */

import { useState } from 'react'
import { ChevronDown, Info } from 'lucide-react'
import type { ReportGroupBy } from '@/lib/api/types'
import { bucketLabel, bucketTitle } from '@/features/reports/period'
import { money, signed } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

export interface PeriodRow {
  period: string
  Tushum: number
  Chiqim: number
  'Oylik maosh': number
  net: number
}

interface Props {
  rows: PeriodRow[]
  groupBy: ReportGroupBy
  showRevenue: boolean
  showExpenses: boolean
  /** Oylik maosh davrlarga taqsimlanganmi (aks holda faqat jami qatorda). */
  payrollInRows: boolean
  showNet: boolean
  totals: { revenue: number; expenses: number; payroll: number; net: number | null }
}

const WEEKDAYS = [t('Ya'), t('Du'), t('Se'), t('Ch'), t('Pa'), t('Ju'), t('Sh')]

function Amount({
  value,
  max,
  tone,
}: {
  value: number
  max: number
  tone: 'revenue' | 'expense' | 'payroll'
}) {
  if (!value) return <span className="text-slate-400">—</span>
  return (
    <div className="flex flex-col items-end gap-1">
      <span className="text-slate-800">{money(value)}</span>
      <span aria-hidden className="block h-1 w-20 overflow-hidden rounded-full bg-slate-100">
        <span
          className={cn(
            'block h-1 rounded-full',
            tone === 'revenue' && 'bg-nihol-500',
            tone === 'expense' && 'bg-orik-400',
            tone === 'payroll' && 'bg-ildiz-500',
          )}
          style={{ width: `${Math.max(4, (Math.abs(value) / max) * 100)}%` }}
        />
      </span>
    </div>
  )
}

function Net({ value, strong = false }: { value: number; strong?: boolean }) {
  if (!value) return <span className="text-slate-400">—</span>
  return (
    <span
      className={cn(
        'inline-block rounded-md px-1.5 py-0.5 tabular-nums',
        strong ? 'font-bold' : 'font-semibold',
        value < 0 ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-800',
      )}
    >
      {signed(value)}
    </span>
  )
}

export function PeriodTable({
  rows,
  groupBy,
  showRevenue,
  showExpenses,
  payrollInRows,
  showNet,
  totals,
}: Props) {
  const [showEmpty, setShowEmpty] = useState(false)
  const active = (row: PeriodRow) =>
    row.Tushum !== 0 || row.Chiqim !== 0 || row['Oylik maosh'] !== 0
  const emptyCount = rows.filter((row) => !active(row)).length
  const visible = showEmpty ? rows : rows.filter(active)
  const max = Math.max(
    1,
    ...visible.flatMap((row) => [Math.abs(row.Tushum), Math.abs(row.Chiqim), row['Oylik maosh']]),
  )

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{t('Davr kesimi')}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t('Harakat boʻlgan davrlar: {active} / {total}', {
              active: rows.length - emptyCount,
              total: rows.length,
            })}
          </p>
        </div>
        {showNet && !payrollInRows && (
          <p className="flex items-center gap-1.5 text-xs text-slate-500">
            <Info className="h-3.5 w-3.5" aria-hidden />
            {t('Oylik maosh faqat jami qatorda')}
          </p>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-sm">
          <thead className="text-left text-xs text-slate-500">
            <tr className="border-b border-slate-100">
              <th className="px-4 py-2 font-medium">{t('Davr')}</th>
              {showRevenue && <th className="px-4 py-2 text-right font-medium">{t('Tushum')}</th>}
              {showExpenses && <th className="px-4 py-2 text-right font-medium">{t('Chiqim')}</th>}
              {payrollInRows && (
                <th className="px-4 py-2 text-right font-medium">{t('Oylik maosh')}</th>
              )}
              {showNet && <th className="px-4 py-2 text-right font-medium">{t('Sof natija')}</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 tabular-nums">
            {visible.map((row) => {
              const date = new Date(`${row.period}T00:00:00`)
              return (
                <tr
                  key={row.period}
                  className={cn(
                    'transition-colors hover:bg-slate-50',
                    !active(row) && 'text-slate-400',
                  )}
                >
                  <td
                    className="whitespace-nowrap px-4 py-2.5"
                    title={bucketTitle(row.period, groupBy)}
                  >
                    <span className="font-medium text-slate-800">
                      {bucketLabel(row.period, groupBy)}
                    </span>
                    {groupBy === 'day' && (
                      <span className="ml-2 text-xs text-slate-500">{WEEKDAYS[date.getDay()]}</span>
                    )}
                  </td>
                  {showRevenue && (
                    <td className="px-4 py-2.5 text-right">
                      <Amount value={row.Tushum} max={max} tone="revenue" />
                    </td>
                  )}
                  {showExpenses && (
                    <td className="px-4 py-2.5 text-right">
                      <Amount value={row.Chiqim} max={max} tone="expense" />
                    </td>
                  )}
                  {payrollInRows && (
                    <td className="px-4 py-2.5 text-right">
                      <Amount value={row['Oylik maosh']} max={max} tone="payroll" />
                    </td>
                  )}
                  {showNet && (
                    <td className="px-4 py-2.5 text-right">
                      <Net value={row.net} />
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
          <tfoot className="border-t-2 border-slate-200 bg-slate-50/70 tabular-nums">
            <tr>
              <td className="px-4 py-3 font-semibold text-slate-900">{t('Jami')}</td>
              {showRevenue && (
                <td className="px-4 py-3 text-right font-semibold text-slate-900">
                  {money(totals.revenue)}
                </td>
              )}
              {showExpenses && (
                <td className="px-4 py-3 text-right font-semibold text-slate-900">
                  {money(totals.expenses)}
                </td>
              )}
              {payrollInRows && (
                <td className="px-4 py-3 text-right font-semibold text-slate-900">
                  {money(totals.payroll)}
                </td>
              )}
              {showNet && totals.net !== null && (
                <td className="px-4 py-3 text-right">
                  <Net value={totals.net} strong />
                  {!payrollInRows && totals.payroll !== 0 && (
                    <span className="mt-0.5 block text-xs text-slate-500">
                      {t('oylik {formatMoney} bilan', { formatMoney: money(totals.payroll) })}
                    </span>
                  )}
                </td>
              )}
            </tr>
          </tfoot>
        </table>
      </div>

      {emptyCount > 0 && (
        <button
          type="button"
          aria-expanded={showEmpty}
          onClick={() => setShowEmpty((value) => !value)}
          className="flex w-full items-center justify-center gap-1.5 border-t border-slate-100 px-4 py-2.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
        >
          <ChevronDown
            className={cn('h-4 w-4 transition-transform', showEmpty && 'rotate-180')}
            aria-hidden
          />
          {showEmpty
            ? t('Harakatsiz davrlarni yashirish')
            : t('Harakatsiz davrlarni ham koʻrsatish ({n})', { n: emptyCount })}
        </button>
      )}
    </section>
  )
}
