/**
 * Bogʻchaning belgisi — logotip yoki bosh harf (PLAN 4.6).
 *
 * Mudira kun boʻyi OʻZ bogʻchasining belgisini koʻrib turishi kerak,
 * umumiy qalpoq ikonkasi emas: ilova uning ishxonasi, bizning
 * mahsulotimiz namoyishi emas.
 *
 * Logotip YUKLASH shart emas. Boʻsh boʻlsa bosh harf koʻrsatiladi va
 * uning rangi nomdan barqaror tanlanadi (`avatarTone`) — yaʼni
 * bogʻcha har safar bir xil rangda koʻrinadi va ekranda hech qanday
 * boʻsh joy qolmaydi.
 */

import { RadixMark } from '@/components/brand/Logo'
import { avatarTone, cn, initials } from '@/lib/utils'

interface Props {
  name?: string | null
  logoUrl?: string | null
  size?: number
  className?: string
}

export function OrgMark({ name, logoUrl, size = 36, className }: Props) {
  if (logoUrl) {
    return (
      <img
        src={logoUrl}
        alt={name ?? ''}
        width={size}
        height={size}
        // `object-contain`: logotip kvadrat boʻlmasligi mumkin va
        // `cover` uni kesib tashlardi — bogʻchaning belgisi kesilgan
        // holda koʻrinishi yaxshi taassurot bermaydi.
        className={cn('shrink-0 rounded-lg object-contain', className)}
        style={{ width: size, height: size }}
      />
    )
  }

  if (!name) {
    // Bogʻcha nomi hali yoʻq (login, yuklanish) — mahsulot belgisi.
    return <RadixMark size={size} className={cn('shrink-0', className)} />
  }

  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex shrink-0 items-center justify-center rounded-lg font-bold',
        avatarTone(name),
        className,
      )}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.42) }}
    >
      {initials(name)}
    </span>
  )
}
