/**
 * Vasiy bolaga kim boʻladi — bola kartasi ham, tahrirlash oynasi ham shundan oʻqiydi.
 *
 * Ilgari roʻyxat sahifaning ichida edi va ikkita yorligʻi ("Buvi/bobo",
 * "Aka/opa") `t()` siz yozilgan — rus va ingliz tilida ham oʻzbekcha
 * chiqardi.
 */

import { t } from '@/lib/i18n'

export const RELATIONS: Array<[string, string]> = [
  ['mother', t('Onasi')],
  ['father', t('Otasi')],
  ['grandparent', t('Buvi/bobo')],
  ['sibling', t('Aka/opa')],
  ['other', t('Boshqa')],
]

export function relationLabel(code: string): string {
  return RELATIONS.find(([value]) => value === code)?.[1] ?? code
}
