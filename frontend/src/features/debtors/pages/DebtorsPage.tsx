/**
 * Qarzdorlar — **hisoblangan ro'yxat**, jadval emas (ADR-7).
 *
 * Ro'yxat har safar hisob-faktura va to'lovlardan hisoblanadi. Shuning
 * uchun u kesh siljisa ham to'g'ri qoladi — bu muhim, chunki noto'g'ri
 * ro'yxat eng yomon joyda chiqardi: ota-onadan pul talab qilishda.
 *
 * Bu sahifaning ishi bitta: **kimga bugun qo'ng'iroq qilish yoki
 * eslatma yuborish kerakligini** ko'rsatish. Shuning uchun unda
 * kechikkan kunlar, oxirgi eslatma vaqti va bir bosishda yuboriladigan
 * eslatma bor (PLAN 3.5).
 */

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  BellRing,
  CheckCircle2,
  ChevronRight,
  Download,
  Phone,
  Sparkles,
} from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { overdueDaysFromSearch, filterByOverdueDays } from '@/features/debtors/overdueDays'
import { fill, getCopy } from '@/features/intelligence/content'
import { Modal } from '@/components/ui/Modal'
import { groupsApi } from '@/features/children/api'
import { notificationsApi, type ReminderFilters } from '@/features/notifications/api'
import { ReminderConfirmDialog } from '@/features/notifications/components/ReminderConfirmDialog'
import { TestModeBanner } from '@/features/notifications/components/TestModeBanner'
import { debtorsApi } from '@/features/payments/api'
import { useExcelExport } from '@/features/reports/useExcelExport'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { EmptyRow } from '@/components/ui/EmptyState'
import { som } from '@/lib/format'
import { t } from '@/lib/i18n'

const money = som

const date = (value: string | null) =>
  value ? value.slice(0, 10).split('-').reverse().join('.') : '—'

/**
 * Ko'chirmadagi qator turlari — odam tilida.
 *
 * Avval bu yerda `entry_type` xom holda chiqardi: "tuition",
 * "payment". Ota-onaga ko'rsatiladigan hujjatda inglizcha kod turishi
 * — tushunarsizlik va ishonchsizlik.
 */
const ENTRY_LABEL: Record<string, string> = {
  tuition: t('Oylik toʻlov'),
  payment: t('Toʻlov'),
  discount: t('Chegirma'),
  penalty: t('Jarima'),
  adjustment: t('Tuzatish'),
  refund: t('Qaytarildi'),
  absence_credit: t('Kelmagan kunlar uchun'),
}

/** Kechikish chegaralari — mudira shu toifalarda o'ylaydi. */
const DAY_FILTERS: Array<[number | null, string]> = [
  [null, t('Hammasi')],
  [15, t('15+ kun')],
  [30, t('30+ kun')],
  [60, t('60+ kun')],
]

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
          <h2 className="text-lg font-bold text-tosh-900">
            {query.data?.child.full_name ?? t('Koʻchirma')}
          </h2>
          <p className="mt-1 text-sm text-tosh-500">
            {t('Moliyaviy koʻchirma — har bir hisob-faktura va toʻlov')}
          </p>
        </div>

        {query.isPending && (
          <p className="py-8 text-center text-sm text-tosh-400">{t('Yuklanmoqda…')}</p>
        )}

        {query.data && (
          <>
            <div className="mb-4 rounded-lg bg-orik-50 px-3 py-2">
              <span className="text-sm text-orik-800">{t('Joriy qarz:')} </span>
              <span className="font-bold text-orik-900">{money(query.data.balance)}</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-tosh-400">
                  <tr>
                    <th className="py-2 font-medium">{t('Sana')}</th>
                    <th className="py-2 font-medium">{t('Izoh')}</th>
                    <th className="py-2 text-right font-medium">{t('Summa')}</th>
                    <th className="py-2 text-right font-medium">{t('Qoldiq')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-tosh-100">
                  {query.data.entries.map((entry) => (
                    <tr key={entry.id}>
                      <td className="py-2 text-xs text-tosh-500">{date(entry.occurred_at)}</td>
                      <td className="py-2 text-tosh-700">
                        {entry.description || ENTRY_LABEL[entry.entry_type] || entry.entry_type}
                      </td>
                      <td
                        className={cn(
                          'num py-2 text-right font-medium',
                          entry.direction === 'debit' ? 'text-orik-800' : 'text-nihol-700',
                        )}
                      >
                        {entry.direction === 'debit' ? '+' : '−'}
                        {money(entry.amount)}
                      </td>
                      <td className="num py-2 text-right text-tosh-500">
                        {money(entry.running_balance)}
                      </td>
                    </tr>
                  ))}
                  {query.data.entries.length === 0 && (
                    <EmptyRow
                      colSpan={4}
                      icon={CheckCircle2}
                      title={t('Yozuv yoʻq')}
                      hint={t('Bu bola boʻyicha hali hisob-faktura ham, toʻlov ham yoʻq.')}
                    />
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}

export default function DebtorsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const [searchParams, setSearchParams] = useSearchParams()

  // Radix AI deep link (docs/07 §8): `?overdue_days=15` — "faqat muddati
  // o'tganlar" yoqiladi va ro'yxat N kundan eskilarga toraytiriladi.
  const aiDays = overdueDaysFromSearch(searchParams)
  const [overdueOnlyChoice, setOverdueOnly] = useState(false)
  const overdueOnly = overdueOnlyChoice || aiDays !== null

  const [minDays, setMinDays] = useState<number | null>(null)
  const [groupId, setGroupId] = useState('')
  const [minAmount, setMinAmount] = useState('')
  const [orderBy, setOrderBy] = useState<'debt' | 'days' | 'name'>('debt')
  const [openChild, setOpenChild] = useState<string | null>(null)
  const [confirming, setConfirming] = useState<ReminderFilters | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const params = useMemo(() => {
    const next: Record<string, string> = { order_by: orderBy }
    if (overdueOnly) next.overdue = 'true'
    if (minDays !== null) next.min_days = String(minDays)
    if (groupId) next.group_id = groupId
    if (minAmount.trim()) next.min_amount = minAmount.trim()
    return next
  }, [overdueOnly, minDays, groupId, minAmount, orderBy])

  const debtorsQuery = useQuery({
    queryKey: queryKeys.debtors(organizationId, params),
    queryFn: () => debtorsApi.list(params),
  })
  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })
  const excel = useExcelExport('debtors')

  // Ekrandagi filtr yuborishda ham saqlanadi: "30+ kun" ni tanlab
  // tugmani bosgan mudira hammaga yuborilishini kutmaydi.
  const listFilters: ReminderFilters = useMemo(
    () => ({
      ...(minDays !== null ? { min_days: minDays } : {}),
      ...(groupId ? { group_id: groupId } : {}),
      ...(minAmount.trim() ? { min_amount: minAmount.trim() } : {}),
    }),
    [minDays, groupId, minAmount],
  )

  const remind = useMutation({
    mutationFn: (filters: ReminderFilters) => notificationsApi.remindDebtors(filters),
    onSuccess: (result) => {
      setError(null)
      setConfirming(null)
      setNotice(
        result.queued === 0
          ? t('Hech kimga eslatma yuborilmadi — telefon raqami yoʻq yoki bugun allaqachon olgan.')
          : t('{queued} ta eslatma yuborildi.', { queued: result.queued }),
      )
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'debtors'] })
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'notifications'] })
    },
    onError: (err: unknown) => {
      setNotice(null)
      setConfirming(null)
      setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))
    },
  })

  const rows = useMemo(
    () =>
      debtorsQuery.data ? filterByOverdueDays(debtorsQuery.data.results, aiDays, new Date()) : [],
    [debtorsQuery.data, aiDays],
  )
  const aiCopy = getCopy().debtors

  return (
    <div className="space-y-6">
      {openChild && <StatementDrawer childId={openChild} onClose={() => setOpenChild(null)} />}
      <ReminderConfirmDialog
        open={confirming !== null}
        filters={confirming ?? {}}
        busy={remind.isPending}
        onConfirm={() => confirming && remind.mutate(confirming)}
        onCancel={() => setConfirming(null)}
      />

      {aiDays !== null && (
        <div
          role="status"
          className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-nihol-100 bg-nihol-50 px-3 py-2 text-sm text-nihol-800"
        >
          <Sparkles className="h-4 w-4 shrink-0" />
          <span>{fill(aiCopy.banner, { days: aiDays })}</span>
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
          <h1 className="text-2xl font-bold tracking-tight text-tosh-900">{t('Qarzdorlar')}</h1>
          <p className="mt-1 text-sm text-tosh-500">
            {t('Qarz barcha hisob-faktura va toʻlovlardan avtomatik hisoblanadi.')}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void excel.start(params)}
            disabled={excel.busy}
            className="inline-flex items-center gap-2 rounded-lg border border-tosh-200 px-3 py-2 text-sm font-medium text-tosh-700 hover:bg-tosh-50 disabled:opacity-60"
          >
            <Download className="h-4 w-4" />
            {excel.busy ? t('Tayyorlanmoqda…') : t('Excel')}
          </button>
          {can('notifications.create') && rows.length > 0 && (
            <button
              type="button"
              onClick={() => setConfirming(listFilters)}
              disabled={remind.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-nihol-600 px-4 py-2 text-sm font-semibold text-white hover:bg-nihol-700 disabled:opacity-60"
            >
              <BellRing className="h-4 w-4" />
              {t('Hammasiga eslatma')}
            </button>
          )}
        </div>
      </div>

      <TestModeBanner />

      {(excel.error || error) && (
        <p role="alert" className="rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-900">
          {excel.error || error}
        </p>
      )}
      {notice && (
        <p className="rounded-lg bg-nihol-50 px-3 py-2 text-sm text-nihol-800">{notice}</p>
      )}

      {/* Filtrlar — mudira "kimga bugun qo'ng'iroq qilay?" degan
          savolga javob izlaydi, shuning uchun kechikish va guruh
          birinchi o'rinda. */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-tosh-200 bg-white p-3">
        <div className="flex flex-wrap items-center gap-1">
          {DAY_FILTERS.map(([value, label]) => (
            <button
              key={label}
              type="button"
              onClick={() => setMinDays(value)}
              className={cn(
                'rounded-lg px-3 py-1.5 text-sm font-medium',
                minDays === value ? 'bg-tosh-900 text-white' : 'text-tosh-600 hover:bg-tosh-50',
              )}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="min-w-[160px]">
          <label htmlFor="debtor-group" className="block text-xs font-medium text-tosh-500">
            {t('Guruh')}
          </label>
          <select
            id="debtor-group"
            value={groupId}
            onChange={(event) => setGroupId(event.target.value)}
            className="mt-1 w-full rounded-lg border border-tosh-200 px-2.5 py-2 text-sm outline-none focus:border-nihol-500"
          >
            <option value="">{t('Barcha guruhlar')}</option>
            {(groupsQuery.data?.items ?? []).map((group) => (
              <option key={group.id} value={group.id}>
                {group.name}
              </option>
            ))}
          </select>
        </div>

        <div className="min-w-[140px]">
          <label htmlFor="debtor-amount" className="block text-xs font-medium text-tosh-500">
            {t('Eng kam qarz')}
          </label>
          <input
            id="debtor-amount"
            inputMode="numeric"
            value={minAmount}
            placeholder="500000"
            onChange={(event) => setMinAmount(event.target.value.replace(/[^\d]/g, ''))}
            className="num mt-1 w-full rounded-lg border border-tosh-200 px-2.5 py-2 text-sm outline-none focus:border-nihol-500"
          />
        </div>

        <div className="min-w-[160px]">
          <label htmlFor="debtor-order" className="block text-xs font-medium text-tosh-500">
            {t('Saralash')}
          </label>
          <select
            id="debtor-order"
            value={orderBy}
            onChange={(event) => setOrderBy(event.target.value as typeof orderBy)}
            className="mt-1 w-full rounded-lg border border-tosh-200 px-2.5 py-2 text-sm outline-none focus:border-nihol-500"
          >
            <option value="debt">{t('Qarz boʻyicha')}</option>
            <option value="days">{t('Kechikish boʻyicha')}</option>
            <option value="name">{t('Ism boʻyicha')}</option>
          </select>
        </div>

        <label
          htmlFor="debtor-overdue"
          className="flex cursor-pointer items-center gap-2 py-2 text-sm text-tosh-600"
        >
          <input
            id="debtor-overdue"
            type="checkbox"
            checked={overdueOnly}
            disabled={aiDays !== null}
            onChange={(event) => setOverdueOnly(event.target.checked)}
          />
          {t('Faqat muddati oʻtganlar')}
        </label>

        {debtorsQuery.data && (
          <p className="ml-auto text-right text-sm">
            <span className="text-xs text-tosh-500">{t('Jami qarz')}</span>
            <br />
            <span className="num text-lg font-bold text-orik-800">
              {money(debtorsQuery.data.total_debt)}
            </span>
          </p>
        )}
      </div>

      <div className="overflow-hidden rounded-2xl border border-tosh-200 bg-white">
        {debtorsQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-tosh-400">{t('Yuklanmoqda…')}</p>
        )}
        {debtorsQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-orik-800">
            {debtorsQuery.error instanceof ApiError
              ? debtorsQuery.error.message
              : t('Maʼlumotni yuklab boʻlmadi.')}
          </p>
        )}
        {debtorsQuery.data && rows.length === 0 && (
          <div className="px-4 py-12 text-center">
            <AlertTriangle className="mx-auto mb-3 h-10 w-10 text-tosh-200" />
            <p className="text-sm text-tosh-500">{t('Qarzdorlar yoʻq.')}</p>
          </div>
        )}

        {debtorsQuery.data && rows.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-sm">
              <thead className="bg-tosh-50 text-left text-xs uppercase tracking-wide text-tosh-500">
                <tr>
                  <th className="px-4 py-3 font-medium">{t('Bola')}</th>
                  <th className="px-4 py-3 font-medium">{t('Guruh')}</th>
                  <th className="px-4 py-3 font-medium">{t('Vasiy')}</th>
                  <th className="px-4 py-3 font-medium">{t('Kechikish')}</th>
                  <th className="px-4 py-3 font-medium">{t('Oxirgi eslatma')}</th>
                  <th className="px-4 py-3 text-right font-medium">{t('Qarz')}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-tosh-100">
                {rows.map((row) => (
                  <tr
                    key={row.child.id}
                    className="cursor-pointer hover:bg-tosh-50"
                    onClick={() => setOpenChild(row.child.id)}
                  >
                    <td className="px-4 py-3 font-medium text-tosh-800">{row.child.full_name}</td>
                    <td className="px-4 py-3 text-tosh-600">{row.child.group ?? '—'}</td>
                    <td className="px-4 py-3 text-tosh-600">
                      {row.primary_guardian ? (
                        <>
                          <p>{row.primary_guardian.full_name}</p>
                          <p className="flex items-center gap-1 text-xs text-tosh-400">
                            <Phone className="h-3 w-3" />
                            {row.primary_guardian.phone}
                          </p>
                        </>
                      ) : (
                        <span className="text-orik-800">{t('vasiy yoʻq')}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {row.days_overdue !== null ? (
                        <span
                          className={cn(
                            'num rounded-full px-2 py-0.5 text-xs font-medium',
                            row.days_overdue >= 30
                              ? 'bg-orik-100 text-orik-900'
                              : 'bg-orik-50 text-orik-800',
                          )}
                        >
                          {t('{days} kun', { days: row.days_overdue })}
                        </span>
                      ) : (
                        <span className="text-xs text-tosh-400">{t('muddati kelmagan')}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-tosh-500">
                      {row.last_reminder_at ? (
                        date(row.last_reminder_at)
                      ) : (
                        <span className="text-tosh-400">{t('yuborilmagan')}</span>
                      )}
                    </td>
                    <td className="num px-4 py-3 text-right font-semibold text-orik-800">
                      {money(row.balance)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {can('notifications.create') && row.primary_guardian && (
                          <button
                            type="button"
                            title={t('Shu ota-onaga eslatma')}
                            aria-label={t('{name} uchun eslatma yuborish', {
                              name: row.child.full_name,
                            })}
                            onClick={(event) => {
                              event.stopPropagation()
                              setConfirming({ child_ids: [row.child.id] })
                            }}
                            className="rounded-lg border border-tosh-200 p-1.5 text-tosh-600 hover:bg-tosh-50"
                          >
                            <BellRing className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <ChevronRight className="h-4 w-4 text-tosh-300" />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
