import { api, httpClient } from '@/lib/api/client'
import type { Child, Envelope, Group, ImportReport, TelegramLink } from '@/lib/api/types'

/** Guruh maydonlari — yosh oralig'i ixtiyoriy (`null` = cheklanmagan). */
export interface GroupInput {
  name: string
  capacity?: number
  age_min?: number | null
  age_max?: number | null
  teacher_id?: string | null
}

export interface ChildInput {
  first_name: string
  last_name: string
  middle_name?: string
  date_of_birth: string
  gender: 'male' | 'female'
  enrollment_status?: string
  enrolled_on?: string | null
  notes?: string
  allergies?: string
  medical_notes?: string
  branch_id?: string | null
  tariff_id?: string | null
}

/**
 * Bo'sh (`null`/`undefined`) kalitlarni olib tashlaydi.
 *
 * Backend `branch_id` ni ixtiyoriy deb biladi: u YUBORILMASA, server filialni
 * o'zi aniqlaydi (`resolve_branch`). Lekin aniq `null` yuborilsa — bu "filial
 * yo'q" degani bo'ladi va validatsiya rad etadi. Org Owner barcha filiallarni
 * ko'rgani uchun tanlangan filial `null` bo'lishi odatiy hol, shuning uchun
 * uni yuborishdan oldin tashlab ketamiz.
 */
function withoutEmpty<T extends object>(payload: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== null && value !== undefined),
  ) as Partial<T>
}

export const childrenApi = {
  list: (params?: Record<string, unknown>) => api.list<Child>('/children', params),
  get: (id: string) => api.get<Child>(`/children/${id}`),
  create: (payload: ChildInput) => api.post<Child>('/children', withoutEmpty(payload)),
  update: (id: string, payload: Partial<ChildInput>) =>
    api.patch<Child>(`/children/${id}`, payload),
  remove: (id: string) => api.delete(`/children/${id}`),

  enroll: (childId: string, groupId: string) =>
    api.post(`/children/${childId}/enroll`, { group_id: groupId }),

  /** Holat — sana va sabab MAJBURIY (Q5). */
  changeStatus: (
    childId: string,
    payload: { enrollment_status: string; status_changed_on: string; status_reason: string },
  ) => api.post<Child>(`/children/${childId}/change-status`, payload),

  archive: (childId: string, reason?: string) =>
    api.post<Child>(`/children/${childId}/archive`, { reason: reason ?? '' }),
  restore: (childId: string) => api.post<Child>(`/children/${childId}/restore`),

  /** Xato kiritilgan yozuvni butunlay o'chiradi — faqat 24 soat ichida (Q6). */
  hardDelete: (childId: string) => api.post(`/children/${childId}/hard-delete`),

  updateGuardianLink: (
    childId: string,
    linkId: string,
    payload: { relation?: string; is_primary?: boolean; can_pickup?: boolean },
  ) => api.patch(`/children/${childId}/guardians/${linkId}`, payload),

  unlinkGuardian: (childId: string, linkId: string) =>
    api.delete(`/children/${childId}/guardians/${linkId}`),

  addGuardian: (
    childId: string,
    payload: {
      first_name: string
      last_name: string
      phone: string
      relation: string
      is_primary?: boolean
      /** Xabar tili; bo'sh — bog'chaning sukut tili (PLAN 3.4). */
      language?: string
    },
  ) => api.post(`/children/${childId}/guardians`, payload),

  /**
   * Import — `multipart/form-data`, shuning uchun umumiy `api` yordamchisi
   * emas, `httpClient` bevosita ishlatiladi (Content-Type'ni brauzer
   * boundary bilan o'zi qo'yishi kerak).
   */
  async importFile(file: File, dryRun: boolean, branchId?: string | null) {
    const form = new FormData()
    form.append('file', file)
    form.append('dry_run', String(dryRun))
    if (branchId) form.append('branch_id', branchId)

    const response = await httpClient.post<Envelope<ImportReport>>('/children/import', form, {
      headers: { 'Content-Type': undefined },
    })
    return response.data.data
  },
}

export const guardiansApi = {
  /**
   * Ota-onaga beriladigan Telegram havolasi (PLAN 3.7).
   *
   * `rotate` eski havolani darhol ishlamas qiladi — havola oilaviy
   * guruhga tashlanishi mumkin, xabarlar ichida esa bolaning ismi
   * bilan qarz summasi ketadi.
   */
  telegramLink: (id: string, rotate = false) =>
    api.post<TelegramLink>(`/guardians/${id}/telegram-link`, { rotate }),
  telegramUnlink: (id: string) => api.post(`/guardians/${id}/telegram-unlink`),
}

export const groupsApi = {
  list: () => api.list<Group>('/groups'),
  create: (payload: GroupInput) => api.post<Group>('/groups', payload),
  update: (id: string, payload: Partial<GroupInput>) => api.patch<Group>(`/groups/${id}`, payload),
  remove: (id: string) => api.delete(`/groups/${id}`),

  /** Guruh tarkibi — hozirgi bolalar va bo'sh joylar (docs/04 §7.3). */
  children: (id: string) =>
    api.get<{
      group: Group
      capacity: number
      free_seats: number | null
      children: Child[]
    }>(`/groups/${id}/children`),
}
