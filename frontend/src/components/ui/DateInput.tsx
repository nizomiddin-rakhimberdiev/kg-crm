/**
 * Sana maydoni — `dd.mm.yyyy` (Q12, PLAN 4.1).
 *
 * Nega native `input[type=date]` emas: u sanani **brauzer lokali**
 * bo'yicha ko'rsatadi. Ya'ni bir xodimda `02.10.2026`, boshqasida
 * `10/02/2026` chiqadi — va ikkinchisi oktabrning ikkisini fevralning
 * o'ni deb o'qiydi. Moliyaviy hujjatda bu xato arzon emas: muddati
 * o'tgan faktura muddati kelmagan bo'lib ko'rinadi.
 *
 * Shuning uchun ko'rinish BIZDA: matn maydoni, uch tilda ham
 * `dd.mm.yyyy`. Kalendar esa native qoladi — uni qaytadan yozish
 * klaviatura va skrinriderni buzadigan ish, brauzerning o'zi esa
 * buni yaxshi qiladi.
 *
 * **Shartnoma `value`/`onChange` da ISO (`yyyy-mm-dd`)**, chunki API
 * va baza shu formatda ishlaydi. Ko'rinish — faqat ko'rinish.
 */

import { useEffect, useRef, useState } from 'react'
import { CalendarDays } from 'lucide-react'
import { parseLocalDate, toLocalDate } from '@/lib/format'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

interface Props {
  /** ISO `yyyy-mm-dd` yoki bo'sh satr. */
  value: string
  onChange: (iso: string) => void
  id?: string
  name?: string
  required?: boolean
  disabled?: boolean
  /** ISO chegaralar — native kalendar uchun ham ishlatiladi. */
  min?: string
  max?: string
  className?: string
  /**
   * `dark` — platforma konsoli uchun (u qora fonda ishlaydi).
   *
   * Konsol uchun alohida komponent yozish ikkita ta'rif yaratardi va
   * ular ertami-kechmi ajralib ketardi; bitta bayroq esa arzon.
   */
  tone?: 'light' | 'dark'
  'aria-label'?: string
  'aria-describedby'?: string
}

/** Yozilayotgan matnga nuqtalarni o'zi qo'yadi: `02102026` → `02.10.2026`. */
function withDots(input: string): string {
  const digits = input.replace(/\D/g, '').slice(0, 8)
  const parts = [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4, 8)].filter(Boolean)
  return parts.join('.')
}

export function DateInput({
  value,
  onChange,
  id,
  name,
  required,
  disabled,
  min,
  max,
  className,
  tone = 'light',
  ...aria
}: Props) {
  const [text, setText] = useState(() => toLocalDate(value))
  const native = useRef<HTMLInputElement>(null)

  // Tashqaridan kelgan qiymat o'zgarsa (forma tozalandi, boshqa yozuv
  // ochildi) ko'rinish ham yangilanadi.
  useEffect(() => {
    setText(toLocalDate(value))
  }, [value])

  const handleText = (raw: string) => {
    const next = withDots(raw)
    setText(next)
    if (next === '') {
      onChange('')
      return
    }
    const iso = parseLocalDate(next)
    if (iso) onChange(iso)
  }

  const handleBlur = () => {
    // Yarim yozilgan sana maydonda QOLMAYDI: u keyin jimgina
    // yuborilib, boshqa sanaga aylanib ketishi mumkin.
    if (text === '') return
    if (!parseLocalDate(text)) setText(toLocalDate(value))
  }

  const openCalendar = () => {
    const element = native.current
    if (!element) return
    // `showPicker()` — Chrome/Edge/Safari. Qo'llab-quvvatlamagan
    // brauzerda maydonning o'zi bosiladi va brauzer o'z kalendarini
    // ochadi; hech qanday holatda xato chiqmaydi.
    if (typeof element.showPicker === 'function') {
      try {
        element.showPicker()
        return
      } catch {
        // Foydalanuvchi harakatidan tashqarida chaqirilsa istisno
        // bo'ladi — o'shanda oddiy fokus qoladi.
      }
    }
    element.focus()
    element.click()
  }

  const invalid = text !== '' && !parseLocalDate(text)

  return (
    <div className={cn('relative', className)}>
      <input
        id={id}
        name={name}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        placeholder={t('kk.oo.yyyy')}
        required={required}
        disabled={disabled}
        value={text}
        aria-invalid={invalid || undefined}
        onChange={(event) => handleText(event.target.value)}
        onBlur={handleBlur}
        className={cn(
          'w-full rounded-lg border px-3 py-2 pr-9 text-sm outline-none',
          tone === 'dark'
            ? 'border-slate-700 bg-slate-800 text-slate-100 placeholder:text-slate-500 focus:border-nihol-500'
            : 'bg-white',
          invalid
            ? 'border-orik-400'
            : tone === 'light' && 'border-tosh-200 focus:border-nihol-500',
          disabled && (tone === 'dark' ? 'opacity-50' : 'bg-tosh-50 text-tosh-400'),
        )}
        {...aria}
      />
      <button
        type="button"
        onClick={openCalendar}
        disabled={disabled}
        aria-label={t('Kalendardan tanlash')}
        title={t('Kalendardan tanlash')}
        className={cn(
          'absolute right-1 top-1/2 -translate-y-1/2 rounded-md p-1.5 disabled:opacity-40',
          tone === 'dark'
            ? 'text-slate-400 hover:bg-slate-700 hover:text-slate-100'
            : 'text-tosh-400 hover:bg-tosh-50 hover:text-tosh-700',
        )}
      >
        <CalendarDays className="h-4 w-4" />
      </button>
      {/* Kalendar — native. Ko'rinmaydi, lekin ekranda turadi:
          `display:none` bo'lsa `showPicker()` ishlamaydi. */}
      <input
        ref={native}
        type="date"
        tabIndex={-1}
        aria-hidden="true"
        value={value}
        min={min}
        max={max}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="pointer-events-none absolute bottom-0 right-2 h-0 w-0 opacity-0"
      />
    </div>
  )
}
