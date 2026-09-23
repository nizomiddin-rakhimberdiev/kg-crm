/**
 * Obuna holati bannerlari (docs/03 §20.6).
 *
 * To'lamagan mijozning ma'lumoti HECH QACHON o'chirilmaydi va yashirilmaydi
 * — u faqat o'qish rejimiga o'tadi va o'z moliyaviy tarixini ko'ra oladi.
 */

import { AlertTriangle, Clock, CreditCard } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'

/** Sinov tugashiga necha kun qolgani — soatlarni tepaga yaxlitlaydi. */
const daysLeft = (iso: string | null | undefined) => {
  if (!iso) return null
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000))
}

/**
 * Obuna havolasi — faqat uni ocha oladiganga.
 *
 * `/billing` tashkilot egasiga tegishli (docs/02 §11.2), boshqa rol uni
 * bossa boshqaruv paneliga qaytariladi. Ya'ni havola tarbiyachi uchun
 * "bosaman — hech narsa bo'lmaydi" degan o'lik tugma edi. Banner matni
 * hammaga qoladi: sinov muddati butun jamoa bilishi kerak bo'lgan fakt.
 */
function BillingLink({ label }: { label: string }) {
  const { can } = useCan()
  if (!can('billing.read')) return null
  return (
    <Link to="/billing" className="ml-auto shrink-0 font-semibold underline">
      {label}
    </Link>
  )
}

export function SubscriptionBanner() {
  const { subscription } = useAuth()
  if (!subscription) return null

  if (subscription.read_only) {
    return (
      <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-6 py-2.5 text-sm text-amber-900">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span>
          {t("Obuna to'xtatilgan — ma'lumotlarni")} <strong>{t("ko'rish")}</strong>{' '}
          {t("mumkin, o'zgartirish mumkin emas. Hisobingiz va tariximiz saqlanib turibdi.")}
        </span>
        <BillingLink label={t("Hisobni ko'rish")} />
      </div>
    )
  }

  if (subscription.status === 'trialing') {
    const remaining = daysLeft(subscription.trial_ends_at)
    return (
      <div className="flex items-center gap-2 border-b border-brand-200 bg-brand-50 px-6 py-2.5 text-sm text-brand-900">
        <Clock className="h-4 w-4 shrink-0" />
        <span>
          {t('Sinov davri faol')}
          {remaining !== null && t(' — {remaining} kun qoldi', { remaining })}
          {t(". Yoqmasa, hech qanday to'lov olinmaydi.")}
        </span>
        <BillingLink label={t('Rejani tanlash')} />
      </div>
    )
  }

  // `pending_payment` va `past_due` — kirish TO'LIQ, lekin eslatma kerak:
  // bank o'tkazmasi kunlab ketadi va mijoz nima kutilayotganini bilsin
  // (docs/01 §4.4).
  if (subscription.status === 'pending_payment' || subscription.status === 'past_due') {
    const isPending = subscription.status === 'pending_payment'
    return (
      <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50/70 px-6 py-2.5 text-sm text-amber-900">
        <CreditCard className="h-4 w-4 shrink-0" />
        <span>
          {isPending
            ? t("Hisob yozildi — to'lov kutilmoqda. Kirish to'liq ochiq.")
            : t("Hisob muddati o'tdi. Kirish hozircha to'liq ochiq.")}
        </span>
        <BillingLink label={t("Hisobni ko'rish")} />
      </div>
    )
  }

  return null
}
