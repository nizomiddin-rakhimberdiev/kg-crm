/**
 * Oylik maosh (docs/04 §11).
 *
 * Oqim bir tomonlama: qoralama → yakunlangan → to'langan. Yakunlangandan
 * keyin tahrirlash yo'q — xato keyingi oyda tuzatuvchi bonus/ushlab qolish
 * bilan hal qilinadi. Bu ledger'dagi qarshi yozuv bilan bir xil mantiq.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Lock, Plus, UserPlus, Wallet } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { employeesApi, payrollApi, positionsApi } from '@/features/payroll/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type PayrollRun } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { EmptyRow } from '@/components/ui/EmptyState'

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
  const [tab, setTab] = useState<'runs' | 'employees'>('runs')
  const [openRun, setOpenRun] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [empForm, setEmpForm] = useState({
    first_name: '', last_name: '', hire_date: '', base_salary: '', position_id: '',
  })

  const runsQuery = useQuery({
    queryKey: queryKeys.payrollRuns(organizationId),
    queryFn: () => payrollApi.listRuns(),
  })
  const employeesQuery = useQuery({
    queryKey: queryKeys.employees(organizationId),
    queryFn: () => employeesApi.list(),
  })
  const positionsQuery = useQuery({
    queryKey: queryKeys.positions(organizationId),
    queryFn: positionsApi.list,
  })
  const runQuery = useQuery({
    queryKey: queryKeys.payrollRun(organizationId, openRun ?? ''),
    queryFn: () => payrollApi.getRun(openRun!),
    enabled: Boolean(openRun),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'payroll'] })
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'employees'] })
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : 'Xatolik yuz berdi.')

  const createRun = useMutation({
    mutationFn: () => payrollApi.createRun(now.getFullYear(), now.getMonth() + 1),
    onSuccess: (run) => { setError(null); setOpenRun(run.id); invalidate() },
    onError: fail,
  })
  const finalize = useMutation({
    mutationFn: (id: string) => payrollApi.finalize(id),
    onSuccess: () => { setError(null); invalidate() },
    onError: fail,
  })
  const markPaid = useMutation({
    mutationFn: (id: string) => payrollApi.markPaid(id),
    onSuccess: () => { setError(null); invalidate() },
    onError: fail,
  })
  const updateItem = useMutation({
    mutationFn: ({ itemId, field, value }: { itemId: string; field: string; value: string }) =>
      payrollApi.updateItem(openRun!, itemId, { [field]: value || '0' }),
    onSuccess: () => { setError(null); invalidate() },
    onError: fail,
  })
  const createEmployee = useMutation({
    mutationFn: () =>
      employeesApi.create({
        ...empForm,
        position_id: empForm.position_id || null,
      }),
    onSuccess: () => {
      setEmpForm({ first_name: '', last_name: '', hire_date: '', base_salary: '', position_id: '' })
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const run: PayrollRun | undefined = runQuery.data

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Oylik maosh</h1>
        <p className="mt-1 text-sm text-slate-500">
          Yakunlangan hisoblash o'zgarmaydi — tuzatish keyingi oyda kiritiladi.
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {([['runs', 'Hisoblashlar'], ['employees', 'Xodimlar']] as const).map(([key, label]) => (
          <button key={key} type="button" onClick={() => setTab(key)}
            className={cn('-mb-px border-b-2 px-4 py-2 text-sm font-medium transition',
              tab === key ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-800')}>
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      )}

      {tab === 'runs' && (
        <>
          {can('payroll.create') && (
            <button type="button" onClick={() => createRun.mutate()} disabled={createRun.isPending}
              className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60">
              <Plus className="h-4 w-4" />
              {`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')} uchun hisoblash`}
            </button>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {runsQuery.data?.items.map((r) => {
              const [label, tone] = STATUS[r.status]
              return (
                <button key={r.id} type="button" onClick={() => setOpenRun(r.id)}
                  className={cn('rounded-2xl border bg-white p-4 text-left transition hover:border-brand-300',
                    openRun === r.id ? 'border-brand-400' : 'border-slate-200')}>
                  <div className="flex items-center justify-between">
                    <p className="font-semibold text-slate-900">
                      {r.period_year}-{String(r.period_month).padStart(2, '0')}
                    </p>
                    <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>{label}</span>
                  </div>
                  <p className="mt-2 text-lg font-bold text-slate-900">{money(r.total_net)} so'm</p>
                  <p className="text-xs text-slate-500">{r.items.length} ta xodim</p>
                </button>
              )
            })}
          </div>

          {runsQuery.data?.items.length === 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center">
              <Wallet className="mx-auto mb-3 h-10 w-10 text-slate-200" />
              <p className="text-sm text-slate-500">Hozircha hisoblash yo'q.</p>
            </div>
          )}

          {run && (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
                <div>
                  <p className="font-semibold text-slate-900">
                    {run.period_year}-{String(run.period_month).padStart(2, '0')} · {STATUS[run.status][0]}
                  </p>
                  <p className="text-xs text-slate-500">
                    Yalpi {money(run.total_gross)} · ushlab qolindi {money(run.total_deductions)} ·
                    sof <strong>{money(run.total_net)}</strong>
                  </p>
                </div>
                {can('payroll.update') && (
                  <div className="flex gap-2">
                    {run.status === 'draft' && (
                      <button type="button" onClick={() => finalize.mutate(run.id)}
                        className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold text-white hover:bg-sky-700">
                        <Lock className="h-4 w-4" /> Yakunlash
                      </button>
                    )}
                    {run.status === 'finalized' && (
                      <button type="button" onClick={() => markPaid.mutate(run.id)}
                        className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700">
                        <CheckCircle2 className="h-4 w-4" /> To'langan
                      </button>
                    )}
                  </div>
                )}
              </div>

              <table className="w-full text-sm">
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
                      <td className="px-4 py-2 text-right text-slate-600">{money(item.base_amount)}</td>
                      {(['bonus', 'deduction'] as const).map((field) => (
                        <td key={field} className="px-4 py-2 text-right">
                          {run.is_editable && can('payroll.update') ? (
                            <input type="number" min={0} defaultValue={item[field]}
                              aria-label={field}
                              onBlur={(e) => {
                                if (e.target.value !== item[field]) {
                                  updateItem.mutate({ itemId: item.id, field, value: e.target.value })
                                }
                              }}
                              className="w-28 rounded border border-slate-200 px-2 py-1 text-right text-sm outline-none focus:border-brand-500" />
                          ) : (
                            <span className="text-slate-600">{money(item[field])}</span>
                          )}
                        </td>
                      ))}
                      <td className="px-4 py-2 text-right font-semibold text-slate-900">{money(item.net)}</td>
                    </tr>
                  ))}
                  {run.items.length === 0 && (
                    <EmptyRow
                      colSpan={11}
                      icon={Wallet}
                      title="Oylik hisoblanmagan"
                      hint="Xodimlar va lavozimlar kiritilgach, oylik hisoblash davrini shu yerdan boshlaysiz."
                    />
                  )}
                </tbody>
              </table>

              {!run.is_editable && (
                <p className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
                  Hisoblash yakunlangan — tahrirlash yopiq. Tuzatishni keyingi oyda
                  bonus yoki ushlab qolish sifatida kiriting.
                </p>
              )}
            </div>
          )}
        </>
      )}

      {tab === 'employees' && (
        <>
          {can('payroll.create') && (
            <form onSubmit={(e) => { e.preventDefault(); createEmployee.mutate() }}
              className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-3">
              {([['last_name', 'Familiya', 'text'], ['first_name', 'Ism', 'text'],
                 ['hire_date', 'Ishga kirgan sana', 'date'], ['base_salary', 'Oylik maosh', 'number']] as const
              ).map(([key, label, type]) => (
                <div key={key}>
                  <label htmlFor={key} className="mb-1 block text-xs font-medium text-slate-600">{label}</label>
                  <input id={key} type={type} required value={empForm[key]}
                    onChange={(e) => setEmpForm((p) => ({ ...p, [key]: e.target.value }))}
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500" />
                </div>
              ))}
              <div>
                <label htmlFor="position" className="mb-1 block text-xs font-medium text-slate-600">Lavozim</label>
                <select id="position" value={empForm.position_id}
                  onChange={(e) => setEmpForm((p) => ({ ...p, position_id: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500">
                  <option value="">—</option>
                  {positionsQuery.data?.items.map((p) => (
                    <option key={p.id} value={p.id}>{p.title}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <button type="submit" disabled={createEmployee.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60">
                  <UserPlus className="h-4 w-4" /> Qo'shish
                </button>
              </div>
            </form>
          )}

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Xodim</th>
                  <th className="px-4 py-3 font-medium">Lavozim</th>
                  <th className="px-4 py-3 font-medium">Holat</th>
                  <th className="px-4 py-3 text-right font-medium">Maosh</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {employeesQuery.data?.items.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-800">{e.full_name}</td>
                    <td className="px-4 py-3 text-slate-600">{e.position_title ?? '—'}</td>
                    <td className="px-4 py-3">
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium',
                        e.employment_status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500')}>
                        {e.employment_status === 'active' ? 'Ishlayapti'
                          : e.employment_status === 'on_leave' ? "Ta'tilda" : 'Bo\'shagan'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-slate-700">{money(e.base_salary)} so'm</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {employeesQuery.data?.items.length === 0 && (
              <p className="px-4 py-12 text-center text-sm text-slate-400">Xodimlar yo'q.</p>
            )}
          </div>
        </>
      )}
    </div>
  )
}
