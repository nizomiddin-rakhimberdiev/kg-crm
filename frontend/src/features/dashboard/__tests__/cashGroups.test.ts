/** Qoplarni ikkita guruhga yig'ish (PLAN 7.3). */

import { describe, expect, it } from 'vitest'
import { groupAccounts } from '../cashGroups'
import type { CashAccountBalance } from '@/lib/api/types'

const account = (kind: string, name: string, balance: string): CashAccountBalance =>
  ({ id: kind, kind, name, balance }) as CashAccountBalance

const FOUR = [
  account('bank', 'Bank hisobi', '48600000'),
  account('cash', 'Naqd kassa', '31600000'),
  account('ewallet', 'Payme / Click', '300000'),
  account('terminal', 'Terminal', '138820000'),
]

describe('groupAccounts', () => {
  it('toʻrtta qopdan ikkita guruh chiqadi', () => {
    const groups = groupAccounts(FOUR)
    expect(groups.map((g) => g.key)).toEqual(['cash', 'bank'])
  })

  it('naqd alohida qoladi', () => {
    const [cash] = groupAccounts(FOUR)
    expect(cash.balance).toBe(31600000)
    expect(cash.parts).toEqual(['Naqd kassa'])
  })

  it('oʻtkazma, terminal va Payme/Click qoʻshiladi', () => {
    const bank = groupAccounts(FOUR)[1]
    expect(bank.balance).toBe(48600000 + 300000 + 138820000)
    expect(bank.parts).toEqual(['Bank hisobi', 'Payme / Click', 'Terminal'])
  })

  it('yigʻindi oʻzgarmaydi — faqat koʻrsatish guruhlanadi', () => {
    const total = FOUR.reduce((sum, a) => sum + Number(a.balance), 0)
    expect(groupAccounts(FOUR).reduce((sum, g) => sum + g.balance, 0)).toBe(total)
  })

  it('boʻsh guruh koʻrsatilmaydi', () => {
    expect(groupAccounts([account('cash', 'Naqd kassa', '100')])).toHaveLength(1)
    expect(groupAccounts([])).toEqual([])
    expect(groupAccounts(undefined)).toEqual([])
  })
})
