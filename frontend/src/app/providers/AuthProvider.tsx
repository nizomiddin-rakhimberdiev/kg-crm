/**
 * Autentifikatsiya konteksti (docs/05 §10).
 *
 * Context faqat kichik global MIJOZ holatini saqlaydi: foydalanuvchi,
 * tashkilot, ruxsatlar, obuna holati. Server ma'lumoti bu yerga ko'chirilmaydi
 * — u TanStack Query'da qoladi.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { authApi } from '@/features/auth/api'
import { restoreSession, setSessionExpiredHandler } from '@/lib/api/client'
import { applyOrganizationLocale } from '@/lib/i18n'
import { tokenStorage } from '@/lib/auth/tokenStorage'
import { supportSession } from '@/lib/auth/supportSession'
import { clearAllDrafts } from '@/lib/drafts'
import { shouldLandOnTenantAddress, tenantPath } from '@/lib/tenantAddress'
import type { AuthSession, CurrentUser, SubscriptionState } from '@/lib/api/types'

interface AuthContextValue {
  user: CurrentUser | null
  subscription: SubscriptionState | null
  /** Boot paytida sessiyani tiklash tugagunicha `true`. */
  isLoading: boolean
  isAuthenticated: boolean
  /** Obuna to'xtatilgan — yozish amallari o'chiriladi (docs/03 §20.6). */
  isReadOnly: boolean
  applySession: (session: AuthSession) => void
  /** Vendor xodimining faqat-o'qish sessiyasi (ADR-10) — refresh tokensiz. */
  applySupportSession: (access: string) => Promise<void>
  /** Joriy sessiya vendor tomonidan ochilganmi. */
  isSupportSession: boolean
  /** Profil o'zgargach kontekstni serverdagi holatga qayta tenglashtiradi. */
  refreshUser: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [subscription, setSubscription] = useState<SubscriptionState | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const clearSession = useCallback(() => {
    tokenStorage.clear()
    setUser(null)
    setSubscription(null)
    // Keshni to'liq tozalash MAJBURIY: umumiy kompyuterda keyingi
    // foydalanuvchi oldingisining ma'lumotini ko'rmasligi kerak.
    queryClient.clear()
    // Saqlanmagan formalar ham — ularda bola va vasiyning shaxsiy
    // ma'lumoti bo'lishi mumkin (lib/drafts.ts).
    clearAllDrafts()
  }, [queryClient])

  const applySession = useCallback(
    (session: AuthSession) => {
      const slug = session.user.organization?.slug ?? null

      tokenStorage.setAccess(session.access)
      // Refresh token JAVOBDA YO'Q — u `httpOnly` cookie'da va uni
      // brauzer o'zi saqlaydi (PLAN 5.1). Shuning uchun bu yerda
      // saqlanadigan narsa faqat access token, va u xotirada.

      // Kirish `/login` dan (manzilsiz) yoki boshqa bog'cha manzilidan
      // bo'lishi mumkin. Ikkala holatda ham foydalanuvchi O'Z manziliga
      // qo'ndiriladi. Bu xavfsizlik chorasi EMAS — token baribir faqat
      // o'z tashkilotini ochadi — bu manzilni to'g'rilash: havolalar,
      // xatcho'plar va keyingi kirishlar bir xil joyga olib borsin.
      if (slug && shouldLandOnTenantAddress(slug)) {
        // To'liq sahifa yangilanishi shart: `basename` router yaratilganda
        // o'rnatilgan va uni joyida o'zgartirib bo'lmaydi.
        window.location.replace(tenantPath(slug))
        return
      }

      queryClient.clear()
      setUser(session.user)
      setSubscription(session.subscription)
    },
    [queryClient],
  )

  const applySupportSession = useCallback(
    async (access: string) => {
      // Refresh token ATAYLAB saqlanmaydi: sessiya sahifa yangilanishi
      // bilan tugaydi va vendor konsoldan qayta kirishi kerak.
      supportSession.mark()
      tokenStorage.setAccess(access)
      queryClient.clear()

      const { user: me, subscription: sub, organization_settings } = await authApi.me()
      setUser(me)
      setSubscription(sub)
      setIsLoading(false)
      applyOrganizationLocale(organization_settings?.default_language)
    },
    [queryClient],
  )

  const refreshUser = useCallback(async () => {
    const { user: me, subscription: sub, organization_settings } = await authApi.me()
    setUser(me)
    setSubscription(sub)
    applyOrganizationLocale(organization_settings?.default_language)
  }, [])

  const logout = useCallback(async () => {
    try {
      // Refresh token cookie'da — server uni o'zi o'qiydi va
      // tozalaydi.
      await authApi.logout()
    } catch {
      // Serverga yetib bormasa ham lokal sessiya baribir yopiladi.
    }
    clearSession()
  }, [clearSession])

  // Interceptor sessiya tugaganini shu yerga xabar qiladi.
  useEffect(() => {
    setSessionExpiredHandler(clearSession)
  }, [clearSession])

  // Boot: refresh token bo'lsa, sessiyani tiklaymiz.
  useEffect(() => {
    let cancelled = false

    const restore = async () => {
      // Avval YANGILASH, keyin `me` (PLAN 5.1).
      //
      // Refresh token cookie'da va JS uni ko'rmaydi, ya'ni "sessiya
      // bormi?" degan savolga faqat server javob beradi. Shuning
      // uchun boot ketma-ketligi aniq: `refresh` → `me`. Teskari
      // tartibda har yuklanishda bitta keraksiz `401` chiqardi —
      // konsolda shovqin va Sentry'da soxta xato.
      //
      // Cookie yo'q bo'lsa `refresh` 401 qaytaradi va biz jimgina
      // mehmon holatiga o'tamiz: bu xato emas, "kirmagan" degani.
      tokenStorage.dropLegacyTokens()
      try {
        await restoreSession()
      } catch {
        if (!cancelled) setIsLoading(false)
        return
      }
      try {
        const { user: me, subscription: sub, organization_settings } = await authApi.me()
        if (cancelled) return

        // Manzildagi bog'cha sessiyadagidan boshqa bo'lsa — o'z
        // manziliga qaytaramiz (2026-10-05).
        //
        // Bitta brauzerda refresh cookie BITTA: ikkinchi bog'chaga
        // kirish birinchi sessiyani almashtiradi, eski yorliqdagi
        // manzil esa o'zgarmay qoladi. Natijada URL `/t/paddington/…`
        // deb turadi, ekranda esa boshqa bog'chaning ma'lumoti.
        //
        // Bu sizib chiqish EMAS — tashkilot tokendan olinadi va RLS
        // bazada ushlab turadi (ADR-9). Lekin bu XATO QILDIRADI:
        // xodim o'zini boshqa bog'chada deb o'ylab davomat belgilashi
        // yoki to'lov yozishi mumkin. Kirishdagi bilan bir xil
        // to'g'rilash, faqat endi sessiya tiklanganda ham.
        const slug = me.organization?.slug ?? null
        if (slug && shouldLandOnTenantAddress(slug)) {
          window.location.replace(tenantPath(slug))
          return
        }

        setUser(me)
        setSubscription(sub)
        applyOrganizationLocale(organization_settings?.default_language)
      } catch {
        if (!cancelled) clearSession()
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void restore()
    return () => {
      cancelled = true
    }
  }, [clearSession])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      subscription,
      isLoading,
      isAuthenticated: user !== null,
      isReadOnly: subscription?.read_only ?? false,
      applySession,
      applySupportSession,
      isSupportSession: supportSession.isActive(),
      refreshUser,
      logout,
    }),
    [user, subscription, isLoading, applySession, applySupportSession, refreshUser, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth() <AuthProvider> ichida chaqirilishi kerak')
  return context
}

/** Joriy tashkilot ID'si — query kalitlari uchun. */
export function useOrganizationId(): string {
  const { user } = useAuth()
  return user?.organization?.id ?? 'anonymous'
}
