/**
 * Obuna bo'lgan bog'chalar ro'yxati — **faqat metama'lumot** (docs/04 §19).
 *
 * Bu yerda bolalar SONI ko'rinadi, ro'yxati emas. Farq katta: son
 * biznesni boshqarish uchun kerak, ro'yxat esa hech qachon kerak emas
 * va u sizib chiqadigan narsa. Backend ham, baza ham (RLS) shu
 * chegarani mustaqil ravishda qo'llaydi.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Building2, Search } from 'lucide-react'
import { cn, formatUZS } from '@/lib/utils'
import { platform } from '../api'
import { usePlatformAuth } from '../PlatformAuthProvider'
import { NewOrganizationDialog } from '../components/NewOrganizationDialog'

export const STATUS_LABEL: Record<string, [string, string]> = {
  trialing: ['Sinov davri', 'bg-sky-500/10 text-sky-400'],
  pending_payment: ["To'lov kutilmoqda", 'bg-amber-500/10 text-amber-400'],
  active: ['Faol', 'bg-emerald-500/10 text-emerald-400'],
  past_due: ["Muddati o'tgan", 'bg-amber-500/10 text-amber-300'],
  suspended: ["To'xtatilgan", 'bg-red-500/10 text-red-400'],
}

const FILTERS: Array<[string, string]> = [
  ['', 'Hammasi'],
  ['trialing', 'Sinov'],
  ['active', 'Faol'],
  ['past_due', "Muddati o'tgan"],
  ['suspended', "To'xtatilgan"],
]

/**
 * Oylik hisob — plan bo'yicha (500 000 + har 10 bolaga 80 000).
 *
 * Bu **taxminiy** ko'rsatkich: haqiqiy hisob yopilgan `usage_snapshot`
 * dan chiqadi. Shuning uchun ustun nomi ham "taxminiy".
 */
const monthlyEstimate = (children: number): number => {
  const base = 500_000
  const included = 50
  const steps = Math.ceil(Math.max(0, children - included) / 10)
  return base + steps * 80_000
}

export default function PlatformOrganizationsPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  // Yangi tenant — yangi obuna va o'chirilmaydigan ma'lumot; buni faqat
  // administrator ochadi (backend ham shuni talab qiladi).
  const { isAdmin } = usePlatformAuth()

  const { data, isLoading } = useQuery({
    queryKey: ['platform', 'organizations', search, status],
    queryFn: () => platform.organizations({ search, status }),
  })

  const rows = data ?? []
  const mrr = rows
    .filter((row) => row.subscription?.status === 'active')
    .reduce((sum, row) => sum + monthlyEstimate(row.billable_children), 0)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Bog'chalar</h1>
          <p className="mt-1 text-sm text-slate-400">
            {rows.length} ta tashkilot · faol obunalardan taxminiy oylik: {formatUZS(mrr)}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Nomi bo'yicha qidirish"
              className="w-64 rounded-lg border border-slate-800 bg-slate-900 py-2 pl-9 pr-3 text-sm outline-none placeholder:text-slate-600 focus:border-brand-500"
            />
          </div>
          {isAdmin && <NewOrganizationDialog />}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {FILTERS.map(([key, label]) => (
          <button
            key={key || 'all'}
            type="button"
            onClick={() => setStatus(key)}
            className={cn(
              'rounded-lg px-3 py-1.5 text-sm font-medium',
              status === key
                ? 'bg-slate-100 text-slate-900'
                : 'bg-slate-900 text-slate-400 hover:bg-slate-800',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Bog'cha</th>
              <th className="px-4 py-3">Holat</th>
              <th className="px-4 py-3 text-right">Bolalar</th>
              <th className="px-4 py-3 text-right">Taxminiy oylik</th>
              <th className="px-4 py-3">Muddat</th>
              <th className="px-4 py-3">Davr tugashi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900/40">
            {rows.map((row) => {
              const subscription = row.subscription
              const [label, tone] = STATUS_LABEL[subscription?.status ?? ''] ?? [
                'Obunasiz',
                'bg-slate-700/40 text-slate-400',
              ]
              return (
                <tr key={row.id} className="hover:bg-slate-900">
                  <td className="px-4 py-3">
                    <Link
                      to={`/platform/organizations/${row.id}`}
                      className="font-medium hover:text-brand-400"
                    >
                      {row.name}
                    </Link>
                    <p className="text-xs text-slate-500">{row.contact_email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                      {label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">{row.billable_children}</td>
                  <td className="px-4 py-3 text-right">
                    {subscription ? formatUZS(monthlyEstimate(row.billable_children)) : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {subscription?.payment_term ?? '—'}
                    {subscription && Number(subscription.discount_percent) > 0 && (
                      <span className="ml-1 text-emerald-400">
                        −{Number(subscription.discount_percent)}%
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {subscription?.current_period_end ?? '—'}
                  </td>
                </tr>
              )
            })}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                  <Building2 className="mx-auto mb-2 h-6 w-6" />
                  Tashkilot topilmadi.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
