import { api } from '@/lib/api/client'
import type {
  AbsenceClaim,
  AttendanceStatus,
  AttendanceSummaryRow,
  DailyRegister,
  Holiday,
} from '@/lib/api/types'

export interface BulkRow {
  child_id: string
  status: AttendanceStatus
  reason?: string
}

export const attendanceApi = {
  daily: (groupId: string, date: string) =>
    api.get<DailyRegister>('/attendance/daily', { group: groupId, date }),

  summary: (month: string, groupId?: string | null) =>
    api.get<{ month: string; rows: AttendanceSummaryRow[] }>('/attendance/summary', {
      month,
      ...(groupId ? { group: groupId } : {}),
    }),

  markBulk: (groupId: string, date: string, records: BulkRow[]) =>
    api.post('/attendance/bulk', {
      group_id: groupId,
      attendance_date: date,
      records,
    }),
}

/**
 * Hujjat bilan tasdiqlangan kelmaslik (ADR-19).
 *
 * Davomat API'sidan ALOHIDA turadi va bu ataylab: pul faqat hujjat
 * asosida harakat qiladi, davomat jadvalidan emas.
 */
export const absenceApi = {
  list: (params?: Record<string, unknown>) =>
    api.list<AbsenceClaim>('/absence-claims', { page_size: 100, ...params }),
  create: (payload: {
    child_id: string
    kind: 'medical' | 'parental'
    date_from: string
    date_to: string
    document_no?: string
    note?: string
  }) => api.post<AbsenceClaim>('/absence-claims', payload),
  approve: (id: string, note = '') =>
    api.post<AbsenceClaim>(`/absence-claims/${id}/approve`, { note }),
  reject: (id: string, note = '') =>
    api.post<AbsenceClaim>(`/absence-claims/${id}/reject`, { note }),
}

export const holidaysApi = {
  list: () => api.list<Holiday>('/holidays', { page_size: 100 }),
  create: (payload: { holiday_date: string; name: string }) =>
    api.post<Holiday>('/holidays', payload),
  remove: (id: string) => api.delete(`/holidays/${id}`),
}
