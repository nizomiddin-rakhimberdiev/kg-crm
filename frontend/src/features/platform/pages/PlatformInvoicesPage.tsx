/**
 * Barcha hisob-fakturalar + bank o'tkazmasini qayd etish.
 *
 * MVP'da to'lovlar bank orqali keladi va ularni vendor qo'lda kiritadi.
 * Bir necha o'nlab mijozda bu avtomatlashtirishdan arzonroq va
 * aniqroq (docs/06 §2) — avtomatik to'lov integratsiyasi hajm
 * paydo bo'lganda qo'shiladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { CreditCard } from 'lucide-react'
import { ApiError } from '@/lib/api/types'
import { cn, formatDate, formatUZS } from '@/lib/utils'
import { platform } from '../api'
import { usePlatformAuth } from '../PlatformAuthProvider'

const TONE: Record<string, string> = {
  paid: 'bg-emerald-500/10 text-emerald-400',
  issued: 'border border-tosh-500/40 text-tosh-200',
  overdue: 'bg-red-500/10 text-red-400',
  cancelled: 'bg-slate-700/40 text-slate-400',
}

const FILTERS: Array<[string, string]> = [
  ['', 'Hammasi'],
  ['issued', 'Yozilgan'],
  ['overdue', "Muddati o'tgan"],
  ['paid', "To'langan"],
]

const day = (iso: string) => formatDate(iso)

export default function PlatformInvoicesPage() {
  const queryClient = useQueryClient()
  const { isAdmin } = usePlatformAuth()

  const [status, setStatus] = useState('')
  const [paying, setPaying] = useState<string | null>(null)
  const [amount, setAmount] = useState('')
  const [reference, setReference] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['platform', 'invoices', status],
    queryFn: () => platform.invoices(status || undefined),
  })

  const record = useMutation({
    mutationFn: () => platform.recordPayment(paying!, amount, reference),
    onSuccess: () => {
      setError(null)
      setNotice("To'lov qayd etildi. Obuna faollashtirildi.")
      setPaying(null)
      setAmount('')
      setReference('')
      void queryClient.invalidateQueries({ queryKey: ['platform'] })
    },
    onError: (err: unknown) => {
      setNotice(null)
      setError(err instanceof ApiError ? err.message : "To'lovni yozib bo'lmadi.")
    },
  })

  const rows = data ?? []
  const field =
    'rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-brand-500'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Hisob-fakturalar</h1>
        <p className="mt-1 text-sm text-slate-400">
          Bank o'tkazmasi kelganda uni shu yerdan qayd etasiz.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
          {notice}
        </div>
      )}

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
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Raqam</th>
                <th className="px-4 py-3">Bog'cha</th>
                <th className="px-4 py-3">Yozilgan</th>
                <th className="px-4 py-3">Muddat</th>
                <th className="px-4 py-3 text-right">Summa</th>
                <th className="px-4 py-3">Holat</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900/40">
              {rows.map((invoice) => (
                <tr key={invoice.id}>
                  <td className="px-4 py-3 font-medium">{invoice.number}</td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/platform/organizations/${invoice.organization_id}`}
                      className="hover:text-brand-400"
                    >
                      {invoice.organization}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{day(invoice.issued_at)}</td>
                  <td className="px-4 py-3 text-slate-400">{day(invoice.due_at)}</td>
                  <td className="px-4 py-3 text-right font-semibold">
                    {formatUZS(Number(invoice.total_amount))}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-medium',
                        TONE[invoice.status] ?? 'bg-slate-700/40 text-slate-400',
                      )}
                    >
                      {invoice.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {isAdmin && invoice.status !== 'paid' && invoice.status !== 'cancelled' && (
                      <button
                        type="button"
                        onClick={() => {
                          setPaying(paying === invoice.id ? null : invoice.id)
                          setAmount(invoice.total_amount)
                        }}
                        className="rounded-lg border border-slate-700 px-2.5 py-1 text-xs font-medium hover:bg-slate-800"
                      >
                        To'lov yozish
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {!isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-slate-500">
                    <CreditCard className="mx-auto mb-2 h-6 w-6" />
                    Hisob topilmadi.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {paying && (
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="text-sm font-semibold">Kelgan o'tkazmani qayd etish</h2>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="text-xs text-slate-400">
              Summa
              <input
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className={`${field} mt-1 block w-44`}
              />
            </label>
            <label className="text-xs text-slate-400">
              Bank hujjati raqami
              <input
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="MT-102"
                className={`${field} mt-1 block w-52`}
              />
            </label>
            <button
              type="button"
              disabled={record.isPending || !amount}
              onClick={() => record.mutate()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              Qayd etish
            </button>
            <button
              type="button"
              onClick={() => setPaying(null)}
              className="px-3 py-2 text-sm text-slate-400 hover:text-slate-200"
            >
              Bekor qilish
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Ortiqcha to'lov qabul qilinmaydi — qoldiqdan katta summa rad etiladi.
          </p>
        </section>
      )}
    </div>
  )
}
