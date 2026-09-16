/**
 * Vendor xodimi mijoz tizimida ekanini KO'RSATADI (ADR-10).
 *
 * Belgisiz kirish ikki tomondan xavfli: xodim o'zining qaysi tizimda
 * ekanini unutadi, va ekranni mijoz bilan birga ko'rayotgan holatda
 * bog'cha kimning nima qilayotganini bilmaydi. Chiziq ataylab to'q
 * rangda va sahifaning eng tepasida.
 */

import { ShieldAlert } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'

export function SupportSessionBanner() {
  const { isSupportSession, user } = useAuth()
  if (!isSupportSession) return null

  return (
    <div className="flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-center text-sm font-medium text-amber-950">
      <ShieldAlert className="h-4 w-4 flex-none" />
      <span>
        Qo'llab-quvvatlash sessiyasi — <strong>{user?.organization?.name}</strong> tizimidasiz.
        Faqat o'qish: hech narsani o'zgartira olmaysiz.
      </span>
    </div>
  )
}
