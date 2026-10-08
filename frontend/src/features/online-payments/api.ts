/**
 * Online payments — Payme / Click into the kindergarten's own merchant
 * (PLAN 6.1, ADR-26).
 */

import { api } from '@/lib/api/client'

export type OnlineProvider = 'payme' | 'click'

export interface PaymentLink {
  url: string
  expires_at: string
}

export interface MerchantCredentialState {
  provider: OnlineProvider
  configured: boolean
  merchant_id: string
  service_id: string
  /** Last four characters only — the secret never comes back. */
  secret_hint: string
  sandbox: boolean
  /** Pasted into the provider's merchant cabinet. */
  webhook_url: string
}

export interface CredentialInput {
  merchant_id: string
  service_id?: string
  secret: string
  sandbox: boolean
}

/** What the parent's public page shows (`GET /public/pay/link/{token}`). */
export interface PublicPayLink {
  kindergarten: string
  logo_url: string | null
  /** Bogʻchaning telefoni — ota-ona ikkilansa, murojaat qiladigan joy. */
  contact_phone: string
  /** First name and initial only — the link may be forwarded. */
  child: string
  invoice: string
  /** `MM.YYYY` */
  period: string
  amount_due: string
  payable: string
  is_paid: boolean
  providers: Partial<Record<OnlineProvider, string>>
}

export const onlinePaymentsApi = {
  createLink: (invoiceId: string) =>
    api.post<PaymentLink>('/online-payments/links', { invoice_id: invoiceId }),

  credentials: () => api.get<MerchantCredentialState[]>('/online-payments/credentials'),

  saveCredential: (provider: OnlineProvider, body: CredentialInput) =>
    api.request<{ provider: OnlineProvider; secret_hint: string }>(
      'put',
      `/online-payments/credentials/${provider}`,
      body,
    ),

  removeCredential: (provider: OnlineProvider) =>
    api.delete(`/online-payments/credentials/${provider}`),

  publicLink: (token: string) =>
    api.get<PublicPayLink>(`/public/pay/link/${encodeURIComponent(token)}`),
}

export const PROVIDER_LABEL: Record<OnlineProvider, string> = {
  payme: 'Payme',
  click: 'Click',
}
