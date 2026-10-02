/**
 * Ish kunlari — katakchalar, "1,2,3,4,5" emas (PLAN 4.2).
 *
 * Auditda bu sozlama erkin matn maydoni edi va ekranda `1,2,3,4,5`
 * deb turardi. Mudira bu raqamlar nimani bildirishini bilishi kerak
 * emas — va bitta xato belgi (`6` oʻrniga `0`) kunlik toʻlov hisobini
 * jimgina buzadi (ADR-19: kun narxi ish kunlari soniga boʻlinadi).
 *
 * Saqlanadigan shakl oʻzgarmaydi — ISO raqamlar vergul bilan
 * (1 = dushanba … 7 = yakshanba), yaʼni backend va migratsiyalar
 * tegilmaydi.
 */

import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'

/** ISO raqam + qisqa nom. Dushanbadan boshlanadi — mahalliy hafta shunday. */
const DAYS: Array<[number, string]> = [
  [1, t('Du')],
  [2, t('Se')],
  [3, t('Ch')],
  [4, t('Pa')],
  [5, t('Ju')],
  [6, t('Sh')],
  [7, t('Ya')],
]

const FULL: Record<number, string> = {
  1: t('Dushanba'),
  2: t('Seshanba'),
  3: t('Chorshanba'),
  4: t('Payshanba'),
  5: t('Juma'),
  6: t('Shanba'),
  7: t('Yakshanba'),
}

export function parseWeekdays(value: unknown): number[] {
  return String(value ?? '')
    .split(',')
    .map((part) => Number(part.trim()))
    .filter((day) => Number.isInteger(day) && day >= 1 && day <= 7)
}

export function formatWeekdays(days: number[]): string {
  return [...new Set(days)].sort((a, b) => a - b).join(',')
}

interface Props {
  value: unknown
  disabled?: boolean
  onChange: (next: string) => void
}

export function WeekdayPicker({ value, disabled, onChange }: Props) {
  const selected = parseWeekdays(value)

  const toggle = (day: number) => {
    const next = selected.includes(day)
      ? selected.filter((item) => item !== day)
      : [...selected, day]
    // Hamma kun olib tashlanmasin: ish kuni nol boʻlsa kunlik toʻlov
    // nolga boʻlinadi va hisob umuman ishlamay qoladi.
    if (next.length === 0) return
    onChange(formatWeekdays(next))
  }

  return (
    <div className="flex flex-wrap gap-1">
      {DAYS.map(([day, short]) => {
        const active = selected.includes(day)
        return (
          <label
            key={day}
            title={FULL[day]}
            className={cn(
              'cursor-pointer rounded-lg border px-2.5 py-1.5 text-xs font-medium transition',
              active
                ? 'border-nihol-500 bg-nihol-50 text-nihol-800'
                : 'border-tosh-200 text-tosh-500 hover:bg-tosh-50',
              disabled && 'cursor-not-allowed opacity-50',
            )}
          >
            <input
              type="checkbox"
              className="sr-only"
              checked={active}
              disabled={disabled}
              onChange={() => toggle(day)}
              aria-label={FULL[day]}
            />
            {short}
          </label>
        )
      })}
    </div>
  )
}
