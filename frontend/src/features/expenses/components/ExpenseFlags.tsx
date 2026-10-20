/**
 * Chiqim yonidagi belgilar (Bosqich 13.2a–13.3a): nasiya (toʻlanmagan
 * boʻlsa — toʻlash), investitsiya, boshqa oyning xarajati, chek.
 * Roʻyxatning ikkala koʻrinishida (mobil va jadval) bir xil.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Paperclip } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { cashApi } from '@/features/cash/api'
import { expensesApi } from '@/features/expenses/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError, type Expense } from '@/lib/api/types'
import { formatDate } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'

const chip = 'rounded-full px-2 py-0.5 text-xs font-medium'

export function ExpenseFlags({ expense }: { expense: Expense }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const [paying, setPaying] = useState(false)
  const [potId, setPotId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const accounts = useQuery({
    queryKey: ['org', organizationId, 'cash', 'accounts'],
    queryFn: cashApi.accounts,
    enabled: paying,
  })
  const pots = (accounts.data?.items ?? []).filter(
    (account) => account.is_active && (account.kind === 'cash' || account.kind === 'bank'),
  )
  const pot = potId || pots.find((row) => row.kind === 'bank')?.id || ''
  const pay = useMutation({
    mutationFn: () => expensesApi.payCredit(expense.id, pot),
    onSuccess: () => {
      setPaying(false)
      invalidateMoney(queryClient, organizationId)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const unpaidCredit = expense.on_credit && !expense.paid_on
  const otherMonth = expense.period && !expense.expense_date.startsWith(expense.period)

  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {unpaidCredit && (
        <span className={`${chip} bg-orik-50 text-orik-700`}>
          {expense.due_date
            ? t('Nasiya · {date} gacha', { date: formatDate(expense.due_date) })
            : t('Nasiya · toʻlanmagan')}
        </span>
      )}
      {expense.on_credit && expense.paid_on && (
        <span className={`${chip} bg-slate-100 text-slate-600`}>
          {t('Nasiya toʻlandi {date}', { date: formatDate(expense.paid_on) })}
        </span>
      )}
      {expense.is_capex && (
        <span className={`${chip} bg-slate-100 text-slate-700`}>
          {expense.amortize_months
            ? t('Investitsiya · {n} oyga', { n: expense.amortize_months })
            : t('Investitsiya')}
        </span>
      )}
      {otherMonth && (
        <span className={`${chip} bg-slate-100 text-slate-700`}>
          {t('{month} xarajati', { month: expense.period })}
        </span>
      )}
      {expense.has_receipt && (
        <a
          href={`/api/v1/expenses/${expense.id}/receipt/download`}
          onClick={async (event) => {
            event.preventDefault()
            // Oyna BOSISH paytida ochiladi: fayl kelgandan keyin ochilgan
            // oynani Safari bloklaydi ("Pop-up Window Blocked").
            const tab = window.open('', '_blank')
            const { httpClient } = await import('@/lib/api/client')
            try {
              const response = await httpClient.get(`/expenses/${expense.id}/receipt/download`, {
                responseType: 'blob',
              })
              const url = URL.createObjectURL(response.data as Blob)
              if (tab && !tab.closed) tab.location.href = url
              else window.location.href = url
            } catch {
              tab?.close()
            }
          }}
          className="inline-flex items-center gap-0.5 text-xs text-slate-600 underline-offset-2 hover:underline"
        >
          <Paperclip className="h-3 w-3" />
          {t('Chek')}
        </a>
      )}
      {unpaidCredit && can('expenses.update') && !paying && (
        <button
          type="button"
          onClick={() => setPaying(true)}
          className="text-xs font-medium text-brand-700 hover:underline"
        >
          {t('Toʻlash')}
        </button>
      )}
      {paying && (
        <span className="flex items-center gap-1.5">
          <select
            aria-label={t('Qaysi puldan')}
            value={pot}
            onChange={(event) => setPotId(event.target.value)}
            className="rounded-md border border-slate-200 px-2 py-1 text-xs"
          >
            {pots.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={!pot || pay.isPending}
            onClick={() => pay.mutate()}
            className="rounded-md bg-brand-600 px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
          >
            {t('Toʻlandi')}
          </button>
        </span>
      )}
      {error && (
        <span role="alert" className="text-xs text-red-700">
          {error}
        </span>
      )}
    </span>
  )
}
