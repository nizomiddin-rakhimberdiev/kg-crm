import { api } from '@/lib/api/client'
import type {
  AuditLog,
  DashboardKpis,
  ExpenseReport,
  ProfitLoss,
  ReportExport,
  ReportGroupBy,
  RevenueReport,
} from '@/lib/api/types'

export const dashboardApi = {
  kpis: () => api.get<DashboardKpis>('/dashboard'),
}

export interface BenefitsReport {
  date_from: string
  date_to: string
  total: string
  rows: Array<{
    child_id: string
    child_name: string
    kind: string
    kind_label: string
    reason: string
    created_by: string | null
    total: string
  }>
  by_kind: Array<{ kind: string; label: string; total: string }>
  by_month: Array<{ month: string; total: string }>
}

export const reportsApi = {
  revenue: (from: string, to: string, groupBy: ReportGroupBy = 'month') =>
    api.get<RevenueReport>('/reports/revenue', { from, to, group_by: groupBy }),
  // Chiqimlar alohida — foyda-zararga ruxsati yo'q (oylik maoshni ko'rmaydigan)
  // foydalanuvchi uchun hisobot sahifasi shundan yig'iladi.
  expenses: (from: string, to: string, groupBy: ReportGroupBy = 'month') =>
    api.get<ExpenseReport>('/reports/expenses', { from, to, group_by: groupBy }),
  profitLoss: (from: string, to: string, groupBy: ReportGroupBy = 'month') =>
    api.get<ProfitLoss>('/reports/profit-loss', { from, to, group_by: groupBy }),
  /** Imtiyozlar (Bosqich 12.2): kim, kimga, qancha, nega — hisob-faktura qatorlaridan. */
  benefits: (from: string, to: string) =>
    api.get<BenefitsReport>('/reports/benefits', { from, to }),

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
    // Nomni SERVER beradi va u so'rov tilida ("tushum_2026-10-02.xlsx",
    // PLAN 4.2). Mijoz tomonidagi nom faqat zaxira: ikkita nom bo'lsa,
    // foydalanuvchi papkasida ikki xil uslubdagi fayl paydo bo'lardi.
    const disposition = String(response.headers?.['content-disposition'] ?? '')
    const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
    const name = match ? decodeURIComponent(match[1]) : filename
    const url = URL.createObjectURL(response.data as Blob)
    const link = document.createElement('a')
    link.href = url
    link.download = name
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
