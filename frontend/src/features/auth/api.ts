/** Auth endpointlari (docs/04 §5). */

import { api, httpClient } from '@/lib/api/client'
import type {
  AuthSession,
  CurrentUser,
  Envelope,
  LoginResult,
  SubscriptionState,
} from '@/lib/api/types'

export interface SignupPayload {
  organization_name: string
  contact_email: string
  contact_phone?: string
  full_name: string
  password: string
}

export const authApi = {
  signup: (payload: SignupPayload) => api.post<AuthSession>('/auth/signup', payload),

  login: (email: string, password: string) =>
    api.post<LoginResult>('/auth/login', { email, password }),

  selectOrganization: (pendingToken: string, organizationId: string) =>
    api.post<AuthSession>('/auth/select-organization', {
      pending_token: pendingToken,
      organization_id: organizationId,
    }),

  me: () => api.get<{ user: CurrentUser; subscription: SubscriptionState }>('/auth/me'),

  /**
   * O'z profilini tahrirlash. Faqat ism va telefon — rol, filial va email
   * administrator ishi (backend ularni bu yerda umuman qabul qilmaydi).
   */
  updateProfile: (payload: { full_name?: string; phone?: string }) =>
    api.patch<{ user: CurrentUser; subscription: SubscriptionState }>('/auth/me', payload),

  /**
   * Profil rasmi — `multipart/form-data`, shuning uchun `httpClient`
   * bevosita: brauzer `Content-Type` ni boundary bilan o'zi qo'yishi kerak.
   */
  async uploadPhoto(file: File) {
    const form = new FormData()
    form.append('photo', file)
    const response = await httpClient.post<
      Envelope<{ user: CurrentUser; subscription: SubscriptionState }>
    >('/auth/me/photo', form, { headers: { 'Content-Type': undefined } })
    return response.data.data
  },

  async removePhoto() {
    const response = await httpClient.delete<
      Envelope<{ user: CurrentUser; subscription: SubscriptionState }>
    >('/auth/me/photo')
    return response.data.data
  },

  logout: (refresh: string | null) => api.post<void>('/auth/logout', { refresh }),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<void>('/auth/password/change', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
}
