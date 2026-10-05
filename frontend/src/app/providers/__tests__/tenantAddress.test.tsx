/**
 * Manzildagi bog'cha va sessiyadagi bog'cha bir xil bo'lishi (2026-10-05).
 *
 * Bitta brauzerda ikkinchi bog'chaga kirilsa, refresh cookie BITTA
 * bo'lgani uchun ikkinchi sessiya birinchisini almashtiradi. Eski
 * yorliqdagi manzil esa o'zgarmaydi: URL `/t/paddington/...` deb turadi,
 * ekranda esa Oriental Kinderland ma'lumoti.
 *
 * Bu ma'lumot sizib chiqishi EMAS — tashkilot tokendan olinadi va RLS
 * bazada ushlab turadi. Lekin bu XATO QILDIRADI: xodim o'zini Paddington
 * da deb o'ylab, boshqa bog'chaning davomatini belgilashi mumkin.
 * Shuning uchun sessiya tiklanganda manzil to'g'rilanadi.
 */

import { render, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const replace = vi.fn()

vi.mock('@/features/auth/api', () => ({
  authApi: { me: vi.fn(), logout: vi.fn() },
}))
vi.mock('@/lib/api/client', () => ({
  restoreSession: vi.fn(async () => 'access-token'),
  setSessionExpiredHandler: vi.fn(),
  api: {},
  httpClient: { get: vi.fn(), post: vi.fn() },
}))
vi.mock('@/lib/api/tokenStorage', () => ({
  tokenStorage: { setAccess: vi.fn(), dropLegacyTokens: vi.fn(), clear: vi.fn() },
}))

const session = (slug: string) => ({
  user: { id: '1', full_name: 'Abdulaziz', permissions: [], organization: { slug } },
  subscription: { status: 'active', read_only: false },
  organization_settings: { default_language: 'uz' },
})

async function boot(urlSlug: string, sessionSlug: string) {
  vi.resetModules()
  const pathname = `/t/${urlSlug}/attendance`
  // `location` ni AYNAN shu manzil bilan qo'yamiz: `tenantAddress` slugni
  // modul yuklanganda `window.location.pathname` dan o'qiydi, va soxta
  // obyektni oldindan muzlatib qo'ysak u eski manzilda qolib ketardi.
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { ...window.location, pathname, replace },
  })
  const { authApi } = await import('@/features/auth/api')
  vi.mocked(authApi.me).mockResolvedValue(session(sessionSlug) as never)
  const { AuthProvider } = await import('../AuthProvider')
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <div>ok</div>
      </AuthProvider>
    </QueryClientProvider>,
  )
  await waitFor(() => expect(authApi.me).toHaveBeenCalled())
}

describe('manzil va sessiya mos kelishi', () => {
  beforeEach(() => replace.mockClear())
  afterEach(() => vi.restoreAllMocks())

  it('boshqa bogʻcha manzilida ochilsa, oʻz manziliga qaytaradi', async () => {
    await boot('paddington', 'oriental-kinderland')
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/t/oriental-kinderland/home'))
  })

  it('manzil toʻgʻri boʻlsa, hech qayerga yubormaydi', async () => {
    await boot('oriental-kinderland', 'oriental-kinderland')
    await new Promise((r) => setTimeout(r, 30))
    expect(replace).not.toHaveBeenCalled()
  })
})
