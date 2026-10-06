import { api, httpClient } from '@/lib/api/client'
import type { Envelope } from '@/lib/api/types'
import type {
  StaffAttendanceStatus,
  StaffDailyRow,
  StaffTimesheet,
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
 * Xodimlar davomati va oylik tabel (docs/04 §8.3).
 *
 * `branch` — faqat ega uchun ma'noli (topbar tanlovi); filialga bog'langan
 * xodimga backend baribir o'z filialini beradi.
 */
export const staffAttendanceApi = {
  daily: (date: string, branch?: string | null) =>
    api.get<{ date: string; rows: StaffDailyRow[] }>('/staff-attendance/daily', {
      date,
      ...(branch ? { branch } : {}),
    }),

  markBulk: (
    date: string,
    records: Array<{ employee_id: string; status: StaffAttendanceStatus; note?: string }>,
    branch?: string | null,
  ) =>
    api.post<{ saved: number }>('/staff-attendance/bulk', {
      attendance_date: date,
      records,
      ...(branch ? { branch_id: branch } : {}),
    }),

  timesheet: (month: string, branch?: string | null) =>
    api.get<StaffTimesheet>('/staff-attendance/timesheet', {
      month,
      ...(branch ? { branch } : {}),
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

  /**
   * Spravka/arizani biriktirish — `multipart/form-data`, shuning uchun
   * umumiy `api` yordamchisi emas, `httpClient` bevosita (brauzer
   * `Content-Type` ni boundary bilan o'zi qo'yishi kerak).
   */
  async attachDocument(id: string, file: File) {
    const form = new FormData()
    form.append('file', file)
    const response = await httpClient.post<Envelope<AbsenceClaim>>(
      `/absence-claims/${id}/document`,
      form,
      { headers: { 'Content-Type': undefined } },
    )
    return response.data.data
  },

  /**
   * Yuklab olish `/media/` havolasi orqali EMAS: statik URL na kirishni,
   * na tashkilot chegarasini biladi, hujjat esa bolaning tibbiy
   * ma'lumotnomasi bo'lishi mumkin.
   */
  async downloadDocument(id: string, fallbackName: string) {
    const response = await httpClient.get(`/absence-claims/${id}/document/download`, {
      responseType: 'blob',
    })
    const disposition = String(response.headers?.['content-disposition'] ?? '')
    const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
    const url = URL.createObjectURL(response.data as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = match ? decodeURIComponent(match[1]) : fallbackName
    link.click()
    URL.revokeObjectURL(url)
  },
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
