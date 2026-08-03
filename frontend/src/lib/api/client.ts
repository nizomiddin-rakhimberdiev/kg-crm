/**
 * Axios klienti — JWT biriktirish, token yangilash va xato normalizatsiyasi.
 *
 * Bu fayl backend bilan bo'lgan YAGONA aloqa nuqtasi: har bir chaqiruv
 * konvertdan tozalangan `data` ni oladi va har qanday nosozlik bitta
 * `ApiError` shakliga keladi (docs/05 §12).
 */

import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { env } from '@/config/env'
import { tokenStorage } from '@/lib/auth/tokenStorage'
import { ApiError, type Envelope, type ErrorEnvelope } from './types'

export const httpClient: AxiosInstance = axios.create({
  baseURL: env.apiBaseUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

/** Sessiya tugaganda ilova xabardor bo'lishi uchun (AuthProvider ulanadi). */
type SessionExpiredHandler = () => void
let onSessionExpired: SessionExpiredHandler = () => {}
export const setSessionExpiredHandler = (handler: SessionExpiredHandler) => {
  onSessionExpired = handler
}

httpClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// --- Token yangilash ---
//
// Bir vaqtda bir nechta so'rov 401 olishi mumkin. Har biri alohida refresh
// yuborsa, rotatsiya tufayli birinchisidan keyingilari yaroqsiz tokenga
// murojaat qiladi va foydalanuvchi sababsiz tashqariga chiqib qoladi.
// Shuning uchun refresh bitta va'daga birlashtiriladi.
let refreshPromise: Promise<string> | null = null

const refreshAccessToken = async (): Promise<string> => {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) throw new ApiError('AUTHENTICATION_REQUIRED', 'Sessiya topilmadi.')

  const response = await axios.post<Envelope<{ access: string; refresh: string }>>(
    `${env.apiBaseUrl}/auth/refresh`,
    { refresh },
    { headers: { 'Content-Type': 'application/json' } },
  )
  const tokens = response.data.data
  tokenStorage.setAccess(tokens.access)
  tokenStorage.setRefresh(tokens.refresh)
  return tokens.access
}

const isRefreshCall = (config?: InternalAxiosRequestConfig) =>
  Boolean(config?.url?.includes('/auth/refresh'))

httpClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ErrorEnvelope>) => {
    const config = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined

    if (!error.response) {
      throw new ApiError('NETWORK_ERROR', 'Serverga ulanib bo\'lmadi. Internetni tekshiring.')
    }

    const { status, data } = error.response

    // 401 → bir marta yangilashga urinamiz.
    if (status === 401 && config && !config._retried && !isRefreshCall(config)) {
      config._retried = true
      try {
        refreshPromise ??= refreshAccessToken().finally(() => {
          refreshPromise = null
        })
        const access = await refreshPromise
        config.headers.Authorization = `Bearer ${access}`
        return httpClient(config)
      } catch {
        tokenStorage.clear()
        onSessionExpired()
        throw new ApiError('AUTHENTICATION_REQUIRED', 'Sessiya muddati tugadi. Qaytadan kiring.')
      }
    }

    const envelope = data?.error
    throw new ApiError(
      envelope?.code ?? 'INTERNAL_ERROR',
      envelope?.message ?? 'Kutilmagan xatolik yuz berdi.',
      envelope?.details ?? null,
      status,
    )
  },
)

/** Konvertdan `data` ni ochib beradi — chaqiruvchilar `.data.data` yozmasin. */
export const api = {
  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await httpClient.get<Envelope<T>>(url, { params })
    return response.data.data
  },

  /** Ro'yxat endpointlari uchun — `meta.pagination` bilan birga. */
  async list<T>(url: string, params?: Record<string, unknown>) {
    const response = await httpClient.get<Envelope<T[]>>(url, { params })
    return {
      items: response.data.data,
      pagination: response.data.meta?.pagination ?? null,
    }
  },

  async post<T>(url: string, body?: unknown): Promise<T> {
    const response = await httpClient.post<Envelope<T>>(url, body)
    return response.data?.data
  },

  async patch<T>(url: string, body?: unknown): Promise<T> {
    const response = await httpClient.patch<Envelope<T>>(url, body)
    return response.data.data
  },

  async delete(url: string): Promise<void> {
    await httpClient.delete(url)
  },
}
