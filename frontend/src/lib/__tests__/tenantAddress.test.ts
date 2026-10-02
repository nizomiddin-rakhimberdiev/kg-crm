/**
 * Bog'cha manzili — birinchi frontend testlari (P1-007).
 *
 * Nega aynan shu fayldan boshlanadi: manzil hisoblash sof funksiya
 * (tashqi bog'liqliksiz), lekin u BUTUN ilovaning `basename` ini
 * belgilaydi. Bu yerdagi xato "hech narsa ochilmaydi" bilan tugaydi —
 * ya'ni arzon testlar eng qimmat nosozlikni qoplaydi.
 */

import { describe, expect, it } from 'vitest'
import { basenameFor, slugFromPath, tenantPath, TENANT_PREFIX } from '../tenantAddress'

describe('slugFromPath', () => {
  it("prefiksli yo'ldan slug oladi", () => {
    expect(slugFromPath('/t/quyosh/dashboard')).toBe('quyosh')
    expect(slugFromPath('/t/quyosh')).toBe('quyosh')
    expect(slugFromPath('/t/quyosh/')).toBe('quyosh')
  })

  it("prefiks bo'lmasa null qaytaradi", () => {
    expect(slugFromPath('/')).toBeNull()
    expect(slugFromPath('/login')).toBeNull()
    expect(slugFromPath('/dashboard')).toBeNull()
  })

  it("vendor konsolini bog'cha deb hisoblamaydi", () => {
    // ADR-10: ikki tekislik URL darajasida ham ajralgan. `/platform`
    // hech qachon bog'cha `basename` i ostiga tushmasligi kerak.
    expect(slugFromPath('/platform')).toBeNull()
    expect(slugFromPath('/platform/organizations')).toBeNull()
  })

  it("prefiks bor, lekin slug yo'q — bu manzil emas", () => {
    expect(slugFromPath(`/${TENANT_PREFIX}`)).toBeNull()
    expect(slugFromPath(`/${TENANT_PREFIX}/`)).toBeNull()
  })
})

describe('basenameFor', () => {
  it("slug bo'lsa prefiksli basename", () => {
    expect(basenameFor('quyosh')).toBe('/t/quyosh')
  })

  it("slug bo'lmasa ildiz", () => {
    expect(basenameFor(null)).toBe('/')
  })
})

describe('tenantPath', () => {
  it("boshqa bog'chaga to'liq yo'l quradi", () => {
    expect(tenantPath('bahor')).toBe('/t/bahor/home')
    expect(tenantPath('bahor', '/payments')).toBe('/t/bahor/payments')
  })

  it('slugFromPath bilan teskari mos keladi', () => {
    // Ikkalasi bir xil shaklni bilishi SHART: ular ajralib qolsa,
    // foydalanuvchi kirgandan keyin o'z manziliga qo'na olmasdi.
    for (const slug of ['quyosh', 'bahor-2', 'a']) {
      expect(slugFromPath(tenantPath(slug))).toBe(slug)
    }
  })
})
