/**
 * Ilova tili tanlagichi — UZ · RU · EN.
 *
 * Tanlov brauzerda saqlanadi va sahifa qayta yuklanadi (lib/i18n'dagi
 * izoh): shu narx evaziga tarjima mexanizmi provayder va qayta rendersiz,
 * bitta sof funksiya bo'lib qoladi. Tugmalar `hreflang` emas — bu CRM,
 * qidiruv tizimiga ochiq sahifa emas (public sayt o'z tanlagichiga ega).
 */

import { APP_LOCALES, locale, setLocale, t, type AppLocale } from '@/lib/i18n'
import { cn } from '@/lib/utils'

export function LanguageSwitch({
  className,
  size = 'sm',
}: {
  className?: string
  /** `md` — drawer va login sahifasi uchun kattaroq nishon. */
  size?: 'sm' | 'md'
}) {
  return (
    <div
      role="group"
      aria-label={t('Til')}
      className={cn(
        'inline-flex items-center rounded-lg border border-slate-200 bg-white p-0.5 text-[12px] font-semibold',
        className,
      )}
    >
      {APP_LOCALES.map((item) => (
        <button
          key={item.code}
          type="button"
          lang={item.code}
          title={item.label}
          aria-pressed={item.code === locale}
          onClick={() => setLocale(item.code as AppLocale)}
          className={cn(
            'rounded-md transition-colors',
            size === 'md' ? 'min-h-[40px] px-3 text-sm' : 'px-2 py-1',
            item.code === locale
              ? 'bg-slate-900 text-white'
              : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900',
          )}
        >
          {item.short}
        </button>
      ))}
    </div>
  )
}
