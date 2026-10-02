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
  /** Bogʻcha logotipi; `null` — bosh harf koʻrsatiladi (PLAN 4.6). */
  logo_url?: string | null
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
  logo_url: string | null
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
  /** Toʻlanmagan hisoblarning summasi — satr (pul `float` boʻlmaydi). */
  amount_due?: string | null
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
    /** Xabar tili; bo'sh — bog'chaning sukut tili (PLAN 3.4). */
    language: string
    /** Telegram botga ulanganmi (PLAN 3.7). */
    telegram_linked: boolean
    telegram_linked_at: string | null
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
  /** Allergiya — oshxona va tarbiyachiga kerak (PLAN 2.1). */
  allergies: string
  medical_notes: string
  guardians: GuardianLink[]
  current_group: { id: string; name: string } | null
  /** Holat qachon va nega o'zgargan (Q5). */
  status_changed_on: string | null
  status_reason: string
  archived_at: string | null
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
  /** Guruhning tarbiyachisi (PLAN 2.6) — xodim, tizim hisobi emas. */
  teacher_id: string | null
  teacher_name: string | null
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
  method: 'cash' | 'terminal' | 'bank_transfer' | 'online'
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
  /** Kechikkan kunlar — serverda hisoblanadi, ekranda emas (PLAN 3.5). */
  days_overdue: number | null
  primary_guardian: { full_name: string; phone: string } | null
  /** Oxirgi qarz eslatmasi qachon ketgan; `null` — hali yuborilmagan. */
  last_reminder_at: string | null
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
  /** Tizim hisobi (PLAN 2.8) — bo'lmasligi mumkin. */
  user: string | null
  user_email: string | null
  employment_status: 'active' | 'on_leave' | 'terminated'
  hire_date: string
  termination_date: string | null
  base_salary: string
  /**
   * Maoshning RASMIY qismi (ADR-18): bankka, soliq ushlab qolingan
   * holda. Qolgani (`base_salary − official_salary`) naqd.
   */
  official_salary: string
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
  /** Oy davomida berib yuborilgan pul — ushlab qolishdan alohida. */
  advance: string
  /**
   * Rasmiy qism va undan ushlanmalar (ADR-18). Rasmiy sof maosh
   * bankka, naqd qism kassadan chiqadi — shuning uchun ular alohida.
   */
  official_base: string
  tax_income: string
  tax_pension: string
  official_net: string
  cash_net: string
  gross: string
  net: string
  note: string
}

/** Oylikdan haqiqatan chiqqan pul (docs/03 §14.4a). */
export interface PlannedPayout {
  payroll_item_id: string
  employee: string
  part: 'official' | 'cash'
  amount: string
  cash_account_id: string
  cash_account_name: string
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

export interface Warehouse {
  id: string
  name: string
  is_active: boolean
  created_at: string
}
export interface ProductCategory {
  id: string
  name: string
  is_active: boolean
  created_at: string
}
export interface Supplier {
  id: string
  name: string
  phone: string
  contact_person: string
  is_active: boolean
  created_at: string
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

export interface ExpenseCategory {
  id: string
  name: string
  is_active: boolean
  created_at: string
}

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

/** SMS uzunligi — narx BO'LAKLAR bo'yicha to'lanadi (PLAN 3.3, 3.4). */
export interface SmsLength {
  encoding: 'gsm7' | 'ucs2'
  characters: number
  parts: number
  limit: number
}

export interface NotificationTemplate {
  id: string
  code: 'payment_received' | 'debt_reminder' | 'absence_notice' | string
  channel: 'sms' | 'telegram' | 'email'
  language: 'uz' | 'ru' | 'en'
  subject: string
  body: string
  branch: string | null
  is_active: boolean
  length: SmsLength
  variables: string[]
  created_at: string
}

export interface TemplatePreview extends SmsLength {
  rendered: string
}

export interface TelegramLink {
  /** Bo'sh — bot sozlanmagan; ekran havola emas, izoh ko'rsatadi. */
  url: string
  bot_username: string
  linked: boolean
}

/** Bildirishnomalar sahifasining bosh holati (PLAN 3.2, 3.3, 3.7). */
export interface SmsStatus {
  /** Ishlatiladigan kanal: `telegram` (sukut) yoki `sms`. */
  default_channel: 'telegram' | 'sms'
  /** Shu kanalda haqiqiy provayder ulanmagan — xabar ota-onaga bormaydi. */
  test_mode: boolean
  provider: string
  channels: {
    telegram: {
      configured: boolean
      bot_username: string
      /** Nechta ota-ona botga ulangan — asosiy kanalning qamrovi. */
      reach: { linked: number; total: number }
    }
    sms: { configured: boolean; provider: string }
  }
  sms_enabled: boolean
  send_from_hour: number
  send_to_hour: number
  reminders_per_day: number
  max_retries: number
  usage: {
    year: number
    month: number
    total: number
    sent: number
    failed: number
    queued: number
    test_mode: number
    telegram: number
    sms: number
    parts: number
    price_per_part: string
    /** `null` — narx kiritilmagan; "0 so'm" deb ko'rsatish yolg'on bo'lardi. */
    estimated_cost: string | null
  }
}

export interface ReminderPreview {
  eligible: number
  skipped_no_phone: number
  skipped_already_sent: number
  parts: number
  estimated_cost: string | null
}

export interface Notification {
  id: string
  template: string | null
  /** Xabar turi — shablon o'chirilgan bo'lsa ham ko'rinadi (PLAN 3.7). */
  template_code: string
  guardian: string | null
  guardian_name: string | null
  channel: 'sms' | 'telegram' | 'email'
  recipient_address: string
  rendered_body: string
  status: 'queued' | 'sent' | 'delivered' | 'failed' | 'cancelled' | 'test_mode'
  provider_message_id: string
  retry_count: number
  error: string
  scheduled_for: string | null
  sent_at: string | null
  created_at: string
}

/** Sozlama qiymati skalyar, ro'yxat yoki obyekt bo'lishi mumkin (docs/03 §18.1). */
export type SettingValue =
  string | number | boolean | null | SettingValue[] | { [k: string]: SettingValue }
export type EffectiveSettings = Record<string, SettingValue>

export interface DashboardKpis {
  date: string
  cached: boolean
  /**
   * HAR BIR bo'lak o'z ruxsatini talab qiladi (docs/02 §11.2), shuning
   * uchun hammasi ixtiyoriy: rolida `children.read` yo'q odam javobda
   * `active_children` ni umuman olmaydi — u frontendda yashirilmaydi.
   *
   * Ixtiyoriy ekani ATAYLAB: TypeScript ularni tekshirmasdan chizishga
   * yo'l qo'ymaydi.
   */
  active_children?: number
  attendance_month_pct?: number
  low_stock_count?: number
  month_revenue?: string
  outstanding_debt?: string
  debtor_count?: number
  recent_payments?: Array<{ child: string; amount: string; paid_at: string }>
  revenue_trend?: Array<{ month: string; total: string }>
  /**
   * Kassa qoldig'i — butun tarix bo'yicha (`to'lov − chiqim − oylik`).
   * To'lov, chiqim va oylikning UCHALASINI ham ko'rishga haqli rolga
   * keladi, chunki bitta raqam uchalasini birlashtiradi.
   */
  cash?: {
    income: string
    expenses: string
    payroll: string
    balance: string
    /** Naqd qancha, terminalda qancha, bankda qancha (ADR-17). */
    accounts: CashAccountBalance[]
  }
}

/** Bitta pul qopi va undagi qoldiq (docs/03 §13a). */
export interface CashAccountBalance {
  id: string
  name: string
  kind: 'cash' | 'terminal' | 'bank' | 'ewallet'
  branch_id?: string
  balance: string
}

/** Davr ichida qopga kirgan va undan chiqqan pul. */
export interface CashAccountFlow {
  id: string
  name: string
  kind: 'cash' | 'terminal' | 'bank' | 'ewallet'
  inflow: string
  outflow: string
  net: string
}

/** Hujjat bilan tasdiqlangan kelmaslik (ADR-19). */
export interface AbsenceClaim {
  id: string
  child: string
  child_name: string
  kind: 'medical' | 'parental'
  date_from: string
  date_to: string
  document_no: string
  note: string
  status: 'pending' | 'approved' | 'rejected' | 'applied'
  billable_days: number
  daily_rate: string
  credit_amount: string
  approved_by_name: string | null
  decided_at: string | null
  decision_note: string
  applied_invoice: string | null
  created_at: string
}

export interface Holiday {
  id: string
  holiday_date: string
  name: string
  created_at: string
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
  /**
   * Davr ichida qoplarga kirgan va ulardan chiqqan pul (ADR-17).
   * Bu `net` bilan TENG EMAS va bo'lishi ham shart emas: `net`
   * hisoblash usulida, bu esa kassa usulida.
   */
  by_account: CashAccountFlow[]
}

export interface ReportExport {
  id: string
  report_type: string
  params: Record<string, unknown>
  status: 'queued' | 'running' | 'ready' | 'failed'
  row_count: number
  error: string
  is_ready: boolean
  /** Saqlanadigan fayl nomi — so'rov tilida (PLAN 4.2). */
  filename: string
  requested_by_name: string | null
  completed_at: string | null
  created_at: string
}

export interface AuditLog {
  /** Obyektning NOMI — UUID oʻrniga (PLAN 4.4). Topilmasa boʻsh satr. */
  entity_label: string
  /** `changes` ichidagi UUID'lar nomlari: `{child: "Ali Karimov"}`. */
  changes_labels: Record<string, string>
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
  /**
   * Signallar QACHON hisoblangani (kechasi 03:30).
   *
   * Bu raqam bilan jonli `totals` bir xil bo'lmasligi mumkin va bu
   * normal — shuning uchun ikkalasi ham beriladi va ekranda qaysi
   * biri qachongi holat ekani yoziladi.
   */
  generated_at: string | null
  /** Jonli raqamlar — bosh sahifadagi kartochkalar bilan bitta manbadan. */
  totals: {
    total_debt: string
    overdue_debt: string
    overdue_days: number
  }
}

export interface EmployeeAdvance {
  id: string
  employee: string
  employee_name: string
  amount: string
  paid_on: string
  note: string
  created_at: string
}
