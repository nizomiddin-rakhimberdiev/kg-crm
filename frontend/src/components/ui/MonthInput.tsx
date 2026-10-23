/**
 * Oy maydoni — «Oktabr 2026» (audit, 2026-10-21).
 *
 * Nega native `input[type=month]` emas: u oy nomini **brauzer lokali**
 * bo'yicha chiqaradi. Interfeys o'zbekcha turganda tanlagichda
 * "October 2026" yozilardi — mijoz buni auditda yozib qoldirdi. Bu
 * `DateInput` bilan bir xil savol (Q12) va javobi ham bir xil:
 * ko'rinish bizda bo'lsin.
 *
 * Ikkita tanlagich, bitta `<label>`: oy nomi bilan, yil raqam bilan.
 * Klaviatura va skrinrider native `<Select>` dan tekin keladi — oyni
 * qaytadan yozilgan kalendar bu kafolatni yo'qotardi.
 *
 * **Shartnoma `value`/`onChange` da `yyyy-mm`** — API va baza shu
 * formatda ishlaydi.
 */

import { monthName } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { Select } from '@/components/ui/Select'

interface Props {
  /** `yyyy-mm`. */
  value: string
  onChange: (value: string) => void
  /** Koʻrinadigan yorliq — maydon yorliqsiz qolmaydi (05 §17.2). */
  label: string
  id?: string
  /** `yyyy-mm` chegaralar — chegaradan tashqaridagi oy tanlanmaydi. */
  min?: string
  max?: string
  disabled?: boolean
  className?: string
  tone?: 'light' | 'dark'
}

const MONTHS = Array.from({ length: 12 }, (_, index) => index + 1)

/** `yyyy-mm` → 2026 * 12 + 10: ikki davrni solishtirish uchun. */
function ordinal(period: string | undefined): number | null {
  const match = /^(\d{4})-(\d{1,2})$/.exec(period ?? '')
  if (!match) return null
  return Number(match[1]) * 12 + Number(match[2])
}

export function MonthInput({
  value,
  onChange,
  label,
  id,
  min,
  max,
  disabled,
  className,
  tone = 'light',
}: Props) {
  const match = /^(\d{4})-(\d{2})$/.exec(value)
  const now = new Date()
  const year = match ? Number(match[1]) : now.getFullYear()
  const month = match ? Number(match[2]) : now.getMonth() + 1

  const lower = ordinal(min)
  const upper = ordinal(max)
  const minYear = min ? Number(min.slice(0, 4)) : Math.min(year, now.getFullYear() - 5)
  const maxYear = max ? Number(max.slice(0, 4)) : Math.max(year, now.getFullYear() + 1)
  const years: number[] = []
  for (let candidate = minYear; candidate <= maxYear; candidate += 1) years.push(candidate)

  const outside = (candidateYear: number, candidateMonth: number) => {
    const point = candidateYear * 12 + candidateMonth
    return (lower !== null && point < lower) || (upper !== null && point > upper)
  }

  const monthId = id ?? 'month-input'

  return (
    <div className={cn('flex items-end gap-2', className)}>
      <div>
        <label
          htmlFor={monthId}
          className={cn(
            'mb-1 block text-xs font-medium',
            tone === 'dark' ? 'text-slate-400' : 'text-tosh-600',
          )}
        >
          {label}
        </label>
        <Select
          id={monthId}
          tone={tone}
          value={String(month)}
          disabled={disabled}
          onChange={(event) => onChange(`${year}-${event.target.value.padStart(2, '0')}`)}
        >
          {MONTHS.map((candidate) => (
            <option key={candidate} value={String(candidate)} disabled={outside(year, candidate)}>
              {monthName(candidate)}
            </option>
          ))}
        </Select>
      </div>
      <Select
        aria-label={t('Yil')}
        tone={tone}
        value={String(year)}
        disabled={disabled}
        onChange={(event) => onChange(`${event.target.value}-${String(month).padStart(2, '0')}`)}
      >
        {years.map((candidate) => (
          <option key={candidate} value={String(candidate)}>
            {candidate}
          </option>
        ))}
      </Select>
    </div>
  )
}
