/**
 * Birinchi kun zanjiri — nol oʻrniga keyingi qadam (audit, 2026-10-21).
 *
 * Boʻsh akkauntda boshqaruv paneli faqat nollar koʻrsatadi va bu
 * sotuvdan keyingi BIRINCHI taassurot. Auditor yana bir narsani
 * yozdi: tartibni u oʻzi topishga majbur boʻlgan — tarifsiz bolaga
 * faktura chiqmaydi, lekin buni faqat urinib koʻrgandan keyin
 * bilasiz. Zanjir shu bilimni oldinga chiqaradi.
 *
 * Qadam TARTIBI majburiy, shuning uchun u bitta joyda yozilgan va
 * ekran undan oʻqiydi. Bola tarifdan oldin kelishi mumkin (import),
 * lekin keyingi qadam baribir tarif: usiz faktura yoʻq.
 */

import { t } from '@/lib/i18n'

export type StepKey = 'tariff' | 'child' | 'invoice'

export interface Step {
  key: StepKey
  title: string
  hint: string
  /** Qadam bajariladigan sahifa. */
  to: string
}

export const STEPS: Step[] = [
  {
    key: 'tariff',
    title: t('Tarif yarating'),
    hint: t('Oyiga qancha — bittadan koʻp boʻlishi mumkin (toʻliq kun, yarim kun).'),
    to: '/payments?tab=tariffs',
  },
  {
    key: 'child',
    title: t('Bola qoʻshing'),
    hint: t('Guruh va tarif aynan shu formada tanlanadi — keyin qaytish kerak boʻlmaydi.'),
    to: '/children',
  },
  {
    key: 'invoice',
    title: t('Hisob-faktura chiqaring'),
    hint: t('Bitta tugma butun bogʻcha uchun shu oyning hisob-fakturalarini yozadi.'),
    to: '/payments',
  },
]

export interface Progress {
  hasTariff: boolean
  hasChildren: boolean
  hasInvoice: boolean
}

/** Keyingi bajarilmagan qadam; hammasi bajarilgan boʻlsa — `null`. */
export function nextStep(progress: Progress): StepKey | null {
  if (!progress.hasTariff) return 'tariff'
  if (!progress.hasChildren) return 'child'
  if (!progress.hasInvoice) return 'invoice'
  return null
}
