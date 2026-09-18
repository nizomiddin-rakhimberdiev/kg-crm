import { api } from '@/lib/api/client'
import type { Briefing, Insight } from '@/lib/api/types'

/**
 * Radix Intelligence (docs/07 §11).
 *
 * API gap qaytarmaydi — `type` + `evidence` + kalitlar. Matn shu
 * feature'ning `content.ts` qatlamida tuziladi: so'z o'zgarsa baza qayta
 * hisoblanmaydi.
 */
export const insightsApi = {
  briefing: (branch?: string) =>
    api.get<Briefing>('/insights/briefing', branch ? { branch } : undefined),
  list: (params?: Record<string, unknown>) => api.list<Insight>('/insights', params),

  /** Birinchi ochilish — backend'da idempotent, ikki marta chaqirish zararsiz. */
  seen: (id: string) => api.post<Insight>(`/insights/${id}/seen`),
  resolve: (id: string) => api.post<Insight>(`/insights/${id}/resolve`),
  /** "Hozir emas" — 7 kun jim, keyin shart davom etsa yana chiqadi. */
  dismiss: (id: string) => api.post<Insight>(`/insights/${id}/dismiss`),
}
