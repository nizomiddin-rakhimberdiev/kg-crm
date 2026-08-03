import { api } from '@/lib/api/client'
import type {
  AttendanceStatus,
  AttendanceSummaryRow,
  DailyRegister,
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
