/**
 * Obuna holatining ODAM TILIDAGI nomi (PLAN 4.3).
 *
 * Auditda profil sahifasi holatni XOM holda chiqarardi: "Obuna
 * holati: past_due". Bu nafaqat tushunarsiz — u foydalanuvchiga
 * nima qilish kerakligini ham aytmaydi.
 *
 * Nomlar BITTA joyda, chunki ular uch ekranda ko'rinadi (billing,
 * profil, platforma konsoli) va uch nusxa ertami-kechmi ajralib
 * ketardi — aynan shu narsa `money()` bilan bo'lgan (PLAN 4.1).
 */

import { t } from '@/lib/i18n'

export type SubscriptionStatus =
  'trialing' | 'pending_payment' | 'active' | 'past_due' | 'suspended' | 'cancelled'

/** Nom va rang — ikkisi birga, chunki ular bir ma'noni ifodalaydi. */
export const SUBSCRIPTION_STATUS: Record<string, [string, string]> = {
  trialing: [t('Sinov davri'), 'bg-tosh-100 text-tosh-700'],
  pending_payment: [t('Toʻlov kutilmoqda'), 'bg-orik-50 text-orik-800'],
  active: [t('Faol'), 'bg-nihol-50 text-nihol-700'],
  past_due: [t('Obuna: toʻlov muddati oʻtgan'), 'bg-orik-100 text-orik-900'],
  suspended: [t('Toʻxtatilgan'), 'bg-orik-100 text-orik-900'],
  cancelled: [t('Bekor qilingan'), 'bg-tosh-100 text-tosh-600'],
}

export function subscriptionStatusLabel(status: string | null | undefined): string {
  return SUBSCRIPTION_STATUS[status ?? '']?.[0] ?? t('Obunasiz')
}
