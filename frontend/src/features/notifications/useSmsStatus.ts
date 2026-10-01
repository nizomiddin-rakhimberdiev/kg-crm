/**
 * SMS holati — banner ham, hisob kartasi ham shu bitta so'rovdan.
 *
 * Alohida fayl: komponent fayli faqat komponent eksport qilsa,
 * Vite'ning tez yangilanishi (fast refresh) ishlaydi.
 */

import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { notificationsApi } from '@/features/notifications/api'
import { queryKeys } from '@/lib/api/queryKeys'

export function useSmsStatus() {
  const organizationId = useOrganizationId()
  return useQuery({
    queryKey: queryKeys.smsStatus(organizationId),
    queryFn: notificationsApi.status,
    // Holat kamdan-kam o'zgaradi (provayder sozlamasi), lekin
    // o'zgargach darhol ko'rinishi kerak.
    staleTime: 60_000,
  })
}
