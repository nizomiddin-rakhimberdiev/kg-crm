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
import { setSessionExpiredHandler } from '@/lib/api/client'
import { tokenStorage } from '@/lib/auth/tokenStorage'
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
  }, [queryClient])

  const applySession = useCallback(
    (session: AuthSession) => {
      tokenStorage.setAccess(session.access)
      tokenStorage.setRefresh(session.refresh)
      queryClient.clear()
      setUser(session.user)
      setSubscription(session.subscription)
    },
    [queryClient],
  )

  const refreshUser = useCallback(async () => {
    const { user: me, subscription: sub } = await authApi.me()
    setUser(me)
    setSubscription(sub)
  }, [])

  const logout = useCallback(async () => {
    try {
      await authApi.logout(tokenStorage.getRefresh())
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
      if (!tokenStorage.getRefresh()) {
        setIsLoading(false)
        return
      }
      try {
        const { user: me, subscription: sub } = await authApi.me()
        if (!cancelled) {
          setUser(me)
          setSubscription(sub)
        }
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
      refreshUser,
      logout,
    }),
    [user, subscription, isLoading, applySession, refreshUser, logout],
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
