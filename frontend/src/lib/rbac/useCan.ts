/**
 * Ruxsat tekshiruvi — FAQAT UX uchun (docs/02 §11.3).
 *
 * ⚠️ Bu xavfsizlik chegarasi EMAS. Frontend faqat backend taqiqlagan
 * narsani yashiradi. Har bir tekshiruv backend'da qaytadan bajariladi;
 * bu yerdagi kod ishlamaydigan tugmani ko'rsatmaslik uchun.
 */

import { useCallback } from 'react'
import { useAuth } from '@/app/providers/AuthProvider'

export type PermissionCode = `${string}.${string}`

export function useCan() {
  const { user, isReadOnly } = useAuth()

  const can = useCallback(
    (permission: PermissionCode): boolean => {
      if (!user) return false
      if (!user.permissions.includes(permission)) return false

      // Obuna to'xtatilgan bo'lsa yozish amallari o'chadi; o'qish qoladi.
      if (isReadOnly && !permission.endsWith('.read')) return false

      return true
    },
    [user, isReadOnly],
  )

  const canAny = useCallback((...permissions: PermissionCode[]) => permissions.some(can), [can])

  return { can, canAny, isReadOnly }
}
