/**
 * Brend belgisi — public sahifalar uchun ko'rinish.
 *
 * Logotipning o'zi `@/components/brand/Logo` da; bu fayl faqat uni
 * sahifa konteksti bilan bog'laydi (o'lcham, och/to'q variant). Ilgari
 * bu yerda vaqtinchalik mark chizilar edi — Brendbuk 1.1 bilan u
 * haqiqiy logotipga almashdi.
 */

import { Logo } from '@/components/brand/Logo'

export function Brand({
  className = '',
  variant = 'light',
  height = 34,
}: {
  className?: string
  variant?: 'light' | 'dark'
  height?: number
}) {
  return (
    <span className={`inline-flex items-center ${className}`}>
      <Logo height={height} variant={variant} />
    </span>
  )
}
