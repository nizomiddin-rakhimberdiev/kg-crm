/**
 * Bo'sh ro'yxat holati (P3-002).
 *
 * Yangi bog'cha tizimga birinchi marta kirganda deyarli HAMMA ekran
 * bo'sh bo'ladi. Bo'm-bo'sh jadval ikki xil o'qiladi: "hali hech narsa
 * kiritilmagan" va "nimadir buzilgan" — va foydalanuvchi ikkinchisiga
 * ko'proq moyil, chunki yangi tizimga ishonch hali yo'q.
 *
 * Shuning uchun har bir bo'sh ro'yxat uch narsani aytadi: nima yo'q,
 * nega yo'q bo'lishi normal, va keyingi qadam nima. Uchinchisi eng
 * muhimi — "Bolalar yo'q" jumlasi foydalanuvchini hech qayerga olib
 * bormaydi, "Birinchi bolani qo'shing" esa olib boradi.
 */

import type { LucideIcon } from 'lucide-react'
import { Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  /** Nima yo'q — qisqa, tinch ohangda. */
  title: string
  /** Nega normal va keyin nima qilish kerak. */
  hint?: string
  icon?: LucideIcon
  /** Keyingi qadam — masalan "Bola qo'shish" tugmasi. */
  action?: React.ReactNode
  className?: string
}

export function EmptyState({
  title,
  hint,
  icon: Icon = Inbox,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center px-6 py-14 text-center', className)}>
      <div className="grid h-12 w-12 place-items-center rounded-full bg-slate-100">
        <Icon className="h-5 w-5 text-slate-500" />
      </div>
      <p className="mt-4 text-sm font-medium text-slate-700">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-slate-500">{hint}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

/**
 * Jadval ichida ishlatish uchun — ustunlar sonini qamrab oladigan qator.
 *
 * Alohida variant kerak, chunki `<div>` ni `<tbody>` ichiga qo'yib
 * bo'lmaydi: brauzer uni jadvaldan TASHQARIGA ko'chiradi va natija
 * jadval ostida osilib qolgan matn bo'ladi.
 */
export function EmptyRow({ colSpan, ...props }: EmptyStateProps & { colSpan: number }) {
  return (
    <tr>
      <td colSpan={colSpan} className="p-0">
        <EmptyState {...props} />
      </td>
    </tr>
  )
}
