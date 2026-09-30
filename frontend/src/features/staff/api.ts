import { api } from '@/lib/api/client'
import type { Employee, Permission, Position, Role, StaffUser } from '@/lib/api/types'

/*
 * "Xodimlar" sahifasi IKKI xil odam bilan ishlaydi (docs/02 §6):
 *
 *   • `Employee` (`/employees`, HR) — oylik oladigan xodim: tarbiyachi,
 *     oshpaz, farrosh. Tizimga kirmasligi mumkin.
 *   • `User`     (`/users`, tizim hisobi) — login-parol bilan kiradigan
 *     odam: direktor, kassir. Bog'chaning xodimi bo'lmasligi mumkin.
 *
 * Ular ataylab birlashtirilmagan — auth modeli oylik ma'lumoti bilan
 * ifloslanmasin. Ekranda esa ikkalasi bitta sahifaning ikki tabi.
 */

// --- HR: xodimlar va lavozimlar (docs/04 §11.1) ---

export interface EmployeeInput {
  first_name: string
  last_name: string
  phone?: string
  position_id?: string | null
  hire_date: string
  base_salary: string
  /** Maoshning rasmiy qismi (ADR-18) — qolgani naqd. */
  official_salary?: string
  employment_status?: Employee['employment_status']
  termination_date?: string | null
  /** Org Owner uchun majburiy (ko'p filialda); qolganlarda backend o'zi aniqlaydi. */
  branch_id?: string
}

export const employeesApi = {
  list: (params?: Record<string, unknown>) => api.list<Employee>('/employees', params),
  create: (payload: EmployeeInput) => api.post<Employee>('/employees', payload),
  update: (id: string, payload: Partial<EmployeeInput>) =>
    api.patch<Employee>(`/employees/${id}`, payload),
  // Fizik o'chirish yo'q: backend xodimni "ishdan bo'shagan" qiladi, oylik
  // tarixi joyida qoladi (D5).
  terminate: (id: string) => api.delete(`/employees/${id}`),
}

export const positionsApi = {
  list: () => api.list<Position>('/positions', { page_size: 100 }),
  create: (payload: { title: string; department?: string; branch_id?: string }) =>
    api.post<Position>('/positions', payload),
}

// --- Tizim hisoblari va rollar (docs/04 §6) ---

export interface StaffInput {
  full_name: string
  email: string
  phone?: string
  password?: string
  role_id: string
  branch_id?: string | null
}

export const staffApi = {
  list: (params?: Record<string, unknown>) => api.list<StaffUser>('/users', params),
  create: (payload: StaffInput) => api.post<StaffUser>('/users', payload),
  update: (id: string, payload: Partial<StaffInput>) =>
    api.patch<StaffUser>(`/users/${id}`, payload),
  deactivate: (id: string) => api.delete(`/users/${id}`),
  // Faolsizlantirish — yumshoq o'chirish (`is_active = false`), shuning uchun
  // orqaga yo'l ham bor: xodim va uning tarixi joyida qoladi (docs/03 §7).
  reactivate: (id: string) => api.patch<StaffUser>(`/users/${id}`, { is_active: true }),
  roles: () => api.list<Role>('/roles'),
}

export const rolesApi = {
  list: () => api.list<Role>('/roles'),
  create: (payload: { name: string; code: string; description?: string }) =>
    api.post<Role>('/roles', payload),
  // Tizim rolini o'chirib bo'lmaydi — backend `422` qaytaradi (docs/03 §10.2).
  remove: (id: string) => api.delete(`/roles/${id}`),
  permissions: () => api.get<Permission[]>('/permissions'),
  setPermissions: (roleId: string, codes: string[]) =>
    api.request<{ permissions: string[] }>('put', `/roles/${roleId}/permissions`, {
      permissions: codes,
    }),
}
