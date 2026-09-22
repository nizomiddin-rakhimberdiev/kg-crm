/**
 * Kunlik davomat jurnali (docs/04 §8).
 *
 * Ekran butun guruhni bir ekranda ko'rsatadi va bitta so'rovda saqlaydi:
 * tarbiyachi ertalab 25 ta bolani belgilaydi va har biri uchun alohida
 * so'rov yuborish ham sekin, ham yarim saqlangan holatga olib keladi.
 *
 * Belgilanmagan bolalar ham ro'yxatda turadi — "kim qoldi?" degan savol
 * javobsiz qolmasin.
 */

import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarCheck, Check, Save, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { attendanceApi } from '@/features/attendance/api'
import { groupsApi } from '@/features/children/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type AttendanceStatus } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const STATUS_BUTTONS: Array<{
  value: AttendanceStatus
  label: string
  icon: typeof Check
  active: string
}> = [
  { value: 'present', label: t('Keldi'), icon: Check, active: 'bg-emerald-600 text-white' },
  { value: 'excused', label: t('Sababli'), icon: CalendarCheck, active: 'bg-sky-600 text-white' },
  { value: 'absent', label: t('Kelmagan'), icon: X, active: 'bg-red-600 text-white' },
]

const today = () => new Date().toISOString().slice(0, 10)

export default function AttendancePage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [groupId, setGroupId] = useState('')
  const [date, setDate] = useState(today())
  const [draft, setDraft] = useState<Record<string, AttendanceStatus>>({})
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })

  // Birinchi guruhni avtomatik tanlaymiz — tarbiyachi har kuni bir xil
  // tanlovni takrorlamasin.
  useEffect(() => {
    if (!groupId && groupsQuery.data?.items.length) {
      setGroupId(groupsQuery.data.items[0].id)
    }
  }, [groupId, groupsQuery.data])

  const registerQuery = useQuery({
    queryKey: queryKeys.attendanceDaily(organizationId, groupId, date),
    queryFn: () => attendanceApi.daily(groupId, date),
    enabled: Boolean(groupId && date),
  })

  // Serverdan kelgan holat qoralamaning asosi. Kun yoki guruh almashganda
  // qoralama qayta tiklanadi — aks holda oldingi kunning belgilari
  // ko'chib qolardi.
  useEffect(() => {
    if (registerQuery.data) {
      const initial: Record<string, AttendanceStatus> = {}
      for (const row of registerQuery.data.rows) {
        if (row.status) initial[row.child_id] = row.status
      }
      setDraft(initial)
      setSaved(false)
    }
  }, [registerQuery.data])

  const saveMutation = useMutation({
    mutationFn: () =>
      attendanceApi.markBulk(
        groupId,
        date,
        Object.entries(draft).map(([child_id, status]) => ({ child_id, status })),
      ),
    onSuccess: () => {
      setSaved(true)
      setError(null)
      void queryClient.invalidateQueries({
        queryKey: queryKeys.attendanceDaily(organizationId, groupId, date),
      })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t("Saqlab bo'lmadi.")),
  })

  const rows = registerQuery.data?.rows ?? []

  const counts = useMemo(() => {
    const result = { present: 0, excused: 0, absent: 0, unmarked: 0 }
    for (const row of rows) {
      const status = draft[row.child_id]
      if (!status) result.unmarked += 1
      else result[status] += 1
    }
    return result
  }, [rows, draft])

  const markAll = (status: AttendanceStatus) => {
    setDraft(Object.fromEntries(rows.map((row) => [row.child_id, status])))
    setSaved(false)
  }

  const editable = can('attendance.create')
  const dirty = rows.some((row) => (draft[row.child_id] ?? null) !== row.status)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Davomat')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('Guruhni tanlang va butun kunni bitta bosishda saqlang.')}
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[200px]">
          <label htmlFor="group" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Guruh')}
          </label>
          <select
            id="group"
            value={groupId}
            onChange={(e) => setGroupId(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
          >
            {groupsQuery.data?.items.map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="date" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Sana')}
          </label>
          <input
            id="date"
            type="date"
            max={today()}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
          />
        </div>

        {editable && rows.length > 0 && (
          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              onClick={() => markAll('present')}
              className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              {t('Hammasi keldi')}
            </button>
            <button
              type="button"
              disabled={!dirty || saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
              className={cn(
                'flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition',
                dirty && !saveMutation.isPending
                  ? 'bg-brand-600 text-white hover:bg-brand-700'
                  : 'bg-slate-100 text-slate-400',
              )}
            >
              <Save className="h-4 w-4" />
              {saveMutation.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
            </button>
          </div>
        )}
      </div>

      {rows.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            [t('Keldi'), counts.present, 'text-emerald-700'],
            [t('Sababli'), counts.excused, 'text-sky-700'],
            [t('Kelmagan'), counts.absent, 'text-red-700'],
            [t('Belgilanmagan'), counts.unmarked, 'text-slate-500'],
          ].map(([label, value, tone]) => (
            <div key={String(label)} className="rounded-xl bg-white p-3 text-center shadow-sm">
              <p className={cn('text-xl font-bold', tone as string)}>{value}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {saved && !dirty && (
        <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {t('Saqlandi.')}
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {registerQuery.isPending && groupId && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
        )}
        {!groupId && !groupsQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">
            {t('Avval guruh yarating.')}
          </p>
        )}
        {registerQuery.data?.rows.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">
            {t("Bu guruhda faol bola yo'q.")}
          </p>
        )}

        <ul className="divide-y divide-slate-100">
          {rows.map((row) => {
            const current = draft[row.child_id] ?? null
            return (
              <li
                key={row.child_id}
                className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              >
                <span
                  className={cn(
                    'text-sm font-medium',
                    current ? 'text-slate-800' : 'text-slate-400',
                  )}
                >
                  {row.full_name}
                </span>

                <div className="flex gap-1">
                  {STATUS_BUTTONS.map(({ value, label, icon: Icon, active }) => (
                    <button
                      key={value}
                      type="button"
                      disabled={!editable}
                      title={label}
                      onClick={() => {
                        setDraft((prev) => ({ ...prev, [row.child_id]: value }))
                        setSaved(false)
                      }}
                      className={cn(
                        'flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium transition',
                        current === value
                          ? active
                          : 'bg-slate-50 text-slate-500 hover:bg-slate-100',
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
