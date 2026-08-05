/**
 * Vendor konsoli uchun ALOHIDA API klienti (ADR-10).
 *
 * Mijoz klientidan (`lib/api/client.ts`) mustaqil, va bu ataylab.
 * Ikkala tekislik bitta klientni bo'lishsa, bitta xato — noto'g'ri
 * interceptor, noto'g'ri token — vendor tokenini mijoz so'roviga yoki
 * teskarisiga qo'shib yuborardi. Backend bunday tokenni baribir rad
 * etadi (`plane` da'vosi tekshiriladi), lekin frontend ham shu
 * ajratishni saqlashi kerak: himoya bitta joyga tayanmasligi kerak.
 *
 * Token `sessionStorage` da, `localStorage` da EMAS: vendor sessiyasi
 * tab yopilgach tugaydi. Mijoz sessiyasidan qisqaroq bo'lishi ongli —
 * bu hisob barcha mijozlar metama'lumotiga tegishli.
 */

import axios, { AxiosError, type AxiosInstance } from 'axios'
import { env } from '@/config/env'
import { ApiError, type Envelope, type ErrorEnvelope } from '@/lib/api/types'

const TOKEN_KEY = 'kg_crm_platform_token'

export const platformToken = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token: string | null) {
    try {
      if (token) sessionStorage.setItem(TOKEN_KEY, token)
      else sessionStorage.removeItem(TOKEN_KEY)
    } catch {
      /* private rejim — sessiya faqat xotirada qoladi */
    }
  },
  clear() {
    this.set(null)
  },
}

export const platformHttp: AxiosInstance = axios.create({
  baseURL: env.apiBaseUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

platformHttp.interceptors.request.use((config) => {
  const token = platformToken.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Vendor tokenida refresh YO'Q: muddati tugasa qaytadan kiriladi,
// 2FA kodi bilan. Uzoq yashaydigan vendor sessiyasi — bu hisob
// darajasida ortiqcha xavf.
let onExpired: () => void = () => {}
export const setPlatformSessionExpiredHandler = (handler: () => void) => {
  onExpired = handler
}

platformHttp.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorEnvelope>) => {
    if (error.response?.status === 401) {
      platformToken.clear()
      onExpired()
    }
    const payload = error.response?.data
    if (payload?.error) {
      return Promise.reject(
        new ApiError(payload.error.code, payload.error.message, payload.error.details),
      )
    }
    return Promise.reject(
      new ApiError('NETWORK_ERROR', error.message || 'Server bilan aloqa yo‘q.', null),
    )
  },
)

export const platformApi = {
  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await platformHttp.get<Envelope<T>>(url, { params })
    return response.data.data
  },
  async post<T>(url: string, body?: unknown): Promise<T> {
    const response = await platformHttp.post<Envelope<T>>(url, body)
    return response.data?.data
  },
}
