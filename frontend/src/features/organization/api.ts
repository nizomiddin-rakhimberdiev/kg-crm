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

  /**
   * Logotip — ALOHIDA endpoint (PLAN 4.6).
   *
   * `multipart/form-data` talab qiladi, qolgan maydonlar esa JSON.
   * Bitta endpointda ikki format aralashsa, faylsiz `PATCH`
   * logotipni oʻchirib yuborishi oson boʻlardi.
   */
  uploadLogo: async (file: File) => {
    const { httpClient } = await import('@/lib/api/client')
    const form = new FormData()
    form.append('logo', file)
    const response = await httpClient.put('/organization/logo', form)
    return (response.data as { data: Organization }).data
  },
  removeLogo: async () => {
    const { httpClient } = await import('@/lib/api/client')
    const response = await httpClient.delete('/organization/logo')
    return (response.data as { data: Organization }).data
  },
}
