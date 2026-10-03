import { api } from '@/lib/api/client'
import type {
  BillingUsage,
  Subscription,
  SubscriptionInvoice,
  UsageSnapshot,
} from '@/lib/api/types'

export const billingApi = {
  subscription: () => api.get<Subscription>('/billing/subscription'),
  usage: () => api.get<BillingUsage>('/billing/usage'),
  usageHistory: () => api.get<UsageSnapshot[]>('/billing/usage/history'),
  invoices: () => api.get<SubscriptionInvoice[]>('/billing/invoices'),
  /** Payme / Click pages for one open invoice (PLAN 6.4); `{}` when not set up. */
  payLinks: (invoiceId: string) =>
    api.get<{ providers: Partial<Record<'payme' | 'click', string>> }>(
      `/billing/invoices/${invoiceId}/pay`,
    ),

  acceptTrial: (paymentTerm: string) =>
    api.post<SubscriptionInvoice>('/billing/accept-trial', { payment_term: paymentTerm }),
  changeTerm: (paymentTerm: string) =>
    api.post<Subscription>('/billing/payment-term', { payment_term: paymentTerm }),
}
