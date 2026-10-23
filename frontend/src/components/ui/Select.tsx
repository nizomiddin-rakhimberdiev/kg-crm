/**
 * Tanlagich — native `<select>`, kiyimi bizniki (mijoz eʼtirozi, 2026-10-23).
 *
 * **Nima buzilgan edi.** Ilovada 86 ta `<select>` bor va har biri oʻz
 * klassi bilan yozilgan edi: biri `px-3 py-2`, boshqasi `px-2 py-1`,
 * uchinchisi `h-11`; fokus halqasi baʼzisida bor, baʼzisida yoʻq;
 * strelka esa brauzerniki — Chrome'da bir xil, Safari'da boshqacha,
 * telefonda uchinchi xil. Mijoz buni "umuman standart xolatda emas,
 * oddiy boʻlib qolgan" deb yozdi, va u haq: bitta ekranda uch xil
 * balandlikdagi maydon turardi.
 *
 * **Nega native element qoladi.** `DateInput` dagi bilan bir xil
 * sabab: klaviatura (yuqori/quyi, Home/End), harf bilan qidirish
 * ("g" bosib "Goʻsht" ga sakrash), `optgroup`, skrinrider va
 * telefondagi tizim tanlagichi — bularning hammasi native elementdan
 * BEPUL keladi. Qayta yozilgan roʻyxat ularning har birini yoʻqotadi
 * va uzun roʻyxatda (200 ta bola) sekinroq ham boʻladi.
 *
 * Shuning uchun bu yerda faqat KIYIM: `appearance-none`, oʻz
 * strelkamiz, bitta balandlik, bitta fokus halqasi.
 */

import { forwardRef, type SelectHTMLAttributes } from 'react'
import { ChevronDown, type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  /**
   * `sm` — jadval qatori ichidagi zich tanlagich (36px).
   *
   * Sukut `md` — 40px. Nega 44 emas: yonidagi matn maydonlari
   * `px-3 py-2 text-sm` bilan 38px, va bitta qatorda 44px tanlagich
   * ular ustidan oshib turardi — ya'ni "har xil balandlik" degan
   * shikoyat boshqa shaklda qaytardi. Maydonlar birgalikda
   * kattalashtirilganda bu ham ular bilan birga koʻtariladi.
   */
  size?: 'sm' | 'md'
  /** `dark` — platforma konsoli uchun (u qora fonda ishlaydi). */
  tone?: 'light' | 'dark'
  /** Maydon xato deb belgilangan — chekkasi qizg'ish boʻladi. */
  invalid?: boolean
  /** Chap tomondagi belgi — masalan filial tanlagichidagi bino. */
  icon?: LucideIcon
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { size = 'md', tone = 'light', invalid, icon: Icon, className, children, ...props },
  ref,
) {
  return (
    /*
     * Oʻrash `w-full`: tanlagich ilgari `<select className="w-full">`
     * edi va flex qatorida kenglikni oʻzi olardi. Oʻrash blok element
     * boʻlgani uchun flex BOLASI sifatida u faqat mazmun kengligini
     * olardi — ya'ni maydon qisqarib qolardi. `twMerge` tufayli
     * chaqiruvchining `w-28` yoki `max-w-[180px]` i baribir ustun. */
    <div className={cn('relative w-full', className)}>
      <select
        ref={ref}
        className={cn(
          // `pr-9` — strelka uchun joy; usiz uzun nom uning ostiga kirib ketadi.
          'w-full appearance-none rounded-lg border bg-white pr-9 outline-none transition-colors',
          Icon ? 'pl-9' : 'pl-3',
          size === 'sm' ? 'h-9 text-xs' : 'h-10 text-sm',
          tone === 'dark'
            ? 'border-slate-700 bg-slate-800 text-slate-100 focus:border-nihol-500 focus:ring-2 focus:ring-nihol-500/20'
            : 'border-tosh-200 text-tosh-800 focus:border-nihol-500 focus:ring-2 focus:ring-nihol-500/20',
          invalid && 'border-orik-400 focus:border-orik-500 focus:ring-orik-500/20',
          props.disabled &&
            (tone === 'dark' ? 'opacity-50' : 'cursor-not-allowed bg-tosh-50 text-tosh-500'),
        )}
        {...props}
      >
        {children}
      </select>
      {Icon && (
        <span
          className={cn(
            'pointer-events-none absolute inset-y-0 left-3 flex items-center',
            tone === 'dark' ? 'text-slate-400' : 'text-tosh-500',
            props.disabled && 'opacity-50',
          )}
        >
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      )}
      <span
        className={cn(
          'pointer-events-none absolute inset-y-0 right-3 flex items-center',
          tone === 'dark' ? 'text-slate-400' : 'text-tosh-500',
          props.disabled && 'opacity-50',
        )}
      >
        <ChevronDown className={size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'} aria-hidden />
      </span>
    </div>
  )
})
