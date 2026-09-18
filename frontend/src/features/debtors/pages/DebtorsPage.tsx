/**
 * Qarzdorlar — **hisoblangan ro'yxat**, jadval emas (ADR-7).
 *
 * Ro'yxat har safar ledger'dan hisoblanadi. Shuning uchun u kesh siljisa
 * ham to'g'ri qoladi — bu muhim, chunki noto'g'ri qarzdorlar ro'yxati eng
 * yomon joyda chiqardi: ota-onadan pul talab qilishda.
 */

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, ChevronRight, Phone, Sparkles } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { overdueDaysFromSearch, filterByOverdueDays } from '@/features/debtors/overdueDays'
import { fill, getCopy } from '@/features/intelligence/content'
import { Modal } from '@/components/ui/Modal'
import { debtorsApi } from '@/features/payments/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { EmptyRow } from '@/components/ui/EmptyState'

const money = (value: string) =>
  new Intl.NumberFormat('uz-UZ').format(Number(value)) + " so'm"

function StatementDrawer({ childId, onClose }: { childId: string; onClose: () => void }) {
  const organizationId = useOrganizationId()
  const query = useQuery({
    queryKey: queryKeys.statement(organizationId, childId),
    queryFn: () => debtorsApi.statement(childId),
  })

  return (
    <Modal open onClose={onClose} className="max-w-2xl">
      <div className="p-6">
        <div className="mb-4 pr-10">
          <h2 className="text-lg font-bold text-slate-900">
            {query.data?.child.full_name ?? 'Ko\'chirma'}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Moliyaviy ko'chirma — har bir harakat ledger'dan
          </p>
        </div>

        {query.isPending && (
          <p className="py-8 text-center text-sm text-slate-400">Yuklanmoqda…</p>
        )}

        {query.data && (
          <>
            <div className="mb-4 rounded-lg bg-red-50 px-3 py-2">
              <span className="text-sm text-red-700">Joriy qarz: </span>
              <span className="font-bold text-red-900">{money(query.data.balance)}</span>
            </div>

            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="py-2 font-medium">Sana</th>
                  <th className="py-2 font-medium">Izoh</th>
                  <th className="py-2 text-right font-medium">Summa</th>
                  <th className="py-2 text-right font-medium">Qoldiq</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {query.data.entries.map((entry) => (
                  <tr key={entry.id}>
                    <td className="py-2 text-xs text-slate-500">
                      {entry.occurred_at.slice(0, 10)}
                    </td>
                    <td className="py-2 text-slate-700">{entry.description || entry.entry_type}</td>
                    <td
                      className={cn(
                        'py-2 text-right font-medium',
                        entry.direction === 'debit' ? 'text-red-700' : 'text-emerald-700',
                      )}
                    >
                      {entry.direction === 'debit' ? '+' : '−'}
                      {money(entry.amount)}
                    </td>
                    <td className="py-2 text-right text-slate-500">
                      {money(entry.running_balance)}
                    </td>
                  </tr>
                ))}
                {query.data.entries.length === 0 && (
                  <EmptyRow
                    colSpan={12}
                    icon={CheckCircle2}
                    title="Qarzdor yo'q"
                    hint="Hamma to'lagan. Muddati o'tgan hisob-faktura paydo bo'lsa, bola shu ro'yxatga tushadi."
                  />
                )}
              </tbody>
            </table>
          </>
        )}
      </div>
    </Modal>
  )
}

export default function DebtorsPage() {
  const organizationId = useOrganizationId()
  const [searchParams, setSearchParams] = useSearchParams()
  // Radix AI deep link (docs/07 §8): `?overdue_days=15` — "faqat muddati
  // o'tganlar" yoqiladi va ro'yxat N kundan eskilarga toraytiriladi.
  const overdueDays = overdueDaysFromSearch(searchParams)
  const [overdueOnlyChoice, setOverdueOnly] = useState(false)
  const overdueOnly = overdueOnlyChoice || overdueDays !== null
  const [openChild, setOpenChild] = useState<string | null>(null)

  const params = overdueOnly ? { overdue: 'true' } : undefined
  const debtorsQuery = useQuery({
    queryKey: queryKeys.debtors(organizationId, params),
    queryFn: () => debtorsApi.list(params),
  })

  const rows = useMemo(
    () =>
      debtorsQuery.data
        ? filterByOverdueDays(debtorsQuery.data.results, overdueDays, new Date())
        : [],
    [debtorsQuery.data, overdueDays],
  )
  const aiCopy = getCopy().debtors

  return (
    <div className="space-y-6">
      {openChild && <StatementDrawer childId={openChild} onClose={() => setOpenChild(null)} />}

      {overdueDays !== null && (
        <div
          role="status"
          className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-brand-100 bg-brand-50 px-3 py-2 text-sm text-brand-800"
        >
          <Sparkles className="h-4 w-4 shrink-0" />
          <span>{fill(aiCopy.banner, { days: overdueDays })}</span>
          <button
            type="button"
            className="ml-auto min-h-11 font-medium underline-offset-2 hover:underline"
            onClick={() => setSearchParams({})}
          >
            {aiCopy.showAll}
          </button>
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Qarzdorlar</h1>
          <p className="mt-1 text-sm text-slate-500">
            Ro'yxat ledger'dan hisoblanadi — u hech qachon haqiqatdan ajralmaydi.
          </p>
        </div>
        {debtorsQuery.data && debtorsQuery.data.count > 0 && (
          <div className="text-right">
            <p className="text-xs text-slate-500">Jami qarz</p>
            <p className="text-xl font-bold text-red-700">
              {money(debtorsQuery.data.total_debt)}
            </p>
          </div>
        )}
      </div>

      <label className="flex w-fit cursor-pointer items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={overdueOnly}
          disabled={overdueDays !== null}
          onChange={(e) => setOverdueOnly(e.target.checked)}
        />
        Faqat muddati o'tganlar
      </label>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {debtorsQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">Yuklanmoqda…</p>
        )}
        {debtorsQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-red-600">
            {debtorsQuery.error instanceof ApiError
              ? debtorsQuery.error.message
              : "Ma'lumotni yuklab bo'lmadi."}
          </p>
        )}
        {debtorsQuery.data && rows.length === 0 && (
          <div className="px-4 py-12 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm text-slate-500">Qarzdorlar yo'q.</p>
          </div>
        )}

        {debtorsQuery.data && rows.length > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Bola</th>
                <th className="px-4 py-3 font-medium">Guruh</th>
                <th className="px-4 py-3 font-medium">Vasiy</th>
                <th className="px-4 py-3 font-medium">Eng eski muddat</th>
                <th className="px-4 py-3 text-right font-medium">Qarz</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => (
                <tr
                  key={row.child.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => setOpenChild(row.child.id)}
                >
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {row.child.full_name}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{row.child.group ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {row.primary_guardian ? (
                      <>
                        <p>{row.primary_guardian.full_name}</p>
                        <p className="flex items-center gap-1 text-xs text-slate-400">
                          <Phone className="h-3 w-3" />
                          {row.primary_guardian.phone}
                        </p>
                      </>
                    ) : (
                      <span className="text-amber-700">vasiy yo'q</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {row.oldest_overdue_date ? (
                      <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                        {row.oldest_overdue_date}
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">muddati kelmagan</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-red-700">
                    {money(row.balance)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ChevronRight className="ml-auto h-4 w-4 text-slate-300" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
