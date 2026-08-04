import { api } from '@/lib/api/client'
import type { AuditLog, DashboardKpis, ProfitLoss, ReportExport, RevenueReport } from '@/lib/api/types'

export const dashboardApi = {
  kpis: () => api.get<DashboardKpis>('/dashboard'),
}

export const reportsApi = {
  revenue: (from: string, to: string) =>
    api.get<RevenueReport>('/reports/revenue', { from, to }),
  profitLoss: (from: string, to: string) =>
    api.get<ProfitLoss>('/reports/profit-loss', { from, to }),

  /** Eksportni navbatga qo'yadi — javob darhol qaytadi, fayl fonda tayyorlanadi. */
  requestExport: (reportType: string, params: Record<string, unknown> = {}) =>
    api.post<ReportExport>(`/reports/${reportType}/export`, { params }),
  listExports: () => api.get<ReportExport[]>('/reports/exports'),

  /**
   * Yuklab olish — `/media/` havolasi orqali EMAS.
   *
   * Statik media URL'i na autentifikatsiyani, na tashkilotni biladi.
   * Shuning uchun fayl token bilan olinadi va brauzerga blob sifatida
   * beriladi.
   */
  downloadExport: async (id: string, filename: string) => {
    const { httpClient } = await import('@/lib/api/client')
    const response = await httpClient.get(`/reports/exports/${id}/download`, {
      responseType: 'blob',
    })
    const url = URL.createObjectURL(response.data as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  },
}

export const auditApi = {
  list: (params?: Record<string, unknown>) => api.list<AuditLog>('/audit-logs', params),

  /**
   * Vendor SIZNING tashkilotingizga qanday tekkani (ADR-10).
   *
   * Bu ro'yxatning mavjudligi mahsulot qarori: ko'rinmaydigan kirish
   * ishonchni texnik jihatdan emas, ijtimoiy jihatdan buzadi.
   */
  platformAccess: () => api.list<AuditLog>('/audit-logs/platform-access'),
}
