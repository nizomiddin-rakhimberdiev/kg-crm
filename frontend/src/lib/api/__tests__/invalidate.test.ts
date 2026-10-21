/**
 * Mutatsiyadan keyin ekrandagi raqam yangilanishi kerak (audit, 2026-10-21).
 *
 * Auditda: Omborga mahsulot qo'shilgandan keyin ro'yxat eski holida
 * qolardi va foydalanuvchi "saqlanmadi" deb o'ylab ikkinchi marta
 * bosardi — natijada ikki xil nusxa. Sabab `invalidateMoney` dagi
 * domen nomi edi: u `inventory` deb yozilgan, haqiqiy kalitlar esa
 * `products`, `warehouses`, `movements`. Hech narsa mos kelmasdi va
 * `invalidateQueries` jimgina hech narsani yangilamasdi.
 *
 * Shuning uchun bu test domen ro'yxatini EMAS, haqiqiy kalitlarni
 * tekshiradi: `queryKeys` fabrikasidan kalit olinadi, keshga yoziladi,
 * va `invalidate…` dan keyin u eskirgan bo'lishi kerak.
 */

import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import { invalidateAttendance, invalidateMoney } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'

const ORG = '11111111-1111-1111-1111-111111111111'

type Key = readonly unknown[]

function client(keys: readonly Key[]): QueryClient {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  for (const key of keys) queryClient.setQueryData([...key], { items: [] })
  return queryClient
}

function stale(queryClient: QueryClient, keys: readonly Key[]): string[] {
  return keys
    .filter((key) => !(queryClient.getQueryState([...key])?.isInvalidated ?? false))
    .map((key) => JSON.stringify(key))
}

describe('invalidateMoney', () => {
  const keys = [
    queryKeys.products(ORG),
    queryKeys.warehouses(ORG),
    queryKeys.movements(ORG),
    queryKeys.invoices(ORG),
    queryKeys.payments(ORG),
    queryKeys.debtors(ORG),
    queryKeys.children(ORG),
    queryKeys.cashAccounts(ORG),
    queryKeys.dashboard(ORG),
    queryKeys.briefing(ORG),
    queryKeys.payrollRuns(ORG),
    queryKeys.expenses(ORG),
    queryKeys.tariffs(ORG),
    queryKeys.reportRevenue(ORG, '2026-10-01', '2026-10-31', 'day'),
  ] as const satisfies readonly Key[]

  it('refreshes every screen a money change touches', () => {
    const queryClient = client(keys)
    invalidateMoney(queryClient, ORG)
    expect(stale(queryClient, keys)).toEqual([])
  })

  it('leaves another organization alone', () => {
    const other = ['org', '22222222-2222-2222-2222-222222222222', 'payments', {}]
    const queryClient = client([...keys, other])
    invalidateMoney(queryClient, ORG)
    expect(queryClient.getQueryState(other)?.isInvalidated ?? false).toBe(false)
  })
})

describe('invalidateAttendance', () => {
  const keys = [
    queryKeys.attendanceDaily(ORG, 'g1', '2026-10-21'),
    queryKeys.attendanceSummary(ORG, '2026-10', null),
    queryKeys.absenceClaims(ORG),
    queryKeys.holidays(ORG),
    queryKeys.invoices(ORG),
    queryKeys.children(ORG),
    queryKeys.debtors(ORG),
    queryKeys.dashboard(ORG),
  ] as const satisfies readonly Key[]

  it('refreshes every screen a recount touches', () => {
    const queryClient = client(keys)
    invalidateAttendance(queryClient, ORG)
    expect(stale(queryClient, keys)).toEqual([])
  })
})
