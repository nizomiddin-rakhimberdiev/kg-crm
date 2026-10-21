/**
 * Maydon yorligʻi — majburiyligi KOʻRINADI (audit, 2026-10-21).
 *
 * "Bizni qayerdan eshitgan?" maydoni majburiy edi, lekin ekranda buni
 * aytadigan hech narsa yo'q edi: xodim formani yuborardi, u
 * yuborilmasdi va nega yuborilmaganini brauzerning inglizcha xabari
 * aytardi. Yulduzcha — eng arzon javob, lekin u FAQAT ko'z uchun:
 * skrinrider uchun maydonning o'zida `required` turadi, shuning uchun
 * yulduzcha `aria-hidden`.
 */

import { cn } from '@/lib/utils'

interface Props {
  htmlFor: string
  children: React.ReactNode
  required?: boolean
  className?: string
}

export function FieldLabel({ htmlFor, children, required, className }: Props) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn('mb-1 block text-xs font-medium text-slate-600', className)}
    >
      {children}
      {required && (
        <span aria-hidden className="ml-0.5 text-red-500">
          *
        </span>
      )}
    </label>
  )
}
