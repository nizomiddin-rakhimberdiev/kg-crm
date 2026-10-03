import { afterEach, describe, expect, it } from 'vitest'
import { branchScope, withBranch } from '../branchScope'

describe('withBranch', () => {
  afterEach(() => branchScope.set(null))

  it("filial tanlanmagan — kalit qo'shilmaydi (backend o'zi aniqlaydi)", () => {
    expect(withBranch({ name: 'Guruh' })).toEqual({ name: 'Guruh' })
  })

  it("tanlangan filial yaratish so'roviga qo'shiladi", () => {
    branchScope.set('b-gorkiy')
    expect(withBranch({ name: 'Guruh' })).toEqual({ name: 'Guruh', branch_id: 'b-gorkiy' })
  })

  it("aniq berilgan filial o'zgarmaydi", () => {
    branchScope.set('b-gorkiy')
    expect(withBranch({ name: 'X', branch_id: 'b-main' })).toEqual({
      name: 'X',
      branch_id: 'b-main',
    })
  })
})
