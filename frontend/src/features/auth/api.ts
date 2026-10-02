/** Auth endpointlari (docs/04 §5). */

import { api, httpClient } from '@/lib/api/client'
import type {
  AuthSession,
  CurrentUser,
  Envelope,
  LoginResult,
  SubscriptionState,
} from '@/lib/api/types'

export const authApi = {
  /**
   * Kirish. `code` — faqat server soʻraganda (PLAN 5.4).
   *
   * 2FA yoqilgan hisob uchun birinchi urinish `401 TOTP_REQUIRED`
   * qaytaradi va sahifa shundagina kod maydonini koʻrsatadi: frontend
   * kimda 2FA yoqilganini oldindan bilmaydi va bilishi ham shart emas
   * (vendor login sahifasidagi naqsh bilan bir xil).
   */
  login: (email: string, password: string, code?: string) =>
    api.post<LoginResult>('/auth/login', { email, password, ...(code ? { code } : {}) }),

  /**
   * Parolni tiklash havolasini soʻrash (PLAN 5.2).
   *
   * Javob HAR DOIM bir xil — email tizimda bor-yoʻqligi tashqaridan
   * koʻrinmaydi. Shuning uchun ekranda ham bitta xabar koʻrsatiladi:
   * "bunday email yoʻq" degan matn begona odamga mijozlar roʻyxatini
   * tekshirish imkonini berardi.
   */
  requestPasswordReset: (email: string) =>
    api.post<{ detail: string }>('/auth/password-reset', { email }),

  confirmPasswordReset: (uid: string, token: string, password: string) =>
    api.post<{ detail: string }>('/auth/password-reset/confirm', { uid, token, password }),

  /**
   * Taklif havolasidan birinchi parolni oʻrnatish (PLAN 5.5).
   *
   * Sessiya qaytarmaydi: ega parolni oʻrnatgach odatdagi kirishdan
   * oʻtadi. Shu bitta qadam "parol ishladimi?" degan savolga darhol
   * javob beradi.
   */
  acceptInvite: (token: string, password: string) =>
    api.post<{ detail: string }>('/auth/invite/accept', { token, password }),

  selectOrganization: (pendingToken: string, organizationId: string, code?: string) =>
    api.post<AuthSession>('/auth/select-organization', {
      pending_token: pendingToken,
      organization_id: organizationId,
      ...(code ? { code } : {}),
    }),

  me: () =>
    api.get<{
      user: CurrentUser
      subscription: SubscriptionState
      /** Bog'chaning sukut tili (ADR-16) — xodim o'zi tanlamagan bo'lsa qo'llanadi. */
      organization_settings?: { default_language?: string }
    }>('/auth/me'),

  /**
   * O'z profilini tahrirlash. Faqat ism va telefon — rol, filial va email
   * administrator ishi (backend ularni bu yerda umuman qabul qilmaydi).
   */
  updateProfile: (payload: { full_name?: string; phone?: string }) =>
    api.patch<{ user: CurrentUser; subscription: SubscriptionState }>('/auth/me', payload),

  /**
   * Profil rasmi — `multipart/form-data`, shuning uchun `httpClient`
   * bevosita: brauzer `Content-Type` ni boundary bilan o'zi qo'yishi kerak.
   */
  async uploadPhoto(file: File) {
    const form = new FormData()
    form.append('photo', file)
    const response = await httpClient.post<
      Envelope<{ user: CurrentUser; subscription: SubscriptionState }>
    >('/auth/me/photo', form, { headers: { 'Content-Type': undefined } })
    return response.data.data
  },

  async removePhoto() {
    const response =
      await httpClient.delete<Envelope<{ user: CurrentUser; subscription: SubscriptionState }>>(
        '/auth/me/photo',
      )
    return response.data.data
  },

  /**
   * Chiqish — tanasiz (PLAN 5.1).
   *
   * Refresh token `httpOnly` cookie'da: server uni oʻzi oʻqiydi,
   * bekor qiladi va cookie'ni tozalaydi. Mijoz tomonida yuboradigan
   * narsa yoʻq.
   */
  logout: () => api.post<void>('/auth/logout', {}),

  changePassword: (currentPassword: string, newPassword: string) =>
    api.post<void>('/auth/password/change', {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  // --- Ikki bosqichli tasdiqlash (PLAN 5.4, ADR-24) ---
  //
  // Yoqish IKKI qadam: `setup` sirni beradi, `confirm` esa ilovadagi
  // haqiqiy kod bilan yoqadi. Bir qadamda qilinsa, QR'ni koʻrib
  // ilovaga qoʻshmagan odam keyingi kirishda oʻz hisobidan chiqib
  // qolardi.

  twoFactorSetup: () => api.post<{ secret: string; otpauth_uri: string }>('/auth/2fa/setup', {}),

  twoFactorConfirm: (code: string) =>
    api.post<{ backup_codes: string[] }>('/auth/2fa/confirm', { code }),

  twoFactorDisable: (password: string) =>
    api.post<{ detail: string }>('/auth/2fa/disable', { password }),

  twoFactorBackupCodes: (password: string) =>
    api.post<{ backup_codes: string[] }>('/auth/2fa/backup-codes', { password }),
}
