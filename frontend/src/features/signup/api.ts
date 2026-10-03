/** Self-signup with a 14-day trial (PLAN 6.7, ADR-28). */

import { api } from '@/lib/api/client'

export interface SignupInput {
  name: string
  email: string
  phone: string
  kindergarten_name: string
  children_count: number
  city: string
  language: string
  consent: boolean
  privacy_policy_version: string
  submission_id: string
  /** Honeypot — always empty from a person. */
  website: string
}

export const signupApi = {
  request: (body: SignupInput) => api.post<{ sent: boolean }>('/public/signup', body),
  confirm: (token: string, password: string) =>
    api.post<{ slug: string }>('/public/signup/confirm', { token, password }),
}
