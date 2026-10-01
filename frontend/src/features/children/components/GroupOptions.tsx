/**
 * Guruh tanlash variantlari — BITTA joyda (PLAN 2.5).
 *
 * Auditda uchta select bir xil ro'yxatni uch xil ko'rsatardi: yaratish
 * formasida to'lgan guruh o'chirilgan edi, ro'yxatda va bola kartasida
 * esa faol — bosilganda server uni toast bilan rad etardi. Ya'ni
 * foydalanuvchi mumkin bo'lmagan ishni qila olardi va buni faqat
 * urinib ko'rgandan keyin bilardi.
 *
 * To'lgan guruh FAQAT yangi bola uchun yopiq. Bolaning HOZIRGI guruhi
 * har doim ochiq qoladi: aks holda to'lib ketgan guruhdagi bolaning
 * kartasini ochganda select bo'sh ko'rinardi.
 */

import type { Group } from '@/lib/api/types'
import { t } from '@/lib/i18n'

export function isGroupFull(group: Group): boolean {
  return group.capacity > 0 && group.enrolled_count >= group.capacity
}

export function GroupOptions({
  groups,
  currentId,
}: {
  groups: Group[]
  /** Bolaning hozirgi guruhi — to'lgan bo'lsa ham tanlanadigan qoladi. */
  currentId?: string | null
}) {
  return (
    <>
      <option value="">{t('— guruhsiz —')}</option>
      {groups.map((group) => {
        const full = isGroupFull(group) && group.id !== currentId
        return (
          <option key={group.id} value={group.id} disabled={full}>
            {group.name}
            {group.capacity ? ` (${group.enrolled_count}/${group.capacity})` : ''}
            {full ? ` — ${t("to'lgan")}` : ''}
          </option>
        )
      })}
    </>
  )
}
