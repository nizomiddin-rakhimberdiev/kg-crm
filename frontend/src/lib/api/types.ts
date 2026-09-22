/** Backend konverti va domen tiplari (docs/04 §2). */

export interface Envelope<T> {
  success: true
  data: T
  meta: { pagination?: Pagination } | null
  message: string | null
}

export interface Pagination {
  count: number
  page: number
  page_size: number
  total_pages: number
  next: string | null
  previous: string | null
}

export interface ErrorEnvelope {
  success: false
  error: {
    code: ApiErrorCode
    message: string
    details: Record<string, string[]> | null
  }
}

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'AUTHENTICATION_REQUIRED'
  | 'TOTP_REQUIRED'
  | 'PERMISSION_DENIED'
  | 'NOT_FOUND'
  | 'SUBSCRIPTION_INACTIVE'
  | 'CONFLICT'
  | 'BUSINESS_RULE_VIOLATION'
  | 'RATE_LIMITED'
  | 'INTERNAL_ERROR'
  | 'NETWORK_ERROR'

/** Interceptor har qanday xatoni shu yagona shaklga keltiradi. */
export class ApiError extends Error {
  constructor(
    readonly code: ApiErrorCode,
    message: string,
    readonly details: Record<string, string[]> | null = null,
    readonly status = 0,
  ) {
    super(message)
    this.name = 'ApiError'
  }

  /** React Hook Form uchun maydon xatolari. */
  fieldErrors(): Record<string, string> {
    if (!this.details) return {}
    return Object.fromEntries(
      Object.entries(this.details).map(([field, messages]) => [field, messages.join(' ')]),
    )
  }
}

// --- Domen tiplari ---

export interface OrganizationSummary {
  id: string
  name: string
  slug: string
}

/** Tashkilotning to'liq profili — `/organization` (docs/04 §16). */
export interface Organization {
  id: string
  name: string
  slug: string
  legal_name: string
  tax_id: string
  contact_email: string
  contact_phone: string
  country: string
  locale: string
  onboarded_at: string | null
  created_at: string
}

export interface RoleSummary {
  code: string
  name: string
}

export interface BranchSummary {
  id: string
  name: string
}

export interface CurrentUser {
  id: string
  full_name: string
  email: string
  phone: string
  /** Profil rasmi; `null` bo'lsa bosh harflar ko'rsatiladi. */
  photo_url: string | null
  role: RoleSummary | null
  organization: OrganizationSummary | null
  branch: BranchSummary | null
  permissions: string[]
}

export interface SubscriptionState {
  status: 'trialing' | 'pending_payment' | 'active' | 'past_due' | 'suspended' | 'cancelled'
  read_only: boolean
  trial_ends_at?: string | null
}

export interface AuthSession {
  access: string
  refresh: string
  user: CurrentUser
  subscription: SubscriptionState
}

/** Bir email bir nechta tashkilotga mos kelganda (docs/04 §5). */
export interface PendingOrganizationChoice {
  pending_token: string
  organizations: OrganizationSummary[]
}

export type LoginResult = AuthSession | PendingOrganizationChoice

export const isPendingChoice = (result: LoginResult): result is PendingOrganizationChoice =>
  'pending_token' in result

export interface Branch {
  id: string
  name: string
  code: string
  address: string
  phone: string
  currency: string
  timezone: string
  is_active: boolean
  created_at: string
}

export interface Permission {
  id: string
  code: string
  module: string
  action: string
  label: string
}

export interface Role {
  id: string
  name: string
  code: string
  description: string
  is_system: boolean
  branch: string | null
  permissions: string[]
}

export interface StaffUser {
  id: string
  full_name: string
  email: string
  phone: string
  role: Role | null
  branch: Branch | null
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

// --- Bolalar CRM ---

export interface GuardianLink {
  id: string
  guardian: {
    id: string
    first_name: string
    last_name: string
    full_name: string
    phone: string
    email: string
  }
  relation: string
  is_primary: boolean
  can_pickup: boolean
}

export interface Child {
  id: string
  first_name: string
  last_name: string
  middle_name: string
  full_name: string
  date_of_birth: string
  age_years: number
  gender: 'male' | 'female'
  enrollment_status: 'prospect' | 'active' | 'paused' | 'graduated' | 'withdrawn'
  enrolled_on: string | null
  tariff: string | null
  tariff_name: string | null
  balance: string
  notes: string
  guardians: GuardianLink[]
  current_group: { id: string; name: string } | null
  is_active: boolean
  created_at: string
}

export interface Group {
  id: string
  name: string
  age_min: number | null
  age_max: number | null
  capacity: number
  enrolled_count: number
  is_active: boolean
  created_at: string
}

export interface ImportRowError {
  row: number
  field: string
  message: string
}

export interface ImportReport {
  total_rows: number
  created: number
  skipped_duplicates: number
  dry_run: boolean
  errors: ImportRowError[]
}

// --- Davomat ---

export type AttendanceStatus = 'present' | 'absent' | 'excused'

export interface DailyRegisterRow {
  child_id: string
  full_name: string
  status: AttendanceStatus | null
  reason: string
  check_in_at: string | null
  record_id: string | null
}

export interface DailyRegister {
  group: { id: string; name: string }
  date: string
  rows: DailyRegisterRow[]
}

export interface AttendanceSummaryRow {
  child_id: string
  full_name: string
  present: number
  absent: number
  excused: number
  total: number
  attendance_rate: number
}

// --- Moliya ---

export interface TariffPlan {
  id: string
  name: string
  amount: string
  billing_period: 'monthly' | 'daily' | 'termly'
  is_active: boolean
  created_at: string
}

export interface InvoiceLine {
  id: string
  description: string
  quantity: string
  unit_amount: string
  line_total: string
}

export interface Invoice {
  id: string
  number: string
  child: string
  child_name: string
  period_year: number
  period_month: number
  amount_due: string
  amount_paid: string
  amount_outstanding: string
  status: 'draft' | 'issued' | 'partially_paid' | 'paid' | 'overdue' | 'cancelled'
  issued_date: string
  due_date: string
  lines: InvoiceLine[]
  created_at: string
}

export interface BillingRunResult {
  period: string
  created: number
  skipped_existing: number
  skipped_no_tariff: string[]
  total_amount: string
}

export interface Payment {
  id: string
  child: string
  child_name: string
  invoice: string | null
  invoice_number: string | null
  amount: string
  method: 'cash' | 'card' | 'bank_transfer' | 'online'
  reference: string
  paid_at: string
  is_reversed: boolean
  reversed_at: string | null
  reversal_reason: string
  created_at: string
}

export interface DebtorRow {
  child: { id: string; full_name: string; group: string | null }
  balance: string
  oldest_overdue_date: string | null
  primary_guardian: { full_name: string; phone: string } | null
}

export interface DebtorList {
  count: number
  total_debt: string
  results: DebtorRow[]
}

export interface StatementEntry {
  id: string
  occurred_at: string
  entry_type: string
  direction: 'debit' | 'credit'
  amount: string
  description: string
  running_balance: string
}

export interface ChildStatement {
  child: { id: string; full_name: string }
  balance: string
  entries: StatementEntry[]
  open_invoices: Array<{
    id: string
    number: string
    amount_due: string
    amount_paid: string
    due_date: string
    status: string
  }>
}

export interface DailyCashSummary {
  date: string
  by_method: Record<string, string>
  total: string
  reversed_total: string
  count: number
}

// --- HR va oylik ---

export interface Position {
  id: string
  title: string
  department: string
  is_active: boolean
  created_at: string
}

export interface Employee {
  id: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  position: string | null
  position_title: string | null
  employment_status: 'active' | 'on_leave' | 'terminated'
  hire_date: string
  termination_date: string | null
  base_salary: string
  is_active: boolean
  created_at: string
}

export interface PayrollItem {
  id: string
  employee: string
  employee_name: string
  base_amount: string
  bonus: string
  deduction: string
  gross: string
  net: string
  note: string
}

export interface PayrollRun {
  id: string
  period_year: number
  period_month: number
  status: 'draft' | 'finalized' | 'paid'
  is_editable: boolean
  total_gross: string
  total_deductions: string
  total_net: string
  finalized_at: string | null
  paid_at: string | null
  items: PayrollItem[]
  created_at: string
}

// --- Ombor va chiqimlar ---

export interface Warehouse { id: string; name: string; is_active: boolean; created_at: string }
export interface ProductCategory { id: string; name: string; is_active: boolean; created_at: string }
export interface Supplier {
  id: string; name: string; phone: string; contact_person: string
  is_active: boolean; created_at: string
}

export interface Product {
  id: string
  name: string
  sku: string
  category_id: string | null
  category_name: string | null
  unit: 'kg' | 'g' | 'l' | 'ml' | 'pcs' | 'pack'
  min_stock: string
  current_stock: string
  is_low_stock: boolean
  is_active: boolean
  created_at: string
}

export interface StockMovement {
  id: string
  product: string
  product_name: string
  warehouse: string
  warehouse_name: string
  supplier: string | null
  supplier_name: string | null
  direction: 'in' | 'out'
  movement_type: 'purchase' | 'consumption' | 'adjustment' | 'waste' | 'transfer'
  quantity: string
  unit_cost: string | null
  occurred_at: string
  reference: string
  note: string
  created_at: string
}

export interface ExpenseCategory { id: string; name: string; is_active: boolean; created_at: string }

export interface Expense {
  id: string
  category: string
  category_name: string
  amount: string
  expense_date: string
  description: string
  status: 'pending' | 'approved' | 'rejected' | 'paid'
  approved_by_name: string | null
  decided_at: string | null
  decision_note: string
  created_at: string
}

export interface ExpenseSummary {
  date_from: string
  date_to: string
  total: string
  by_category: Array<{ category: string; total: string }>
}

export interface NotificationTemplate {
  id: string
  code: 'payment_received' | 'debt_reminder' | 'absence_notice' | string
  channel: 'sms' | 'telegram' | 'email'
  subject: string
  body: string
  branch: string | null
  is_active: boolean
  created_at: string
}

export interface Notification {
  id: string
  template: string | null
  guardian: string | null
  guardian_name: string | null
  channel: 'sms' | 'telegram' | 'email'
  recipient_address: string
  rendered_body: string
  status: 'queued' | 'sent' | 'failed' | 'cancelled'
  provider_message_id: string
  retry_count: number
  error: string
  scheduled_for: string | null
  sent_at: string | null
  created_at: string
}

/** Sozlama qiymati skalyar, ro'yxat yoki obyekt bo'lishi mumkin (docs/03 §18.1). */
export type SettingValue = string | number | boolean | null | SettingValue[] | { [k: string]: SettingValue }
export type EffectiveSettings = Record<string, SettingValue>

export interface DashboardKpis {
  date: string
  active_children: number
  month_revenue: string
  outstanding_debt: string
  debtor_count: number
  attendance_month_pct: number
  low_stock_count: number
  recent_payments: Array<{ child: string; amount: string; paid_at: string }>
  revenue_trend: Array<{ month: string; total: string }>
  cached: boolean
}

/** Hisobot kesimi (docs/04 §14.2 `group_by`). */
export type ReportGroupBy = 'day' | 'week' | 'month' | 'quarter' | 'year'

export interface RevenueReport {
  basis: 'cash'
  date_from: string
  date_to: string
  group_by: ReportGroupBy
  total: string
  payment_count: number
  /** Uzluksiz davrlar: `period` — davr boshi (ISO sana), bo'sh davr ham bor. */
  by_period: Array<{ period: string; total: string; count: number }>
  by_method: Array<{ method: string; total: string; count: number }>
}

export interface ProfitLoss {
  basis: 'cash'
  date_from: string
  date_to: string
  group_by: ReportGroupBy
  /**
   * Oylik maosh davrlarga taqsimlanganmi. Kun/hafta kesimida `false`:
   * oylik — oylik ko'rsatkich, uni kunlarga bo'lish o'ylab topilgan raqam
   * bo'lardi. Jami (`payroll`, `net`) kesimdan qat'i nazar bir xil.
   */
  payroll_in_periods: boolean
  revenue: string
  expenses: string
  payroll: string
  net: string
  by_period: Array<{
    period: string
    revenue: string
    expenses: string
    payroll: string
    net: string
  }>
}

export interface ReportExport {
  id: string
  report_type: string
  params: Record<string, unknown>
  status: 'queued' | 'running' | 'ready' | 'failed'
  row_count: number
  error: string
  is_ready: boolean
  requested_by_name: string | null
  completed_at: string | null
  created_at: string
}

export interface AuditLog {
  id: string
  created_at: string
  actor: string | null
  actor_name: string | null
  actor_email: string
  action: string
  entity_type: string
  entity_id: string | null
  changes: Record<string, unknown>
  ip: string | null
}

export interface Subscription {
  id: string
  status: 'trialing' | 'pending_payment' | 'active' | 'past_due' | 'suspended' | 'cancelled'
  payment_term: 'monthly' | 'semiannual' | 'annual'
  discount_percent: string
  plan_code: string
  plan_name: string
  base_price: string
  included_children: number
  overage_step_children: number
  overage_step_price: string
  trial_started_at: string | null
  trial_ends_at: string | null
  current_period_start: string
  current_period_end: string
  committed_children: number | null
  is_read_only: boolean
  created_at: string
}

export interface BillingUsage {
  period: { year: number; month: number }
  current_children: number
  peak_children: number
  included_children: number
  billable_children: number
  overage_steps: number
  prepaid_base: boolean
  projected: {
    base_amount: string
    overage_amount: string
    discount_amount: string
    total_amount: string
    currency: string
  }
  /** `true` — raqam hali OLINMAGAN. Haqiqiy hisob yopilgan dalildan chiqadi. */
  is_projection: boolean
}

export interface UsageSnapshot {
  id: string
  period_year: number
  period_month: number
  peak_children: number
  peak_observed_at: string
  billable_children: number
  measurement_method: 'daily_peak' | 'manual_adjustment'
  note: string
  closed_at: string | null
  created_at: string
}

export interface SubscriptionInvoice {
  id: string
  number: string
  status: 'issued' | 'paid' | 'overdue' | 'cancelled'
  issued_at: string
  due_at: string
  period_start: string
  period_end: string
  billable_children: number
  base_amount: string
  overage_amount: string
  discount_amount: string
  total_amount: string
  amount_paid: string
  currency: string
  usage_snapshot: string | null
  created_at: string
}

/* ------------------------------------------------ Radix Intelligence (docs/07) */

export type InsightType = 'payment_delay' | 'attendance_drop'
export type InsightSeverity = 'warning' | 'critical'
export type InsightStatus = 'new' | 'seen' | 'resolved' | 'dismissed' | 'auto_resolved'

/** `evidence` v1, `payment_delay` — faqat raqamlar va id'lar, ism yo'q (docs/07 §6). */
export interface PaymentDelayEvidence {
  as_of: string
  overdue_days_threshold: number
  children_count: number
  active_children: number
  critical_days_threshold: number
  critical_children_threshold: number
  total_overdue: string
  average_days_overdue: number
  max_days_overdue: number
  children: {
    child_id: string
    group_id: string | null
    overdue_amount: string
    days_overdue: number
    invoices: number
  }[]
}

export interface Insight {
  id: string
  branch: string
  type: InsightType
  severity: InsightSeverity
  status: InsightStatus
  is_open: boolean
  subject_type: 'branch' | 'group'
  subject_id: string
  /** Tipga qarab o'qiladi — `payment_delay` uchun `PaymentDelayEvidence`. */
  evidence: Record<string, unknown>
  evidence_version: number
  recommendation_key: string
  /** Tenant basename'iga nisbatan yo'l — router o'zi qo'shadi. */
  deep_link: string
  generated_at: string
  refreshed_at: string | null
  seen_at: string | null
  resolved_at: string | null
  dismissed_at: string | null
  dismissed_until: string | null
  auto_resolved_at: string | null
}

/** Bugungi davomat to'liqligi — BOLA darajasida (docs/07 §11). */
export interface AttendanceCheck {
  expected: number
  recorded: number
  percent: number
  complete: boolean
}

export interface Briefing {
  date: string
  open_count: number
  insights: Insight[]
  checks: {
    working_day: boolean
    /** Filial foydalanuvchisi yoki `?branch=` — bitta filial. */
    attendance?: AttendanceCheck | null
    /** Egasi, filial tanlanmagan — har bir filial alohida. */
    attendance_by_branch?: Record<string, AttendanceCheck | null>
  }
}
