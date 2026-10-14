import { beforeEach, describe, expect, it } from 'vitest'
import { clearAllDrafts, clearDraft, draftKey, readDraft, writeDraft } from '@/lib/drafts'

describe('qoralamalar', () => {
  beforeEach(() => sessionStorage.clear())

  it('yozilgan qoralama qaytib oʻqiladi', () => {
    const key = draftKey('u1', 'children-create')
    writeDraft(key, { first_name: 'Ali' })
    expect(readDraft<{ first_name: string }>(key)).toEqual({ first_name: 'Ali' })
  })

  it('foydalanuvchisiz kalit yoʻq — hech narsa saqlanmaydi', () => {
    expect(draftKey(undefined, 'x')).toBeNull()
    writeDraft(null, { a: 1 })
    expect(sessionStorage.length).toBe(0)
  })

  it('bir foydalanuvchining qoralamasi boshqasiga koʻrinmaydi', () => {
    writeDraft(draftKey('u1', 'f'), { a: 1 })
    expect(readDraft(draftKey('u2', 'f'))).toBeNull()
  })

  it('chiqishda barcha qoralamalar oʻchadi, boshqa kalitlar qoladi', () => {
    writeDraft(draftKey('u1', 'a'), 1)
    writeDraft(draftKey('u2', 'b'), 2)
    sessionStorage.setItem('boshqa', 'qoladi')
    clearAllDrafts()
    expect(readDraft(draftKey('u1', 'a'))).toBeNull()
    expect(readDraft(draftKey('u2', 'b'))).toBeNull()
    expect(sessionStorage.getItem('boshqa')).toBe('qoladi')
  })

  it('buzilgan JSON — xato emas, qoralama yoʻq', () => {
    const key = draftKey('u1', 'f')!
    sessionStorage.setItem(key, '{buzuq')
    expect(readDraft(key)).toBeNull()
    clearDraft(key)
    expect(sessionStorage.getItem(key)).toBeNull()
  })
})
