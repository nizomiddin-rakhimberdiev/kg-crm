/**
 * Obuna holati bannerlari (docs/03 §20.6).
 *
 * To'lamagan mijozning ma'lumoti HECH QACHON o'chirilmaydi va yashirilmaydi
 * — u faqat o'qish rejimiga o'tadi va o'z moliyaviy tarixini ko'ra oladi.
 */

import { useState } from 'react'
import { AlertTriangle, Clock, CreditCard, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { som, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'

/** Sinov tugashiga necha kun qolgani — soatlarni tepaga yaxlitlaydi. */
const daysLeft = (iso: string | null | undefined) => {
  if (!iso) return null
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86_400_000))
}

/**
 * "Qanday toʻlash" — faqat uni ocha oladiganga (PLAN 4.9).
 *
 * `/billing` tashkilot egasiga va direktorga tegishli (docs/02
 * §11.2), boshqa rol uni bossa boshqaruv paneliga qaytariladi —
 * yaʼni havola tarbiyachi uchun "bosaman, hech narsa boʻlmaydi"
 * degan oʻlik tugma edi.
 */
function BillingLink({ label }: { label: string }) {
  return (
    <Link
      to="/billing"
      className="ml-auto shrink-0 rounded-lg bg-white/70 px-3 py-1 text-xs font-semibold underline-offset-2 hover:underline"
    >
      {label}
    </Link>
  )
}

/**
 * Yopilgan banner KUNIGA BIR MARTA qaytadi (PLAN 4.9).
 *
 * Yopilmaydigan banner har ekranda joy egallab turadi va odam uni
 * oʻqimay qoʻyadi; butunlay yopiladigani esa toʻlov esdan chiqishiga
 * olib keladi. Kun — shu ikkisi orasidagi muvozanat.
 *
 * `localStorage` ataylab: bu bitta brauzerdagi qulaylik, serverda
 * saqlanadigan holat emas. Oʻqish/yozish `try` ichida — maxfiy
 * rejimda u istisno koʻtaradi.
 */
const DISMISS_KEY = 'radix.subscription-banner-dismissed'

function useDailyDismiss(): [boolean, () => void] {
  const stamp = today()
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === stamp
    } catch {
      return false
    }
  })
  const dismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, stamp)
    } catch {
      // Maxfiy rejim — banner shu sessiyada yopiladi, xolos.
    }
    setDismissed(true)
  }
  return [dismissed, dismiss]
}

function DismissButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={t('Bugun koʻrsatmaslik')}
      title={t('Bugun koʻrsatmaslik')}
      className="shrink-0 rounded-md p-1 opacity-60 transition hover:bg-black/5 hover:opacity-100"
    >
      <X className="h-4 w-4" />
    </button>
  )
}

export function SubscriptionBanner() {
  const { subscription } = useAuth()
  const { can } = useCan()
  const [dismissed, dismiss] = useDailyDismiss()

  // **Faqat egasi va direktorga** (PLAN 4.9). Ilgari matn hammaga
  // koʻrinardi — "sinov muddati butun jamoa bilishi kerak" degan
  // mulohaza bilan. Egasining qarori boshqa: toʻlov holati
  // tarbiyachining ishi emas va unga qoʻshimcha tashvish beradi.
  if (!subscription || !can('billing.read')) return null
  if (dismissed && !subscription.read_only) return null

  if (subscription.read_only) {
    return (
      <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50 px-6 py-2.5 text-sm text-amber-900">
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span>
          {t('Obuna toʻxtatilgan — maʼlumotlarni')} <strong>{t('koʻrish')}</strong>{' '}
          {t('mumkin, oʻzgartirish mumkin emas. Hisobingiz va tariximiz saqlanib turibdi.')}
        </span>
        {/* Toʻxtatilgan obuna yopilmaydi: u ish oqimini toʻxtatib
            turgan holat, eslatma emas. */}
        <BillingLink label={t('Qanday toʻlash')} />
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
          {t('. Yoqmasa, hech qanday toʻlov olinmaydi.')}
        </span>
        <BillingLink label={t('Rejani tanlash')} />
        <DismissButton onClick={dismiss} />
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
            ? t('Hisob yozildi — toʻlov kutilmoqda. Kirish toʻliq ochiq.')
            : t('Hisob muddati oʻtdi. Kirish hozircha toʻliq ochiq.')}
          {/* SUMMA ham shu yerda (PLAN 4.9): "toʻlov kutilmoqda" deb
              aytib, qancha ekanini aytmaslik mijozni boshqa ekranga
              yuboradi — yaʼni banner ishini bajarmaydi. */}
          {subscription.amount_due && (
            <strong className="ml-1">{som(subscription.amount_due)}</strong>
          )}
        </span>
        <BillingLink label={t('Qanday toʻlash')} />
        <DismissButton onClick={dismiss} />
      </div>
    )
  }

  return null
}
