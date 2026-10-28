/**
 * Bolaning holati — nomi, rangi va ketish sabablari BITTA joyda
 * (mijoz soʻrovi, 2026-10-28).
 *
 * Mijoz yoʻlni shunday aytdi: **yangi → sinovda (3 kun) → faol**,
 * keyin **ketgan** (sababi roʻyxatdan) va baʼzan **qaytib kelgan**.
 *
 * Avval bu roʻyxat uchta faylda uch marta yozilgandi va ular
 * allaqachon bir-biridan ajralib ulgurgandi — yangi holat qoʻshish
 * uchun uch joyni eslash kerak boʻlardi, esdan chiqqani esa jimgina
 * kod koʻrsatardi (ADR-45: ekran hech qachon kod koʻrsatmaydi).
 */

import type { Child } from '@/lib/api/types'
import { t } from '@/lib/i18n'

export type ChildStatus = Child['enrollment_status']

/** Tanlash roʻyxatidagi TARTIB — bolaning yoʻli boʻyicha. */
export const STATUS_ORDER: ChildStatus[] = [
  'prospect',
  'trial',
  'active',
  'returned',
  'paused',
  'withdrawn',
  'graduated',
]

export const STATUS_LABELS: Record<ChildStatus, string> = {
  prospect: t('Yangi'),
  trial: t('Sinovda'),
  active: t('Faol'),
  returned: t('Qaytib kelgan'),
  paused: t('Toʻxtatilgan'),
  withdrawn: t('Ketgan'),
  graduated: t('Bitirgan'),
}

export const STATUS_TONE: Record<ChildStatus, string> = {
  prospect: 'bg-ildiz-50 text-ildiz-700',
  trial: 'bg-orik-50 text-orik-700',
  active: 'bg-nihol-50 text-nihol-700',
  returned: 'bg-nihol-50 text-nihol-700',
  paused: 'bg-orik-50 text-orik-700',
  withdrawn: 'bg-tosh-100 text-tosh-600',
  graduated: 'bg-tosh-100 text-tosh-600',
}

/**
 * Nega ketdi — roʻyxat QATʼIY, izoh yoniga yoziladi.
 *
 * Erkin matn "bu oy nega oltita bola ketdi?" degan savolga oltita har
 * xil jumla qoldirardi. Roʻyxat esa solishtiriladi: tarbiyachi bilan
 * kelishmovchilik tufayli ketgan uchta oila boshqaruv qarorini talab
 * qiladi, boshqa shaharga koʻchgan uchtasi esa yoʻq.
 */
export const WITHDRAW_REASONS: Array<[string, string]> = [
  ['relocation', t('Boshqa joyga koʻchish')],
  ['state_kindergarten', t('Davlat bogʻchasidan joy chiqdi')],
  ['finances', t('Moliyaviy sharoit oʻzgardi')],
  ['family', t('Oilaviy sharoit')],
  ['medical', t('Tibbiy koʻrsatma')],
  ['inclusive', t('Inklyuziv taʼlim ehtiyoji')],
  ['staff_change', t('Kadrlar almashuvi')],
  ['group_size', t('Guruhda bola koʻp')],
  ['adaptation', t('Bola moslasha olmadi')],
  ['teacher_conflict', t('Tarbiyachilar bilan kelishmovchilik')],
  ['other', t('Boshqa sabab')],
]
