/** Auth endpointlari (docs/04 §5). */

import { api } from '@/lib/api/client'
import type {
  AuthSession,
  CurrentUser,
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

  logout: (refresh: string | null) => api.post<void>('/auth/logout', { refresh }),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<void>('/auth/password/change', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
}
