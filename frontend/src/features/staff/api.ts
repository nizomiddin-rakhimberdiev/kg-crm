import { api } from '@/lib/api/client'
import type { Permission, Role, StaffUser } from '@/lib/api/types'

export interface StaffInput {
  full_name: string
  email: string
  phone?: string
  password?: string
  role_id: string
  branch_id?: string | null
}

export const staffApi = {
  list: (params?: { search?: string; branch?: string }) =>
    api.list<StaffUser>('/users', params),
  create: (payload: StaffInput) => api.post<StaffUser>('/users', payload),
  update: (id: string, payload: Partial<StaffInput>) =>
    api.patch<StaffUser>(`/users/${id}`, payload),
  deactivate: (id: string) => api.delete(`/users/${id}`),
  roles: () => api.list<Role>('/roles'),
}

export const rolesApi = {
  list: () => api.list<Role>('/roles'),
  permissions: () => api.get<Permission[]>('/permissions'),
  setPermissions: (roleId: string, codes: string[]) =>
    api.request<{ permissions: string[] }>('put', `/roles/${roleId}/permissions`, {
      permissions: codes,
    }),
}
