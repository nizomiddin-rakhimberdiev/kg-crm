/**
 * Vendor sessiyasi — mijoz sessiyasidan mustaqil (ADR-10).
 *
 * Ikkita alohida provayder bor va ular bir-birini ko'rmaydi. Bu
 * ataylab: bitta provayderda ikkala holatni saqlash "qaysi rejimda
 * turibman?" degan savolni har bir komponentga tarqatardi, va o'sha
 * savolga bir joyda noto'g'ri javob berilishi kifoya edi.
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
import { useNavigate } from 'react-router-dom'
import { platform, type PlatformSession } from './api'
import { platformToken, setPlatformSessionExpiredHandler } from './lib/client'

type PlatformUser = PlatformSession['user']

interface PlatformAuthValue {
  user: PlatformUser | null
  isAuthenticated: boolean
  isAdmin: boolean
  login: (email: string, password: string, code?: string) => Promise<void>
  logout: () => void
}

const USER_KEY = 'kg_crm_platform_user'

const PlatformAuthContext = createContext<PlatformAuthValue | null>(null)

export function PlatformAuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [user, setUser] = useState<PlatformUser | null>(() => {
    try {
      const raw = sessionStorage.getItem(USER_KEY)
      return raw && platformToken.get() ? (JSON.parse(raw) as PlatformUser) : null
    } catch {
      return null
    }
  })

  const logout = useCallback(() => {
    platformToken.clear()
    try {
      sessionStorage.removeItem(USER_KEY)
    } catch {
      /* private rejim */
    }
    setUser(null)
    navigate('/platform/login', { replace: true })
  }, [navigate])

  useEffect(() => {
    // Token muddati tugasa — qaytadan kirish. Vendor tokenida refresh
    // yo'q: uzoq yashaydigan vendor sessiyasi ortiqcha xavf.
    setPlatformSessionExpiredHandler(() => {
      setUser(null)
      navigate('/platform/login', { replace: true })
    })
  }, [navigate])

  const login = useCallback(async (email: string, password: string, code?: string) => {
    const session = await platform.login(email, password, code)
    platformToken.set(session.access)
    try {
      sessionStorage.setItem(USER_KEY, JSON.stringify(session.user))
    } catch {
      /* private rejim */
    }
    setUser(session.user)
  }, [])

  const value = useMemo<PlatformAuthValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isAdmin: user?.role === 'platform_admin',
      login,
      logout,
    }),
    [user, login, logout],
  )

  return <PlatformAuthContext.Provider value={value}>{children}</PlatformAuthContext.Provider>
}

export function usePlatformAuth(): PlatformAuthValue {
  const context = useContext(PlatformAuthContext)
  if (!context)
    throw new Error('usePlatformAuth() <PlatformAuthProvider> ichida chaqirilishi kerak')
  return context
}
