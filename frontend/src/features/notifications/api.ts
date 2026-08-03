import { api } from '@/lib/api/client'
import type { EffectiveSettings, Notification, NotificationTemplate, SettingValue } from '@/lib/api/types'

export interface SendPayload {
  template_code: string
  guardian_ids: string[]
  variables?: Record<string, string>
  body_override?: string
}

export const notificationsApi = {
  list: (params?: Record<string, unknown>) => api.list<Notification>('/notifications', params),
  send: (payload: SendPayload) =>
    api.post<{ queued: number; skipped_no_phone: number; results: Notification[] }>(
      '/notifications/send',
      payload,
    ),
  retry: (id: string) => api.post<Notification>(`/notifications/${id}/retry`),
  remindDebtors: () =>
    api.post<{ queued: number; results: Notification[] }>('/notifications/remind-debtors'),
}

export const templatesApi = {
  list: () => api.list<NotificationTemplate>('/notification-templates'),
  update: (id: string, payload: Partial<Pick<NotificationTemplate, 'body' | 'is_active'>>) =>
    api.patch<NotificationTemplate>(`/notification-templates/${id}`, payload),
}

export const settingsApi = {
  all: () => api.get<EffectiveSettings>('/settings'),
  set: (key: string, value: SettingValue) =>
    api.request<{ key: string; value: SettingValue }>('put', `/settings/${key}`, { value }),
}
