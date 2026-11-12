/**
 * Qoplar va ularning qoldigʻi — "Qaysi puldan" tanlovi uchun (2026-10-14).
 *
 * Komponentdan alohida: hook va hisob-kitob funksiyasi bir faylda,
 * komponentlar boshqasida — React Fast Refresh shuni talab qiladi.
 */

import { useQuery } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { cashApi } from '@/features/cash/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { useCan } from '@/lib/rbac/useCan'

export interface Pot {
  id: string
  name: string
  /** `null` — qoldiqni koʻrishga ruxsat yoʻq; nomi baribir tanlanadi. */
  balance: number | null
  /** Qoldiq ichidagi, bankka hali tushmagan terminal/Click/Payme puli. */
  inTransit: number
}

export function usePots(enabled = true): { pots: Pot[]; isPending: boolean } {
  const organizationId = useOrganizationId()
  const { can } = useCan()
  const accounts = useQuery({
    queryKey: queryKeys.cashAccounts(organizationId),
    queryFn: cashApi.accounts,
    enabled,
  })
  const balances = useQuery({
    queryKey: [...queryKeys.cashAccounts(organizationId), 'balances'],
    queryFn: cashApi.balances,
    enabled: enabled && can('payments.read'),
  })
  const byId = new Map((balances.data ?? []).map((row) => [row.id, Number(row.balance)]))
  const transit = new Map((balances.data ?? []).map((row) => [row.id, Number(row.in_transit ?? 0)]))
  const pots = (accounts.data?.items ?? [])
    .filter((account) => account.is_active)
    .map((account) => ({
      id: account.id,
      name: account.name,
      balance: byId.has(account.id) ? (byId.get(account.id) as number) : null,
      inTransit: transit.get(account.id) ?? 0,
    }))
  return { pots, isPending: accounts.isPending }
}

/**
 * Tanlangan qopda qancha yetmaydi. `credit` — tahrirlashda shu qopga
 * qaytadigan eski summa: avval u qaytadi, keyin yangisi chiqadi.
 */
export function shortfall(pots: Pot[], potId: string, amount: number, credit = 0): number {
  const pot = pots.find((p) => p.id === potId)
  if (!pot || pot.balance === null) return 0
  return Math.max(0, amount - (pot.balance + credit))
}
