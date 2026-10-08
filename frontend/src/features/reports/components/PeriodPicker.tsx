/**
 * Davr tanlagich: Kun · Hafta · Oy · Chorak · Yil · Ixtiyoriy, va
 * tanlangan davr bo'ylab ◀ ▶ yurish.
 *
 * Direktor "bu oy" yoki "o'tgan chorak" deb o'ylaydi, "2026-07-01 dan
 * 2026-09-30 gacha" deb emas. Sana maydonlari faqat "Ixtiyoriy" da
 * ochiladi — qolgan hollarda ular shovqin.
 */

import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react'
import { DateInput } from '@/components/ui/DateInput'
import { cn } from '@/lib/utils'
import {
  PRESETS,
  periodFor,
  periodLabel,
  shiftPeriod,
  toISODate,
  type Period,
  type PeriodPreset,
} from '../period'
import { t } from '@/lib/i18n'

interface PeriodPickerProps {
  value: Period
  onChange: (period: Period) => void
  className?: string
}

export function PeriodPicker({ value, onChange, className }: PeriodPickerProps) {
  const today = new Date()
  const isCustom = value.preset === 'custom'
  // Kelajakka o'tish ma'nosiz: u yerda hali ma'lumot yo'q.
  const next = shiftPeriod(value, 1)
  const canGoForward = next.from <= toISODate(today)

  const pick = (preset: PeriodPreset) => {
    if (preset === 'custom') {
      onChange({ preset, from: value.from, to: value.to })
      return
    }
    // Yangi preset joriy davr ichidagi sanaga qarab: oydan haftaga
    // o'tilsa, o'sha oyning emas, bugungi hafta ochiladi — foydalanuvchi
    // ko'pincha "hozir"ni ko'rmoqchi.
    const anchor =
      value.from <= toISODate(today) && toISODate(today) <= value.to ? today : new Date(value.from)
    onChange(periodFor(preset, anchor))
  }

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      {/* Preset'lar — telefonda gorizontal skroll, ekranni sig'dirmaydi */}
      <div className="-mx-3 overflow-x-auto px-3 sm:mx-0 sm:px-0">
        <div
          role="tablist"
          aria-label={t('Davr turi')}
          className="inline-flex min-w-max rounded-lg border border-slate-200 bg-slate-50 p-1"
        >
          {PRESETS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={value.preset === key}
              onClick={() => pick(key)}
              className={cn(
                'rounded-md px-3 py-1.5 text-sm font-medium transition',
                value.preset === key
                  ? 'bg-white text-brand-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-800',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onChange(shiftPeriod(value, -1))}
            aria-label={t('Oldingi davr')}
            className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50 active:scale-90"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <p className="min-w-[10rem] px-2 text-center text-sm font-semibold text-slate-800 tabular-nums">
            {periodLabel(value)}
          </p>
          <button
            type="button"
            onClick={() => onChange(next)}
            disabled={!canGoForward}
            aria-label={t('Keyingi davr')}
            className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50 active:scale-90 disabled:opacity-40 disabled:active:scale-100"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {!isCustom && (
          <button
            type="button"
            onClick={() => onChange(periodFor(value.preset, today))}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
          >
            <CalendarDays className="h-3.5 w-3.5 text-slate-500" />
            {t('Bugun')}
          </button>
        )}

        {isCustom && (
          <div className="flex flex-wrap items-center gap-2">
            <DateInput
              aria-label={t('Dan')}
              value={value.from}
              max={value.to}
              onChange={(iso) => iso && onChange({ ...value, from: iso })}
            />
            <span className="text-slate-500">—</span>
            <DateInput
              aria-label={t('Gacha')}
              value={value.to}
              min={value.from}
              max={toISODate(today)}
              onChange={(iso) => iso && onChange({ ...value, to: iso })}
            />
          </div>
        )}
      </div>
    </div>
  )
}
