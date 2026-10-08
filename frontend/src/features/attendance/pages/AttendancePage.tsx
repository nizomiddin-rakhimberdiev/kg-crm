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
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarCheck, Check, Save, X } from 'lucide-react'
import { DateInput } from '@/components/ui/DateInput'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { attendanceApi } from '@/features/attendance/api'
import { groupsApi } from '@/features/children/api'
import { invalidateAttendance } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type AttendanceStatus } from '@/lib/api/types'
import { AbsenceClaimsPanel } from '@/features/attendance/components/AbsenceClaimsPanel'
import { HolidaysPanel } from '@/features/attendance/components/HolidaysPanel'
import { StaffAttendancePanel } from '@/features/attendance/components/StaffAttendancePanel'
import { Modal } from '@/components/ui/Modal'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { useToast } from '@/app/providers/ToastProvider'
import { QueryError } from '@/components/ui/QueryError'
import { t } from '@/lib/i18n'

const STATUS_BUTTONS: Array<{
  value: AttendanceStatus
  label: string
  icon: typeof Check
  active: string
}> = [
  { value: 'present', label: t('Keldi'), icon: Check, active: 'bg-emerald-600 text-white' },
  { value: 'excused', label: t('Sababli'), icon: CalendarCheck, active: 'bg-ildiz-700 text-white' },
  { value: 'absent', label: t('Kelmagan'), icon: X, active: 'bg-red-600 text-white' },
]

const today = () => new Date().toISOString().slice(0, 10)

function ChildrenAttendance() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [groupId, setGroupId] = useState('')
  const [date, setDate] = useState(today())
  const [draft, setDraft] = useState<Record<string, AttendanceStatus>>({})
  // Sabab har bola uchun alohida saqlanadi va davomat bilan BIRGA yuboriladi
  // (`reason` maydoni bazada boshidan bor edi, faqat so'ralmasdi).
  const [reasons, setReasons] = useState<Record<string, string>>({})
  // Ochiq modal: qaysi bolaning sababi kiritilyapti.
  const [reasonFor, setReasonFor] = useState<{ childId: string; name: string } | null>(null)
  const [reasonDraft, setReasonDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  // Saqlanganini TOAST aytadi (PLAN 4.7): kichkina kulrang "Saqlandi"
  // yozuvini mudira koʻrmaydi va ikkinchi marta bosadi.
  const { toast } = useToast()

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
      const initialReasons: Record<string, string> = {}
      for (const row of registerQuery.data.rows) {
        if (row.status) initial[row.child_id] = row.status
        if (row.reason) initialReasons[row.child_id] = row.reason
      }
      setDraft(initial)
      setReasons(initialReasons)
      setSaved(false)
    }
  }, [registerQuery.data])

  const saveMutation = useMutation({
    mutationFn: () =>
      attendanceApi.markBulk(
        groupId,
        date,
        Object.entries(draft).map(([child_id, status]) => ({
          child_id,
          status,
          reason: reasons[child_id] ?? '',
        })),
      ),
    onSuccess: () => {
      setSaved(true)
      toast(t('Davomat saqlandi'))
      setError(null)
      void queryClient.invalidateQueries({
        queryKey: queryKeys.attendanceDaily(organizationId, groupId, date),
      })
      invalidateAttendance(queryClient, organizationId)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Saqlab boʻlmadi.')),
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
  // "O'zgardimi?" — holat VA sabab bo'yicha. Faqat holatga qarasak, allaqachon
  // "Sababli" deb belgilangan bolaga sabab yozish tugmani faolsiz qoldirardi
  // va yozuv jimgina yo'qolardi.
  const dirty = rows.some(
    (row) =>
      (draft[row.child_id] ?? null) !== row.status ||
      (reasons[row.child_id] ?? '') !== (row.reason ?? ''),
  )

  const closeReason = () => setReasonFor(null)

  const saveReason = () => {
    if (!reasonFor) return
    const value = reasonDraft.trim()
    setReasons((prev) => {
      const next = { ...prev }
      if (value) next[reasonFor.childId] = value
      else delete next[reasonFor.childId]
      return next
    })
    setSaved(false)
    closeReason()
  }

  /*
   * Saqlanmagan davomat yoʻqolmasligi kerak (PLAN 10.2).
   *
   * Tarbiyachi 25 ta bolani belgilaydi, keyin guruhni almashtiradi
   * yoki ilovani yopadi — va belgilangan hammasi yoʻq boʻlardi.
   * Qoralama faqat xotirada (serverga "Saqlash" bilan ketadi), shuning
   * uchun ogohlantirish shu yerda: brauzerdan chiqishda va tanlovni
   * almashtirishda.
   */
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  /** Tanlovni almashtirishdan oldin soʻraydi — qoralama boʻlsa. */
  const switchGuarded = (apply: () => void) => {
    if (dirty && !window.confirm(t('Saqlanmagan belgilar yoʻqoladi. Davom etasizmi?'))) return
    apply()
  }

  return (
    <div className="space-y-6 pb-24 sm:pb-0">
      {/* Sabab oynasi — "Sababli" bosilganda darhol chiqadi. Sabab
          davomat bilan BIRGA saqlanadi: alohida so'rov yuborilsa,
          tarbiyachi "Saqlash" ni bosmasdan chiqib ketganda yarim
          yozilgan holat qolardi. */}
      <Modal open={Boolean(reasonFor)} onClose={closeReason} className="max-w-md">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            saveReason()
          }}
          className="p-5"
        >
          <h2 className="text-base font-semibold text-slate-900">{t('Kelmagani haqida')}</h2>
          <p className="mt-1 text-sm text-slate-500">{reasonFor?.name}</p>
          <input
            autoFocus
            value={reasonDraft}
            onChange={(e) => setReasonDraft(e.target.value)}
            maxLength={255}
            placeholder={t('Masalan: kasal, shifokorda, oilaviy sabab')}
            aria-label={t('Masalan: kasal, shifokorda, oilaviy sabab')}
            className="mt-4 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={closeReason}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
            >
              {t('Saqlash')}
            </button>
          </div>
        </form>
      </Modal>

      <p className="text-sm text-slate-500">
        {t('Guruhni tanlang va butun kunni bitta bosishda saqlang.')}
      </p>

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
            onChange={(e) => {
              const next = e.target.value
              switchGuarded(() => setGroupId(next))
            }}
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
          <DateInput
            id="date"
            max={today()}
            value={date}
            onChange={(iso) => switchGuarded(() => setDate(iso))}
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
                  : 'bg-slate-100 text-slate-600',
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
            [t('Sababli'), counts.excused, 'text-ildiz-700'],
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
          <p className="px-4 py-8 text-center text-sm text-slate-500">{t('Yuklanmoqda…')}</p>
        )}
        {!groupId && !groupsQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-500">
            {t('Avval guruh yarating.')}
          </p>
        )}
        {registerQuery.isError && (
          <QueryError error={registerQuery.error} onRetry={() => registerQuery.refetch()} />
        )}
        {registerQuery.data?.rows.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-slate-500">
            {t('Bu guruhda faol bola yoʻq.')}
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
                <span className="min-w-0">
                  <span
                    className={cn(
                      'block text-sm font-medium',
                      current ? 'text-slate-800' : 'text-slate-500',
                    )}
                  >
                    {row.full_name}
                  </span>
                  {editable && (current === 'excused' || current === 'absent') && (
                    <button
                      type="button"
                      onClick={() => {
                        setReasonDraft(reasons[row.child_id] ?? '')
                        setReasonFor({ childId: row.child_id, name: row.full_name })
                      }}
                      className="mt-0.5 block max-w-[240px] truncate text-left text-xs text-slate-500 underline decoration-dotted underline-offset-2 hover:text-brand-700"
                    >
                      {reasons[row.child_id] || t('Sababini yozish')}
                    </button>
                  )}
                  {!editable && reasons[row.child_id] && (
                    <span className="mt-0.5 block text-xs text-slate-500">
                      {reasons[row.child_id]}
                    </span>
                  )}
                </span>

                <div className="flex gap-1">
                  {STATUS_BUTTONS.map(({ value, label, icon: Icon, active }) => (
                    <button
                      key={value}
                      type="button"
                      disabled={!editable}
                      onClick={() => {
                        setDraft((prev) => ({ ...prev, [row.child_id]: value }))
                        setSaved(false)
                        // "Sababli" — sababning O'ZI ma'no beradi, shuning
                        // uchun darhol so'raymiz. "Kelmagan" uchun izoh
                        // ixtiyoriy: uni ism ostidagi havoladan qo'shish
                        // mumkin, har bosishda modal ochilsa 20 bolani
                        // belgilash azobga aylanardi.
                        if (value === 'excused') {
                          setReasonDraft(reasons[row.child_id] ?? '')
                          setReasonFor({ childId: row.child_id, name: row.full_name })
                        }
                      }}
                      aria-label={`${row.full_name}: ${label}`}
                      aria-pressed={current === value}
                      title={label}
                      className={cn(
                        'flex min-h-11 items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium transition sm:min-h-0 sm:px-2.5',
                        current === value
                          ? active
                          : 'bg-slate-50 text-slate-500 hover:bg-slate-100',
                        !editable && 'cursor-not-allowed opacity-60',
                      )}
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      {/* Yozuv MOBILDA ham koʻrinadi (PLAN 4.7):
                          "Keldi / Sababli / Kelmadi" uchta ikonka
                          bilan ajratilganda tarbiyachi ularni
                          taxmin qilib bosardi — va davomat
                          hisobotga ketadigan maʼlumot. */}
                      <span>{label}</span>
                    </button>
                  ))}
                </div>
              </li>
            )
          })}
        </ul>
      </div>

      {/*
        Telefonda saqlash tugmasi roʻyxat tagida qolib ketadi: 25 ta
        bola belgilangach, tarbiyachi uni topish uchun yuqoriga
        qaytishi kerak edi. Yopishqoq panel — faqat qoralama
        boʻlganda va faqat telefonda.
      */}
      {editable && dirty && rows.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-200 bg-white/95 px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3 backdrop-blur sm:hidden">
          <button
            type="button"
            disabled={saveMutation.isPending}
            onClick={() => saveMutation.mutate()}
            className="flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl bg-brand-600 text-base font-semibold text-white disabled:opacity-60"
          >
            <Save className="h-5 w-5" />
            {saveMutation.isPending
              ? t('Saqlanmoqda…')
              : t('Saqlash · {n} ta belgilandi', { n: rows.length - counts.unmarked })}
          </button>
        </div>
      )}

      {/* Hujjatli kelmaslik — kunlik registrdan ALOHIDA blok (ADR-19).
          Ular bir-biridan hech narsa o'qimaydi: registr "bugun kim
          keldi", bu esa "qaysi kunlar uchun pul qaytariladi". */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
        <AbsenceClaimsPanel />
      </section>

      {/* Bayram kalendari qaytarish bloki BILAN YONMA-YON: u bo'sh
          bo'lsa, qayta hisob bayramni ham ish kuni deb sanaydi va
          bog'cha ishlamagan kun uchun pul qaytarib yuboradi. */}
      <HolidaysPanel />
    </div>
  )
}

/**
 * Davomat — ikki bo'lim: bolalar va xodimlar (tabel).
 *
 * Bo'lim URL'da (`?tab=staff`) — yangilash yoki havola berish uni
 * yo'qotmaydi. Ikkalasi ham `attendance` ruxsati bilan.
 */
export default function AttendancePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') === 'staff' ? 'staff' : 'children'

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Davomat')}</h1>
      <div className="flex gap-1 border-b border-slate-200">
        {(
          [
            ['children', t('Bolalar')],
            ['staff', t('Xodimlar')],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() =>
              setSearchParams(key === 'staff' ? { tab: 'staff' } : {}, { replace: true })
            }
            className={cn(
              '-mb-px border-b-2 px-4 py-2 text-sm font-medium transition',
              tab === key
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-800',
            )}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'staff' ? <StaffAttendancePanel /> : <ChildrenAttendance />}
    </div>
  )
}
