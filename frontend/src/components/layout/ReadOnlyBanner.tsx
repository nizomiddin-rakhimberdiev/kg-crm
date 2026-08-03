/**
 * Obuna holati bannerlari (docs/03 §20.6).
 *
 * To'lamagan mijozning ma'lumoti HECH QACHON o'chirilmaydi va yashirilmaydi
 * — u faqat o'qish rejimiga o'tadi va o'z moliyaviy tarixini ko'ra oladi.
 */

import { AlertTriangle, Clock } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'

export function SubscriptionBanner() {
  const { subscription } = useAuth()
  if (!subscription) return null

  if (subscription.read_only) {
    return (
      <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-6 py-2.5 text-sm text-amber-900">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span>
          Obuna to'xtatilgan — ma'lumotlarni <strong>ko'rish</strong> mumkin, o'zgartirish
          mumkin emas. Hisobingiz va tariximiz saqlanib turibdi.
        </span>
      </div>
    )
  }

  if (subscription.status === 'trialing') {
    return (
      <div className="flex items-center gap-2 border-b border-brand-200 bg-brand-50 px-6 py-2.5 text-sm text-brand-900">
        <Clock className="h-4 w-4 shrink-0" />
        <span>Sinov davri faol. Yoqmasa — hech qanday to'lov olinmaydi.</span>
      </div>
    )
  }

  return null
}
