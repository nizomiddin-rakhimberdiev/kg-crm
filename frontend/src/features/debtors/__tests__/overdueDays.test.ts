import { describe, expect, it } from 'vitest'
import { filterByOverdueDays, overdueDaysFromSearch } from '../overdueDays'
import type { DebtorRow } from '@/lib/api/types'

const row = (id: string, oldest: string | null): DebtorRow => ({
  child: { id, full_name: id, group: null },
  balance: '100',
  oldest_overdue_date: oldest,
  primary_guardian: null,
})

describe('overdueDaysFromSearch', () => {
  it("butun son — qabul, qolgani — filtr yo'q", () => {
    expect(overdueDaysFromSearch(new URLSearchParams('overdue_days=15'))).toBe(15)
    expect(overdueDaysFromSearch(new URLSearchParams(''))).toBeNull()
    expect(overdueDaysFromSearch(new URLSearchParams('overdue_days=abc'))).toBeNull()
    expect(overdueDaysFromSearch(new URLSearchParams('overdue_days=-1'))).toBeNull()
    expect(overdueDaysFromSearch(new URLSearchParams('overdue_days=1.5'))).toBeNull()
  })
})

describe('filterByOverdueDays', () => {
  const today = new Date('2026-09-17T12:00:00')
  const rows = [
    row('160', '2026-04-10'),
    row('16', '2026-09-01'), // cutoff 2026-09-02 → 09-01 < 09-02 → kiradi
    row('15', '2026-09-02'), // teng — kirmaydi (backend `<` bilan bir xil)
    row('none', null),
  ]

  it('chegara backend qoidasi bilan bir xil: due_date < today − N', () => {
    expect(filterByOverdueDays(rows, 15, today).map((r) => r.child.id)).toEqual(['160', '16'])
  })

  it("null — filtr yo'q", () => {
    expect(filterByOverdueDays(rows, null, today)).toHaveLength(4)
  })
})
