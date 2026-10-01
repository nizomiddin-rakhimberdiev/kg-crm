import { api } from '@/lib/api/client'
import type {
  EffectiveSettings,
  Notification,
  NotificationTemplate,
  ReminderPreview,
  SettingValue,
  SmsStatus,
  TemplatePreview,
} from '@/lib/api/types'

/** Ommaviy eslatma filtri — ko'rib chiqish va yuborish uchun bir xil. */
export interface ReminderFilters {
  min_amount?: string
  min_days?: number
  group_id?: string
  child_ids?: string[]
}

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
  /** Test rejimi, yuborish oynasi va oylik SMS hisobi (PLAN 3.2, 3.3). */
  status: () => api.get<SmsStatus>('/notifications/status'),
  /** Yuborishdan OLDIN: nechtasiga ketadi va taxminan qanchaga tushadi. */
  reminderPreview: (filters: ReminderFilters = {}) =>
    api.get<ReminderPreview>('/notifications/reminder-preview', {
      ...filters,
      child_ids: filters.child_ids?.join(','),
    }),
  remindDebtors: (filters: ReminderFilters = {}) =>
    api.post<{ queued: number; results: Notification[] }>('/notifications/remind-debtors', filters),
}

export const templatesApi = {
  list: () => api.list<NotificationTemplate>('/notification-templates'),
  update: (id: string, payload: Partial<Pick<NotificationTemplate, 'body' | 'is_active'>>) =>
    api.patch<NotificationTemplate>(`/notification-templates/${id}`, payload),
  create: (payload: Pick<NotificationTemplate, 'code' | 'channel' | 'language' | 'body'>) =>
    api.post<NotificationTemplate>('/notification-templates', payload),
  /**
   * Ko'rib chiqish — serverda.
   *
   * Uzunlik va bo'laklar hisobi narxni belgilaydi, shuning uchun
   * saqlashdan oldingi oxirgi raqam server tomonidan tasdiqlanadi.
   */
  preview: (body: string, variables: Record<string, string> = {}) =>
    api.post<TemplatePreview>('/notification-templates/preview', { body, variables }),
}

export const settingsApi = {
  all: () => api.get<EffectiveSettings>('/settings'),
  set: (key: string, value: SettingValue) =>
    api.request<{ key: string; value: SettingValue }>('put', `/settings/${key}`, { value }),
}
