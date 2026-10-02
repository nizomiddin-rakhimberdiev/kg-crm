/**
 * Standalone rejimi — bitta bog'cha uchun sotiladigan nusxa (ADR-13).
 *
 * `env` moduli `import.meta.env` ni IMPORT PAYTIDA o'qiydi, shuning
 * uchun har bir holat `resetModules()` dan keyin dinamik import bilan
 * tekshiriladi — aks holda birinchi testdagi qiymat qolganlariga ham
 * yopishib qolardi.
 */

import { afterEach, describe, expect, it, vi } from 'vitest'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

async function loadWithMode(mode: string | undefined, basePath = '/') {
  vi.resetModules()
  if (mode === undefined) {
    vi.stubEnv('VITE_DEPLOYMENT_MODE', '')
  } else {
    vi.stubEnv('VITE_DEPLOYMENT_MODE', mode)
  }
  vi.stubEnv('BASE_URL', basePath)
  return {
    env: (await import('../../config/env')).env,
    tenantAddress: await import('../tenantAddress'),
    navigation: await import('../../config/navigation'),
    tokenStorage: (await import('../auth/tokenStorage')).tokenStorage,
  }
}

describe('deploy rejimi', () => {
  it("sukut bo'yicha SaaS — mavjud o'rnatmalar o'zgarmaydi", async () => {
    const { env } = await loadWithMode(undefined)
    expect(env.isStandalone).toBe(false)
    expect(env.deploymentMode).toBe('saas')
  })

  it("noma'lum qiymat SaaS deb qabul qilinadi, standalone emas", async () => {
    // Xato yozilgan bayroq tizimni ATAYLAB ochib yubormasligi kerak:
    // noaniqlikda xavfsizroq tomon — obuna darvozasi yoqiq qoladi.
    const { env } = await loadWithMode('stand-alone')
    expect(env.isStandalone).toBe(false)
  })

  it("standalone bayrog'i tanilaydi", async () => {
    const { env } = await loadWithMode('standalone')
    expect(env.isStandalone).toBe(true)
  })
})

describe('standalone manzili', () => {
  it("bog'cha prefiksi ishlatilmaydi", async () => {
    const { tenantAddress } = await loadWithMode('standalone')
    // Slug berilgan bo'lsa ham: standalone'da bog'cha bitta.
    expect(tenantAddress.basenameFor('quyosh')).toBe('/')
    expect(tenantAddress.basenameFor(null)).toBe('/')
  })

  it("sub-path o'rnatmasida basename o'sha yo'l bo'ladi", async () => {
    // Demo nusxasi `radix-crm.uz/private` da yashaydi.
    const { tenantAddress } = await loadWithMode('standalone', '/private/')
    expect(tenantAddress.basenameFor(null)).toBe('/private')
  })

  it('SaaS rejimida prefiks saqlanadi', async () => {
    const { tenantAddress } = await loadWithMode('saas')
    expect(tenantAddress.basenameFor('quyosh')).toBe('/t/quyosh')
  })
})

describe('kirishdan keyingi manzil', () => {
  it("standalone: hech qachon ko'chirmaydi", async () => {
    // Aynan shu joy buzilgan edi — foydalanuvchi kirishi bilan
    // `/t/<slug>` ga, ya'ni boshqa o'rnatmaga uloqtirilardi.
    const { tenantAddress } = await loadWithMode('standalone')
    expect(tenantAddress.shouldLandOnTenantAddress('bahor-bogchasi', null)).toBe(false)
    expect(tenantAddress.shouldLandOnTenantAddress('bahor-bogchasi', 'boshqa')).toBe(false)
  })

  it("SaaS: o'z manzilida bo'lmasa ko'chiradi", async () => {
    const { tenantAddress } = await loadWithMode('saas')
    expect(tenantAddress.shouldLandOnTenantAddress('quyosh', null)).toBe(true)
    expect(tenantAddress.shouldLandOnTenantAddress('quyosh', 'bahor')).toBe(true)
  })

  it("SaaS: allaqachon o'z manzilida bo'lsa ko'chirmaydi", async () => {
    const { tenantAddress } = await loadWithMode('saas')
    expect(tenantAddress.shouldLandOnTenantAddress('quyosh', 'quyosh')).toBe(false)
    expect(tenantAddress.shouldLandOnTenantAddress(null, null)).toBe(false)
  })
})

describe('sessiya saqlanishi (PLAN 5.1)', () => {
  it('refresh token `localStorage` da SAQLANMAYDI', async () => {
    // Avval u shu yerda yashardi va XSS uchun oʻlja edi. Endi u
    // `httpOnly` cookie'da va JS uni koʻrmaydi — shuning uchun
    // moduldan uni yozish/oʻqish funksiyalari ham olib tashlangan.
    const { tokenStorage } = await loadWithMode('standalone')
    expect('setRefresh' in tokenStorage).toBe(false)
    expect('getRefresh' in tokenStorage).toBe(false)
  })

  it('eski kalitlar tozalanadi', async () => {
    const { tokenStorage } = await loadWithMode('saas')
    localStorage.setItem('kg_crm_refresh', 'eski-token')
    localStorage.setItem('kg_crm_refresh:bahor', 'eski-token-2')

    tokenStorage.dropLegacyTokens()

    // Cookie'ga oʻtgandan keyin u yerdagi qiymat foydasiz, lekin
    // XSS uchun hamon oʻlja.
    expect(localStorage.getItem('kg_crm_refresh')).toBeNull()
    expect(localStorage.getItem('kg_crm_refresh:bahor')).toBeNull()
  })

  it('access token faqat xotirada', async () => {
    const { tokenStorage } = await loadWithMode('saas')
    localStorage.clear()
    tokenStorage.setAccess('access-123')
    expect(tokenStorage.getAccess()).toBe('access-123')
    expect(Object.keys(localStorage)).toEqual([])
    tokenStorage.clear()
    expect(tokenStorage.getAccess()).toBeNull()
  })
})

describe('standalone menyusi', () => {
  it("obuna punkti ko'rinmaydi", async () => {
    const { navigation } = await loadWithMode('standalone')
    expect(navigation.navItems.some((item) => item.to === '/billing')).toBe(false)
    // Qolgan modullar joyida — rejim menyuni qirqmaydi, faqat sotuvga
    // tegishli punktni olib tashlaydi.
    expect(navigation.navItems.some((item) => item.to === '/children')).toBe(true)
    expect(navigation.navItems.some((item) => item.to === '/payroll')).toBe(true)
  })

  it('SaaS menyusida obuna bor', async () => {
    const { navigation } = await loadWithMode('saas')
    expect(navigation.navItems.some((item) => item.to === '/billing')).toBe(true)
  })
})
