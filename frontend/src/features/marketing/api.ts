import { api } from '@/lib/api/client'

export interface PricingQuote {
  total_amount: string
  /** Necha oy oldindan toʻlanadi — 1, 6 yoki 12. */
  months: number
}

export interface PublicPricing {
  children: number
  currency: string
  trial_days: number
  monthly: PricingQuote
  /** Uchinchi muddat — 6 oy, −15 % (ADR-12). */
  semiannual: PricingQuote
  annual: PricingQuote
  annual_before_discount: string
  annual_saving: string
  plan: {
    included_children: number
    overage_step_children: number
    overage_step_price: string
  }
}

export interface LeadPayload {
  name: string
  phone: string
  kindergarten_name: string
  children_count: number
  city: string
  message: string
  language: 'uz' | 'ru' | 'en'
  consent: boolean
  privacy_policy_version: string
  submission_id: string
  website?: string
}

export const marketingApi = {
  pricing: (children: number) => api.get<PublicPricing>('/public/pricing', { children }),
  createLead: (payload: LeadPayload) =>
    api.post<{ id: string; status: string }>('/public/leads', payload),
}
