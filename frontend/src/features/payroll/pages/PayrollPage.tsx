/**
 * Oylik maosh (docs/04 §11).
 *
 * Oqim bir tomonlama: qoralama → yakunlangan → to'langan. Yakunlangandan
 * keyin tahrirlash yo'q — xato keyingi oyda tuzatuvchi bonus/ushlab qolish
 * bilan hal qilinadi. Bu ledger'dagi qarshi yozuv bilan bir xil mantiq.
 *
 * Xodimlar ro'yxati bu yerda EMAS — u "Xodimlar" sahifasida
 * (`features/staff`). Oylik faqat hisoblashlar bilan ishlaydi.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, CheckCircle2, Lock, Plus, Wallet } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { EmptyRow } from '@/components/ui/EmptyState'
import { payrollApi } from '@/features/payroll/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type PayrollRun } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const money = (v: string) => new Intl.NumberFormat('uz-UZ').format(Number(v))

const STATUS = {
  draft: ['Qoralama', 'bg-slate-100 text-slate-600'],
  finalized: ['Yakunlangan', 'bg-sky-50 text-sky-700'],
  paid: ["To'langan", 'bg-emerald-50 text-emerald-700'],
} as const

export default function PayrollPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const now = new Date()
  const [openRun, setOpenRun] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const runsQuery = useQuery({
    queryKey: queryKeys.payrollRuns(organizationId),
    queryFn: () => payrollApi.listRuns(),
  })
  const runQuery = useQuery({
    queryKey: queryKeys.payrollRun(organizationId, openRun ?? ''),
    queryFn: () => payrollApi.getRun(openRun!),
    enabled: Boolean(openRun),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'payroll'] })
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : 'Xatolik yuz berdi.')

  const createRun = useMutation({
    mutationFn: () => payrollApi.createRun(now.getFullYear(), now.getMonth() + 1),
    onSuccess: (run) => {
      setError(null)
      setOpenRun(run.id)
      invalidate()
    },
    onError: fail,
  })
  const finalize = useMutation({
    mutationFn: (id: string) => payrollApi.finalize(id),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })
  const markPaid = useMutation({
    mutationFn: (id: string) => payrollApi.markPaid(id),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })
  const updateItem = useMutation({
    mutationFn: ({ itemId, field, value }: { itemId: string; field: string; value: string }) =>
      payrollApi.updateItem(openRun!, itemId, { [field]: value || '0' }),
    onSuccess: () => {
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const run: PayrollRun | undefined = runQuery.data
  const periodLabel = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Oylik maosh</h1>
          <p className="mt-1 text-sm text-slate-500">
            Yakunlangan hisoblash o'zgarmaydi — tuzatish keyingi oyda kiritiladi.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {can('payroll.read') && (
            <Link
              to="/staff"
              className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              Xodimlar ro'yxati
              <ArrowUpRight className="h-4 w-4 text-slate-400" />
            </Link>
          )}
          {can('payroll.create') && (
            <button
              type="button"
              onClick={() => createRun.mutate()}
              disabled={createRun.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              <Plus className="h-4 w-4" />
              {periodLabel} uchun hisoblash
            </button>
          )}
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {runsQuery.data?.items.map((r) => {
          const [label, tone] = STATUS[r.status]
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => setOpenRun(r.id)}
              className={cn(
                'rounded-2xl border bg-white p-4 text-left transition hover:border-brand-300',
                openRun === r.id ? 'border-brand-400 ring-2 ring-brand-100' : 'border-slate-200',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="font-semibold text-slate-900 tabular-nums">
                  {r.period_year}-{String(r.period_month).padStart(2, '0')}
                </p>
                <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                  {label}
                </span>
              </div>
              <p className="mt-2 text-lg font-bold text-slate-900 tabular-nums">
                {money(r.total_net)} so'm
              </p>
              <p className="text-xs text-slate-500">{r.items.length} ta xodim</p>
            </button>
          )
        })}
      </div>

      {runsQuery.data?.items.length === 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center">
          <Wallet className="mx-auto mb-3 h-10 w-10 text-slate-200" />
          <p className="text-sm text-slate-500">Hozircha hisoblash yo'q.</p>
          <p className="mt-1 text-xs text-slate-400">
            Avval{' '}
            <Link to="/staff" className="font-medium text-brand-600 hover:underline">
              xodimlarni kiriting
            </Link>
            , keyin joriy oy uchun hisoblashni boshlang.
          </p>
        </div>
      )}

      {run && (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <div className="flex flex-col gap-3 border-b border-slate-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-semibold text-slate-900">
                {run.period_year}-{String(run.period_month).padStart(2, '0')} · {STATUS[run.status][0]}
              </p>
              <p className="text-xs text-slate-500">
                Yalpi {money(run.total_gross)} · ushlab qolindi {money(run.total_deductions)} · sof{' '}
                <strong>{money(run.total_net)}</strong>
              </p>
            </div>
            {can('payroll.update') && (
              <div className="flex gap-2">
                {run.status === 'draft' && (
                  <button
                    type="button"
                    onClick={() => finalize.mutate(run.id)}
                    disabled={finalize.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-60 sm:flex-none"
                  >
                    <Lock className="h-4 w-4" /> Yakunlash
                  </button>
                )}
                {run.status === 'finalized' && (
                  <button
                    type="button"
                    onClick={() => markPaid.mutate(run.id)}
                    disabled={markPaid.isPending}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60 sm:flex-none"
                  >
                    <CheckCircle2 className="h-4 w-4" /> To'langan
                  </button>
                )}
              </div>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Xodim</th>
                  <th className="px-4 py-3 text-right font-medium">Baza</th>
                  <th className="px-4 py-3 text-right font-medium">Bonus</th>
                  <th className="px-4 py-3 text-right font-medium">Ushlab qolish</th>
                  <th className="px-4 py-3 text-right font-medium">Sof</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {run.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-2 font-medium text-slate-800">{item.employee_name}</td>
                    <td className="px-4 py-2 text-right text-slate-600 tabular-nums">
                      {money(item.base_amount)}
                    </td>
                    {(['bonus', 'deduction'] as const).map((field) => (
                      <td key={field} className="px-4 py-2 text-right">
                        {run.is_editable && can('payroll.update') ? (
                          <input
                            type="number"
                            min={0}
                            inputMode="numeric"
                            defaultValue={item[field]}
                            aria-label={field}
                            onBlur={(e) => {
                              if (e.target.value !== item[field]) {
                                updateItem.mutate({ itemId: item.id, field, value: e.target.value })
                              }
                            }}
                            className="w-28 rounded border border-slate-200 px-2 py-1 text-right text-sm outline-none focus:border-brand-500"
                          />
                        ) : (
                          <span className="text-slate-600 tabular-nums">{money(item[field])}</span>
                        )}
                      </td>
                    ))}
                    <td className="px-4 py-2 text-right font-semibold text-slate-900 tabular-nums">
                      {money(item.net)}
                    </td>
                  </tr>
                ))}
                {run.items.length === 0 && (
                  <EmptyRow
                    colSpan={5}
                    icon={Wallet}
                    title="Bu davrda xodim yo'q"
                    hint="Hisoblash yaratilgan paytda ishlayotgan xodim topilmadi. Xodimlar sahifasida ularni kiriting va yangi davr oching."
                  />
                )}
              </tbody>
            </table>
          </div>

          {!run.is_editable && (
            <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
              Hisoblash yakunlangan — tahrirlash yopiq. Tuzatishni keyingi oyda bonus yoki ushlab
              qolish sifatida kiriting.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
