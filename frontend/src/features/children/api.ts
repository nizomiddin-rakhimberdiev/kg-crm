import { api, httpClient } from '@/lib/api/client'
import type { Child, Envelope, Group, ImportReport } from '@/lib/api/types'

export interface ChildInput {
  first_name: string
  last_name: string
  middle_name?: string
  date_of_birth: string
  gender: 'male' | 'female'
  enrollment_status?: string
  notes?: string
  branch_id?: string | null
}

export const childrenApi = {
  list: (params?: Record<string, unknown>) => api.list<Child>('/children', params),
  create: (payload: ChildInput) => api.post<Child>('/children', payload),
  update: (id: string, payload: Partial<ChildInput>) =>
    api.patch<Child>(`/children/${id}`, payload),
  remove: (id: string) => api.delete(`/children/${id}`),

  enroll: (childId: string, groupId: string) =>
    api.post(`/children/${childId}/enroll`, { group_id: groupId }),

  addGuardian: (
    childId: string,
    payload: { first_name: string; last_name: string; phone: string; relation: string; is_primary?: boolean },
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

export const groupsApi = {
  list: () => api.list<Group>('/groups'),
  create: (payload: { name: string; capacity?: number }) => api.post<Group>('/groups', payload),
}
