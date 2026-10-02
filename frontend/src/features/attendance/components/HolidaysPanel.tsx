/**
 * Bayram va yopiq kunlar kalendari (ADR-19).
 *
 * Bu ro'yxat bo'sh bo'lsa, kelmagan kunlar uchun qayta hisob bayramni
 * ham ish kuni deb sanaydi va ota-onaga bog'cha ishlamagan kun uchun
 * pul qaytarib yuboradi. Shuning uchun u qaytarish bloki bilan yonma-yon
 * turadi — sozlamalar ichida emas, ishlayotgan odamning ko'z o'ngida.
 *
 * Ro'yxat oldindan to'ldirilmaydi: diniy bayramlar har yili siljiydi va
 * qarorlar atrofdagi ish kunlarini ko'chiradi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarDays, Plus, Trash2 } from 'lucide-react'
import { DateInput } from '@/components/ui/DateInput'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { holidaysApi } from '@/features/attendance/api'
import { invalidateAttendance } from '@/lib/api/invalidate'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { formatDate } from '@/lib/utils'
import { t } from '@/lib/i18n'

export function HolidaysPanel() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [form, setForm] = useState({ holiday_date: '', name: '' })
  const [error, setError] = useState<string | null>(null)

  const holidaysQuery = useQuery({
    queryKey: queryKeys.holidays(organizationId),
    queryFn: holidaysApi.list,
  })

  // Bayram qayta hisobning MAXRAJINI o'zgartiradi (ADR-19), ya'ni
  // kelmagan kunlar uchun qaytariladigan summa ham o'zgaradi.
  const invalidate = () => invalidateAttendance(queryClient, organizationId)
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const create = useMutation({
    mutationFn: () => holidaysApi.create(form),
    onSuccess: () => {
      setForm({ holiday_date: '', name: '' })
      setError(null)
      invalidate()
    },
    onError: fail,
  })

  const remove = useMutation({
    mutationFn: (id: string) => holidaysApi.remove(id),
    onSuccess: invalidate,
    onError: fail,
  })

  const holidays = holidaysQuery.data?.items ?? []

  return (
    <details className="group rounded-2xl border border-slate-200 bg-white">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-semibold text-slate-900">
        <CalendarDays className="h-4 w-4 text-slate-400" />
        {t('Bayram va yopiq kunlar')}
        {holidays.length > 0 && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
            {holidays.length}
          </span>
        )}
        <span className="ml-auto text-xs font-normal text-slate-400">
          {t('Qayta hisobda ish kuni sanalmaydi')}
        </span>
      </summary>

      <div className="border-t border-slate-100 p-4">
        {error && (
          <div role="alert" className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {can('attendance.create') && (
          <form
            onSubmit={(event) => {
              event.preventDefault()
              create.mutate()
            }}
            className="mb-4 grid gap-3 sm:grid-cols-[10rem_1fr_auto]"
          >
            <div>
              <label htmlFor="hol-date" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Sana')}
              </label>
              <DateInput
                id="hol-date"
                required
                value={form.holiday_date}
                onChange={(iso) => setForm((p) => ({ ...p, holiday_date: iso }))}
              />
            </div>
            <div>
              <label htmlFor="hol-name" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Nomi')}
              </label>
              <input
                id="hol-name"
                required
                maxLength={80}
                value={form.name}
                placeholder={t('Masalan: Navroʻz')}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={create.isPending}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                <Plus className="h-4 w-4" /> {t('Qoʻshish')}
              </button>
            </div>
          </form>
        )}

        <ul className="divide-y divide-slate-100">
          {holidays.map((holiday) => (
            <li key={holiday.id} className="flex items-center justify-between gap-3 py-2">
              <span className="text-sm text-slate-700">
                <span className="tabular-nums text-slate-500">
                  {formatDate(holiday.holiday_date)}
                </span>
                <span className="ml-2 font-medium">{holiday.name}</span>
              </span>
              {can('attendance.delete') && (
                <button
                  type="button"
                  onClick={() => remove.mutate(holiday.id)}
                  title={t('Oʻchirish')}
                  aria-label={t('Oʻchirish')}
                  className="rounded-lg p-1.5 text-slate-300 transition hover:bg-red-50 hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
          {holidays.length === 0 && !holidaysQuery.isPending && (
            <li className="py-4 text-center text-sm text-slate-400">
              {t('Hali bayram kiritilmagan — qayta hisob barcha ish kunlarini toʻliq sanaydi.')}
            </li>
          )}
        </ul>
      </div>
    </details>
  )
}
