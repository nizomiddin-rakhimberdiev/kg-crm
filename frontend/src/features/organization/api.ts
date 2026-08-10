/** Tashkilot profili (docs/04 §16). Singleton — URL'da ID yo'q. */

import { api } from '@/lib/api/client'
import type { Organization } from '@/lib/api/types'

export interface OrganizationInput {
  name?: string
  legal_name?: string
  tax_id?: string
  contact_email?: string
  contact_phone?: string
  country?: string
  locale?: string
}

export const organizationApi = {
  get: () => api.get<Organization>('/organization'),
  update: (payload: OrganizationInput) => api.patch<Organization>('/organization', payload),
}
