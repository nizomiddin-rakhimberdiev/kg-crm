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

/** Oylik yigʻma (Bosqich 12.6). */
export interface MonthlySummary {
  period: string
  roster: number
  categories: Array<{
    category: string
    label: string
    children: number
    charged: string
    benefit: string
    due: string
  }>
  invoiced: { charged: string; benefits: string; recalculations: string; amount_due: string }
  benefits_total: string
  recalculations: Array<{ kind: string; label: string; count: number; amount: string }>
  collected_for_month: {
    total: string
    before_month: string
    in_month: string
    after_month: string
    by_method: Array<{ method: string; total: string }>
  }
  cash_received: {
    total: string
    by_method: Array<{ method: string; total: string }>
    advances_for_later: string
  }
  outstanding: string
  aging: Array<{ period: string; outstanding: string; children: number }>
  check: {
    ok: boolean
    lines_match_invoices: boolean
    allocations_match_paid: boolean
    /** Xom formula — faqat qo'llab-quvvatlash uchun, ekranga chiqmaydi. */
    equation: string
    /** Tenglikning qismlari — ekran shundan gap yasaydi (ADR-45). */
    parts: {
      charged: string
      benefits: string
      recalculated: string
      collected: string
      outstanding: string
    }
  }
  closed: { closed_at: string; closed_by: string } | null
}

/** "Bogʻcha moliyasi bugun" (Bosqich 13.4). */
export type CardStatus = 'ok' | 'warning' | 'critical'
export interface HomeCard {
  key: 'money' | 'debts' | 'spending' | 'profit' | 'checks' | 'growth'
  title: string
  value: string | number
  status: CardStatus
  note: string
  detail?: {
    cash: string
    bank: string
    in_transit: string
    custody: Array<{
      user_id: string
      full_name: string
      cash: string
      bank: string
      amount: string
    }>
  }
  top?: Array<{ category: string; total: string }>
  margin?: string | null
  /** Foyda kartasi: hisoblash usuli (oy bo'yicha) — `/reports` dagi kassa usuli emas. */
  basis?: 'accrual' | 'cash'
  /** Shu oyning oyligi hali yakunlanmagan — ish haqi okladdan taxmin. */
  payroll_estimated?: boolean
  attention?: number
  occupancy?: number | null
  capacity?: number
}
export interface CheckRow {
  id: string
  title: string
  status: 'ok' | 'fail' | 'na'
  detail: string
  link: string
}
export interface AttentionItem {
  rule: string
  title: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  amount: string | null
  link: string
  at: string | null
}
export interface DailyView {
  date: string
  receipts: { total: string; by_method: Array<{ method: string; total: string }> }
  expenses: {
    total: string
    items: Array<{
      id: string
      category: string
      amount: string
      description: string
      pot: string | null
      has_receipt: boolean
    }>
  }
  counts: Array<{ pot: string; counted: string; difference: string; reason: string }>
  handovers: Array<{ from: string; to: string; amount: string; status: string }>
  new_debts: { count: number; total: string }
  attention: AttentionItem[]
}

/** Oylik hisobot paketi (Bosqich 13.5). */
export interface PackSection {
  key: string
  title: string
  [field: string]: unknown
}
export interface Pack {
  period: string
  sections: PackSection[]
  checksum: string
  latest_version: number | null
  changed_since_snapshot: boolean
}

/** Hisobot birligi: davr va (egasi tanlagan boʻlsa) filial. */
export interface PackUnit {
  year: number
  month: number
  branch?: string | null
}
const unit = ({ year, month, branch }: PackUnit) => ({ year, month, ...(branch ? { branch } : {}) })

/** Boshqaruv: topshirish, savol, qabul (Bosqich 13.6, ADR-42). */
export type ReviewStatus =
  'draft' | 'submitted' | 'question' | 'returned' | 'resubmitted' | 'accepted'
export interface ReviewEvent {
  id: string
  kind: 'note' | 'submit' | 'question' | 'answer' | 'accept' | 'return' | 'approve'
  path: string
  text: string
  parent: string | null
  author: string
  version: number | null
  created_at: string
}
export interface ReviewState {
  model: 'A' | 'B' | 'C'
  consolidation: boolean
  status: ReviewStatus
  ready: boolean
  blockers: Array<{ path: string; kind: 'check' | 'attention'; title: string; detail: string }>
  deadline: string
  late: boolean
  snapshot: { version: number; checksum: string; created_at: string } | null
  changed: boolean
  submitted_by: string
  submitted_at: string | null
  acceptors: string[]
  accepted_by: string[]
  can_accept: boolean
  events: ReviewEvent[]
  opens: Array<{ user: string; at: string; format: string }>
  share_links: Array<{
    id: string
    label: string
    version: number
    expires_at: string
    revoked: boolean
    opened: number
    last_opened_at: string | null
  }>
}
export interface NetworkRow {
  branch_id: string
  branch: string
  children: number
  occupancy: string | null
  average_per_child: string | null
  collection_rate: string | null
  payroll_share: string | null
  margin: string | null
  food_per_child_day: string | null
  attention: number
}
export interface NetworkView {
  period: string
  rows: NetworkRow[]
  best: Record<string, string | null>
  worst: Record<string, string | null>
  eliminated_transfers: string
}

/** Reja, prognoz, koʻrsatkichlar, trend (Bosqich 13.7). */
export interface BudgetRow {
  kind: 'revenue' | 'other_income' | 'payroll' | 'category'
  label: string
  plan: string
  actual: string
  difference: string
  percent: string | null
  category_id?: string
}
export interface BudgetView {
  period: string
  has_plan: boolean
  lines: BudgetRow[]
  totals: Record<'income' | 'expenses' | 'result', { plan: string; actual: string }>
}
export interface ForecastBucket {
  days: number
  until: string
  inflows: Record<string, string>
  outflows: Record<string, string>
  closing: string
}
export interface ForecastView {
  as_of: string
  opening: string
  basis: {
    collection_rate: string | null
    recurring_monthly: string
    payroll_net: string
    excluded: string
  }
  lines: Array<{
    date: string
    direction: 'in' | 'out'
    key: string
    amount: string
    basis: string
  }>
  buckets: ForecastBucket[]
  safe_withdrawal: {
    money: string
    obligations_30: string
    reserve: string
    reserve_basis: string
    amount: string
    shortfall: string
  }
}
export interface KpiItem {
  id: string
  title: string
  definition: string
  value: string | number | null
  unit: '%' | 'som' | 'children' | 'months'
}
export interface TrendMonth {
  period: string
  revenue: string
  receipts: string
  operating_expenses: string
  payroll: string
  operating_profit: string
  margin: string | null
  collection_rate: string | null
  money_end: string
}

/** Soliq taqvimi (Bosqich 13.8). */
export interface TaxItem {
  id: string
  kind: string
  title: string
  period: string
  due_date: string
  amount: string
  status: 'paid' | 'due' | 'overdue' | 'upcoming'
  paid_on: string | null
}

export const reportsApi = {
  pack: (at: PackUnit) => api.get<Pack>('/reports/pack', unit(at)),
  packSnapshot: (at: PackUnit) =>
    api.post<{ id: string; version: number; checksum: string }>('/reports/pack/snapshot', unit(at)),
  packVersions: (at: PackUnit) =>
    api.get<Array<{ version: number; checksum: string; created_at: string; created_by: string }>>(
      '/reports/pack/versions',
      unit(at),
    ),
  packDiff: (at: PackUnit, from: number, to?: number) =>
    api.get<{
      changes: Array<{
        path: string
        before: string | null
        after: string | null
        delta: string | null
      }>
    }>('/reports/pack/diff', { ...unit(at), from, ...(to ? { to } : {}) }),
  packSource: (at: PackUnit, key: string) =>
    api.get<{ rows: Array<Record<string, string>> }>('/reports/pack/source', {
      ...unit(at),
      key,
    }),
  review: (at: PackUnit) => api.get<ReviewState>('/reports/review', unit(at)),
  reviewAct: (
    at: PackUnit,
    step: 'submit' | 'approve' | 'accept' | 'return' | 'question' | 'note' | 'answer',
    body: Record<string, string> = {},
  ) => api.post<unknown>(`/reports/review/${step}`, { ...unit(at), ...body }),
  share: (at: PackUnit, label: string, days: number) =>
    api.post<{ id: string; url: string; expires_at: string }>('/reports/review/share', {
      ...unit(at),
      label,
      days,
    }),
  revokeShare: (id: string) =>
    api.post<{ id: string; revoked: boolean }>(`/reports/review/share/${id}/revoke`),
  budget: (at: PackUnit) => api.get<BudgetView>('/reports/budget', unit(at)),
  saveBudget: (
    at: PackUnit,
    lines: Array<{ kind: string; category_id?: string; amount: string }>,
  ) => api.request<BudgetView>('put', '/reports/budget', { ...unit(at), lines }),
  copyBudget: (at: PackUnit, fromYear: number, fromMonth: number) =>
    api.post<BudgetView>('/reports/budget/copy', {
      ...unit(at),
      from_year: fromYear,
      from_month: fromMonth,
    }),
  forecast: (branch?: string | null) =>
    api.get<ForecastView>('/reports/forecast', branch ? { branch } : undefined),
  kpi: (at: PackUnit) => api.get<{ period: string; items: KpiItem[] }>('/reports/kpi', unit(at)),
  trends: (at: PackUnit) => api.get<{ months: TrendMonth[] }>('/reports/trends', unit(at)),
  taxCalendar: (year: number) =>
    api.get<{ year: number; items: TaxItem[]; unpaid: string }>('/reports/tax-calendar', { year }),
  payTax: (id: string, cashAccountId: string) =>
    api.post<{ id: string; status: string }>(`/reports/tax-calendar/${id}/pay`, {
      cash_account_id: cashAccountId,
    }),
  network: (year: number, month: number) =>
    api.get<NetworkView>('/reports/network', { year, month }),
  home: (date?: string) =>
    api.get<{ date: string; cards: HomeCard[]; all_clear: boolean }>(
      '/reports/home',
      date ? { date } : undefined,
    ),
  daily: (date: string) => api.get<DailyView>('/reports/daily', { date }),
  checks: (year: number, month: number) => api.get<CheckRow[]>('/reports/checks', { year, month }),
  attention: (year: number, month: number) =>
    api.get<{ items: AttentionItem[]; count: number }>('/reports/attention', { year, month }),
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
  /** Qayerdan eshitgan (Bosqich 14). */
  sources: (from: string, to: string) =>
    api.get<{
      from: string
      to: string
      rows: Array<{ source: string; label: string; count: number; active: number; share: string }>
      total: number
      unanswered: number
    }>('/reports/sources', { from, to }),
  /** Maʼlumot toʻliqligi (Bosqich 13.3e). */
  completeness: (year: number, month: number) =>
    api.get<{
      expenses: { total: number; with_receipt: number; percent: number | null }
      cash: { active_days: number; closed_days: number }
      bank: {
        statement_uploaded: boolean
        last_statement_on: string | null
        unmatched_lines: number
      }
    }>('/reports/completeness', { year, month }),
  monthlySummary: (year: number, month: number) =>
    api.get<MonthlySummary>('/reports/monthly-summary', { year, month }),
  closeMonth: (year: number, month: number) =>
    api.post<{ id: string; period: string }>('/reports/monthly-summary/close', { year, month }),

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
