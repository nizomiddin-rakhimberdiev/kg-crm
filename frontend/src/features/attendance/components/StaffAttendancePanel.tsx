/**
 * Xodimlar davomati — kunlik belgilash va oylik tabel (docs/04 §8.3).
 *
 * Mijoz so'rovi: oy oxirida oylik hisobotini chiqarish oson bo'lsin.
 * "Kunlik" — har kuni kim keldi; "Oylik tabel" — buxgalter ochadigan
 * jadval: xodim × kun, jami va o'sha xodimning shu oydagi ish kunlari,
 * Excel'ga yuklab olish bilan.
 *
 * Filial — topbar tanlovi (ega uchun). Filialga bog'langan xodimga backend
 * baribir faqat o'z filialini beradi.
 */

import { useMemo, useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Download, FileDown, HeartPulse, Palmtree, RefreshCw, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { staffAttendanceApi } from '@/features/attendance/api'
import { reportsApi } from '@/features/dashboard/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type StaffAttendanceStatus } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const STATUSES: Array<{
  value: StaffAttendanceStatus
  label: string
  code: string
  icon: typeof Check
  active: string
  cell: string
}> = [
  {
    value: 'present',
    label: t('Keldi'),
    code: t('K'),
    icon: Check,
    active: 'bg-emerald-600 text-white',
    cell: 'bg-emerald-50 text-emerald-700',
  },
  {
    value: 'absent',
    label: t('Kelmadi'),
    code: t('Y'),
    icon: X,
    active: 'bg-red-600 text-white',
    cell: 'bg-red-50 text-red-700',
  },
  {
    value: 'sick',
    label: t('Kasal'),
    code: t('B'),
    icon: HeartPulse,
    active: 'bg-amber-500 text-white',
    cell: 'bg-amber-50 text-amber-700',
  },
  {
    value: 'leave',
    label: t('Taʼtilda'),
    code: t('T'),
    icon: Palmtree,
    active: 'bg-ildiz-700 text-white',
    cell: 'bg-ildiz-50 text-ildiz-800',
  },
]
const BY_VALUE = Object.fromEntries(STATUSES.map((s) => [s.value, s])) as Record<
  StaffAttendanceStatus,
  (typeof STATUSES)[number]
>

/** Mahalliy sana — `toISOString()` UTC'ga o'giradi va kechqurun ertangi kun chiqadi. */
const localISO = (date = new Date()) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function StaffAttendancePanel() {
  const [view, setView] = useState<'daily' | 'timesheet'>('daily')
  return (
    <div className="space-y-4">
      <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
        {(
          [
            ['daily', t('Kunlik belgilash')],
            ['timesheet', t('Oylik tabel')],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setView(key)}
            className={cn(
              'rounded-md px-3 py-1.5 text-sm font-medium transition',
              view === key
                ? 'bg-white text-brand-700 shadow-sm'
                : 'text-slate-500 hover:text-slate-800',
            )}
          >
            {label}
          </button>
        ))}
      </div>
      {view === 'daily' ? <DailyStaff /> : <Timesheet />}
    </div>
  )
}

function DailyStaff() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { selectedBranchId } = useBranchScope()
  const { can } = useCan()
  const editable = can('attendance.create')

  const [date, setDate] = useState(localISO())
  // Qoralama: xodim → holat. Server holati ustiga yoziladi, "Saqlash"da yuboriladi.
  const [draft, setDraft] = useState<Record<string, StaffAttendanceStatus>>({})
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const query = useQuery({
    queryKey: queryKeys.staffDaily(organizationId, date, selectedBranchId),
    queryFn: () => staffAttendanceApi.daily(date, selectedBranchId),
  })
  const rows = query.data?.rows ?? []

  const current = (employeeId: string, fallback: StaffAttendanceStatus | null) =>
    draft[employeeId] ?? fallback
  const changed = rows.filter(
    (row) => draft[row.employee_id] && draft[row.employee_id] !== row.status,
  )
  const unmarked = rows.filter((row) => !current(row.employee_id, row.status)).length

  const save = useMutation({
    mutationFn: () =>
      staffAttendanceApi.markBulk(
        date,
        changed.map((row) => ({ employee_id: row.employee_id, status: draft[row.employee_id] })),
        selectedBranchId,
      ),
    onSuccess: () => {
      setDraft({})
      setError(null)
      setSaved(true)
      void queryClient.invalidateQueries({
        queryKey: ['org', organizationId, 'staff-attendance'],
      })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Saqlab boʻlmadi.')),
  })

  const markRest = () => {
    // "Qolganlar keldi" — belgilanmaganlarga; ta'tildagi xodimga "Ta'tilda".
    setDraft((prev) => {
      const next = { ...prev }
      for (const row of rows) {
        if (!current(row.employee_id, row.status)) {
          next[row.employee_id] = row.on_leave ? 'leave' : 'present'
        }
      }
      return next
    })
    setSaved(false)
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs font-medium text-slate-600">
          {t('Sana')}
          <input
            type="date"
            max={localISO()}
            value={date}
            onChange={(e) => {
              setDate(e.target.value)
              setDraft({})
              setSaved(false)
            }}
            className="mt-1 block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </label>
        {editable && rows.length > 0 && (
          <div className="flex flex-wrap gap-2 sm:ml-auto">
            <button
              type="button"
              onClick={markRest}
              disabled={unmarked === 0}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
            >
              {t('Qolganlar keldi')}
            </button>
            <button
              type="button"
              onClick={() => save.mutate()}
              disabled={changed.length === 0 || save.isPending}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              {save.isPending
                ? t('Saqlanmoqda…')
                : changed.length > 0
                  ? t('Saqlash ({v})', { v: changed.length })
                  : t('Saqlash')}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      {saved && changed.length === 0 && (
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {t('Saqlandi.')}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {query.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
        )}
        {query.data && rows.length === 0 && (
          <p className="px-4 py-10 text-center text-sm text-slate-500">
            {t('Bu kuni ishlaydigan xodim yoʻq. Xodimlarni «Xodimlar» boʻlimida kiriting.')}
          </p>
        )}
        {rows.length > 0 && (
          <p className="border-b border-slate-100 px-4 py-2 text-xs text-slate-500">
            {t('{n} ta xodim · belgilanmagan: {u}', { n: rows.length, u: unmarked })}
          </p>
        )}
        <ul className="divide-y divide-slate-100">
          {rows.map((row) => {
            const value = current(row.employee_id, row.status)
            return (
              <li
                key={row.employee_id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              >
                <span className="min-w-0">
                  <span
                    className={cn(
                      'block truncate text-sm font-medium',
                      value ? 'text-slate-800' : 'text-slate-400',
                    )}
                  >
                    {row.full_name}
                  </span>
                  <span className="block truncate text-xs text-slate-400">
                    {row.position ?? '—'}
                    {row.on_leave && ` · ${t('kartada: taʼtilda')}`}
                  </span>
                </span>
                <div className="flex gap-1">
                  {STATUSES.map(({ value: option, label, icon: Icon, active }) => (
                    <button
                      key={option}
                      type="button"
                      title={label}
                      aria-label={label}
                      aria-pressed={value === option}
                      disabled={!editable}
                      onClick={() => {
                        setDraft((prev) => ({ ...prev, [row.employee_id]: option }))
                        setSaved(false)
                      }}
                      className={cn(
                        'flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition',
                        value === option ? active : 'bg-slate-50 text-slate-500 hover:bg-slate-100',
                        !editable && 'cursor-not-allowed opacity-60',
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">{label}</span>
                    </button>
                  ))}
                </div>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}

function Timesheet() {
  const organizationId = useOrganizationId()
  const { selectedBranchId } = useBranchScope()
  const { can } = useCan()
  const [month, setMonth] = useState(localISO().slice(0, 7))
  const [exportId, setExportId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const query = useQuery({
    queryKey: queryKeys.staffTimesheet(organizationId, month, selectedBranchId),
    queryFn: () => staffAttendanceApi.timesheet(month, selectedBranchId),
    placeholderData: keepPreviousData,
  })
  const sheet = query.data

  // Eksport fonda tayyorlanadi; tayyor bo'lguncha holatni so'rab turamiz.
  const exportsQuery = useQuery({
    queryKey: queryKeys.reportExports(organizationId),
    queryFn: reportsApi.listExports,
    enabled: Boolean(exportId),
    refetchInterval: (q) => {
      const job = (q.state.data ?? []).find((row) => row.id === exportId)
      return job && (job.status === 'ready' || job.status === 'failed') ? false : 2000
    },
  })
  const job = (exportsQuery.data ?? []).find((row) => row.id === exportId)

  const requestExport = useMutation({
    mutationFn: () => {
      const [year, monthNumber] = month.split('-').map(Number)
      return reportsApi.requestExport('staff-attendance', {
        year,
        month: monthNumber,
        ...(selectedBranchId ? { branch_id: selectedBranchId } : {}),
      })
    },
    onSuccess: (created) => {
      setError(null)
      setExportId(created.id)
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.message : t('Eksportni boshlab boʻlmadi.')),
  })

  const workingSet = useMemo(
    () => new Set((sheet?.working_dates ?? []).map((iso) => Number(iso.slice(8, 10)))),
    [sheet?.working_dates],
  )
  const days = Array.from({ length: sheet?.days_in_month ?? 0 }, (_, i) => i + 1)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-xs font-medium text-slate-600">
          {t('Oy')}
          <input
            type="month"
            max={localISO().slice(0, 7)}
            value={month}
            onChange={(e) => {
              if (e.target.value) {
                setMonth(e.target.value)
                setExportId(null)
              }
            }}
            className="mt-1 block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </label>
        {/* Eksport — hisobot eksporti ruxsati bilan (davomatni ko'rish
            ruxsati ham kerak; backend ikkalasini tekshiradi). */}
        {can('reports.export') && (
          <div className="flex items-center gap-2 sm:ml-auto">
            {job?.is_ready ? (
              <button
                type="button"
                onClick={() => void reportsApi.downloadExport(job.id, `tabel-${month}.xlsx`)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700"
              >
                <Download className="h-4 w-4" />
                {t('Yuklab olish')}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => requestExport.mutate()}
                disabled={
                  requestExport.isPending || (Boolean(exportId) && job?.status !== 'failed')
                }
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                {exportId && job?.status !== 'failed' ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <FileDown className="h-4 w-4" />
                )}
                {exportId && job?.status !== 'failed'
                  ? t('Tayyorlanmoqda…')
                  : t('Excelʼga yuklash')}
              </button>
            )}
          </div>
        )}
      </div>

      {(error || job?.status === 'failed') && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error ?? job?.error ?? t('Eksport tayyorlanmadi.')}
        </div>
      )}

      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
        {STATUSES.map((status) => (
          <span key={status.value} className="inline-flex items-center gap-1.5">
            <span
              className={cn(
                'grid h-5 w-5 place-items-center rounded text-xs font-bold',
                status.cell,
              )}
            >
              {status.code}
            </span>
            {status.label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <span className="h-5 w-5 rounded bg-slate-100" />
          {t('dam olish / bayram')}
        </span>
      </div>

      <div
        className={cn(
          'overflow-hidden rounded-2xl border border-slate-200 bg-white transition-opacity',
          query.isPlaceholderData && 'opacity-60',
        )}
      >
        {query.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
        )}
        {sheet && sheet.employees.length === 0 && (
          <p className="px-4 py-10 text-center text-sm text-slate-500">
            {t('Bu oyda ishlagan xodim yoʻq.')}
          </p>
        )}
        {sheet && sheet.employees.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-max min-w-full border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 text-slate-500">
                  <th className="sticky left-0 z-10 min-w-[180px] bg-slate-50 px-3 py-2 text-left font-medium">
                    {t('Xodim')}
                  </th>
                  {days.map((day) => (
                    <th
                      key={day}
                      className={cn(
                        'w-7 px-0 py-2 text-center font-medium tabular-nums',
                        !workingSet.has(day) && 'bg-slate-100 text-slate-400',
                      )}
                    >
                      {day}
                    </th>
                  ))}
                  {[
                    t('Keldi'),
                    t('Kelmadi'),
                    t('Kasal'),
                    t('Taʼtilda'),
                    t('Ish kuni'),
                    t('Belgisiz'),
                  ].map((label) => (
                    <th key={label} className="px-2 py-2 text-right font-medium">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sheet.employees.map((row) => (
                  <tr key={row.employee_id}>
                    <td className="sticky left-0 z-10 bg-white px-3 py-1.5">
                      <span className="block max-w-[200px] truncate text-sm font-medium text-slate-800">
                        {row.full_name}
                      </span>
                      <span className="block max-w-[200px] truncate text-xs text-slate-400">
                        {row.position ?? '—'}
                      </span>
                    </td>
                    {days.map((day) => {
                      const status = row.days[String(day)]
                      const meta = status ? BY_VALUE[status] : null
                      return (
                        <td
                          key={day}
                          className={cn(
                            'p-0.5 text-center',
                            !workingSet.has(day) && !meta && 'bg-slate-50',
                          )}
                        >
                          {meta && (
                            <span
                              title={meta.label}
                              className={cn(
                                'mx-auto grid h-6 w-6 place-items-center rounded text-xs font-bold',
                                meta.cell,
                              )}
                            >
                              {meta.code}
                            </span>
                          )}
                        </td>
                      )
                    })}
                    {[row.present, row.absent, row.sick, row.leave, row.working_days].map(
                      (value, index) => (
                        <td
                          key={index}
                          className="px-2 py-1.5 text-right text-sm font-semibold tabular-nums text-slate-800"
                        >
                          {value}
                        </td>
                      ),
                    )}
                    <td
                      className={cn(
                        'px-2 py-1.5 text-right text-sm font-semibold tabular-nums',
                        row.unmarked > 0 ? 'text-amber-700' : 'text-slate-300',
                      )}
                    >
                      {row.unmarked}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {sheet && sheet.employees.length > 0 && (
        <p className="text-xs text-slate-400">
          {t(
            '«Ish kuni» — xodimning shu oydagi ish kunlari (ishga kirgan/ketgan sanasi, dam olish kunlari va bayramlar hisobga olingan). «Belgisiz» — bugungacha hali belgilanmagan ish kunlari.',
          )}
        </p>
      )}
    </div>
  )
}
