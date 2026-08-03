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

export type AttendanceStatus = 'present' | 'absent' | 'excused' | 'late'

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
  late: number
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
