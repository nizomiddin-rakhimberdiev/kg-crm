import { platformApi } from './lib/client'

export interface PlatformSession {
  access: string
  user: { email: string; full_name: string; role: 'platform_admin' | 'platform_support' }
}

export interface OrgSubscription {
  status: string
  payment_term: string
  discount_percent: string
  plan_code: string
  trial_ends_at: string | null
  current_period_end: string
}

export interface OrgRow {
  id: string
  name: string
  slug: string
  contact_email: string
  is_active: boolean
  created_at: string
  subscription: OrgSubscription | null
  billable_children: number
}

export interface OrgDetail extends OrgRow {
  contact_phone: string
  usage_history: Array<{
    period: string
    peak_children: number
    billable_children: number
    method: string
    closed: boolean
  }>
  invoices: Array<{
    number: string
    status: string
    issued_at: string
    due_at: string
    total_amount: string
  }>
}

export interface WorkList {
  trials_ending: Array<{ organization: string; organization_id: string; trial_ends_at: string }>
  overdue_invoices: Array<{
    organization: string
    organization_id: string
    number: string
    due_at: string
    total_amount: string
    days_late: number
  }>
  unpaid_total: string
  counts: { total: number; trialing: number; active: number; suspended: number }
}

export interface PlatformInvoice {
  id: string
  number: string
  organization: string
  organization_id: string
  status: string
  issued_at: string
  due_at: string
  total_amount: string
}

export interface SupportGrant {
  id: string
  organization: string
  organization_name: string
  platform_email: string
  reason: string
  expires_at: string
  revoked_at: string | null
  is_active: boolean
  created_at: string
}

export interface SupportSessionResult {
  access: string
  organization: string
  slug: string
  app_url: string
  grant_expires_at: string
  read_only: boolean
}

export interface PlatformPlan {
  id: string
  code: string
  name: string
  base_price: string
  included_children: number
  overage_step_children: number
  overage_step_price: string
  valid_from: string
  valid_to: string | null
}

export interface NewOrgPayload {
  organization_name: string
  contact_email: string
  contact_phone?: string
  full_name: string
  slug?: string
  branch_name?: string
}

/** Yaratilgandan keyin vendorga qaytadigan narsa — mijozga topshiriladi. */
export interface NewOrgResult {
  id: string
  name: string
  slug: string
  login_url: string
  owner_email: string
  branch: string
  // Taklif havolasi — vendor parol yozmaydi (PLAN 5.5). Javobda
  // qaytadi, chunki pochta yetib bormasa uni qo'lda uzatish kerak.
  invite_link: string
  invite_hours: number
}

export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'closed'

export interface Lead {
  id: string
  name: string
  phone: string
  kindergarten_name: string
  children_count: number
  city: string
  message: string
  language: 'uz' | 'ru' | 'en'
  source: string
  status: LeadStatus
  note: string
  /** Keyingi qo'ng'iroq sanasi — "ertaga" bir hafta o'tib ma'nosini yo'qotadi. */
  next_call_at: string | null
  status_changed_at: string | null
  consented_at: string
  privacy_policy_version: string
  created_at: string
  updated_at: string
}

export interface LeadList {
  items: Lead[]
  counts: Record<LeadStatus, number>
}

export const platform = {
  // `code` — faqat server 2FA talab qilganda (`TOTP_REQUIRED`, ADR-15).
  login: (email: string, password: string, code?: string) =>
    platformApi.post<PlatformSession>('/platform/auth/login', {
      email,
      password,
      ...(code ? { code } : {}),
    }),

  createOrganization: (payload: NewOrgPayload) =>
    platformApi.post<NewOrgResult>('/platform/organizations/create', payload),

  organizations: (params?: { search?: string; status?: string }) =>
    platformApi.get<OrgRow[]>('/platform/organizations', params),
  organization: (id: string) => platformApi.get<OrgDetail>(`/platform/organizations/${id}`),
  workList: () => platformApi.get<WorkList>('/platform/subscriptions/expiring'),

  invoices: (status?: string) =>
    platformApi.get<PlatformInvoice[]>('/platform/invoices', status ? { status } : undefined),
  recordPayment: (invoiceId: string, amount: string, reference: string) =>
    platformApi.post<{ id: string; amount: string }>(`/platform/invoices/${invoiceId}/payments`, {
      amount,
      method: 'bank_transfer',
      reference,
    }),

  suspend: (id: string, reason: string) =>
    platformApi.post<{ status: string }>(`/platform/organizations/${id}/suspend`, { reason }),
  reactivate: (id: string) =>
    platformApi.post<{ status: string }>(`/platform/organizations/${id}/reactivate`),
  extendTrial: (id: string, days: number, reason: string) =>
    platformApi.post<{ trial_ends_at: string }>(`/platform/organizations/${id}/extend-trial`, {
      days,
      reason,
    }),
  supportGrant: (id: string, reason: string, hours: number) =>
    platformApi.post<SupportGrant>(`/platform/organizations/${id}/support-grant`, {
      reason,
      hours,
    }),
  supportGrants: () => platformApi.get<SupportGrant[]>('/platform/support-grants'),

  // Saytdagi «Demo olish» formasi — platforma darajasidagi ma'lumot, tenant emas.
  leads: (params?: { status?: LeadStatus }) => platformApi.get<LeadList>('/platform/leads', params),
  setLeadStatus: (
    id: string,
    status: LeadStatus,
    note?: string,
    // `undefined` — tegilmaydi, `null` — rejani bekor qiladi. Ikkalasini
    // bitta qiymat bilan ifodalash sotuvchining rejasini jimgina
    // o'chirardi.
    nextCallAt?: string | null,
  ) =>
    platformApi.post<Lead>(`/platform/leads/${id}/status`, {
      status,
      ...(note !== undefined ? { note } : {}),
      ...(nextCallAt !== undefined ? { next_call_at: nextCallAt } : {}),
    }),
  /** Amaldagi ruxsat bilan mijoz ilovasiga kirish tokenini oladi. */
  supportSession: (id: string) =>
    platformApi.post<SupportSessionResult>(`/platform/organizations/${id}/support-session`),

  plans: () => platformApi.get<PlatformPlan[]>('/platform/plans'),
}
