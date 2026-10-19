/**
 * "Bizni qayerdan eshitdingiz?" (Bosqich 14) — roʻyxat backend'dagi
 * `HeardFrom` bilan aynan bir xil; yangisi qoʻshilsa ikkala joyda.
 */

import { t } from '@/lib/i18n'

export type HeardFrom =
  | 'instagram'
  | 'telegram'
  | 'facebook'
  | 'website'
  | 'referral'
  | 'sibling'
  | 'outdoor'
  | 'walk_by'
  | 'other'

export const HEARD_FROM: Array<[HeardFrom, string]> = [
  ['instagram', t('Instagram')],
  ['telegram', t('Telegram')],
  ['facebook', t('Facebook')],
  ['website', t('Google / sayt')],
  ['referral', t('Tanish-bilish tavsiyasi')],
  ['sibling', t('Aka-ukasi yoki opa-singlisi shu yerda')],
  ['outdoor', t('Banner, flayer, reklama')],
  ['walk_by', t('Yonidan oʻtib qolgan')],
  ['other', t('Boshqa')],
]

export function heardFromLabel(value: string | null | undefined): string {
  return HEARD_FROM.find(([key]) => key === value)?.[1] ?? t('Koʻrsatilmagan')
}
