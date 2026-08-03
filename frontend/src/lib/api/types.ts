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
