/**
 * "Bir oylik ariza" — bola shu oy kelmaydi, joyi saqlanadi (Bosqich 12.1).
 *
 * Oy uchun hisob-faktura 0 soʻm boʻladi va sababi qatorda yoziladi. Agar
 * oʻsha oyga faktura allaqachon chiqqan va toʻlanmagan boʻlsa, backend uni
 * bekor qilib 0 soʻmlik qayta yozadi; toʻlov tushgan boʻlsa — toʻxtaydi va
 * sababini aytadi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarOff } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { childrenApi } from '@/features/children/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { t } from '@/lib/i18n'

const MONTHS = [
  t('Yanvar'),
  t('Fevral'),
  t('Mart'),
  t('Aprel'),
  t('May'),
  t('Iyun'),
  t('Iyul'),
  t('Avgust'),
  t('Sentabr'),
  t('Oktabr'),
  t('Noyabr'),
  t('Dekabr'),
]

/** Oʻtgan oydan 12 oy oldinga — ariza deyarli har doim shu oraliqda. */
function monthOptions(): Array<[string, string]> {
  const now = new Date()
  const out: Array<[string, string]> = []
  for (let shift = -1; shift <= 11; shift += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() + shift, 1)
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    out.push([value, `${MONTHS[d.getMonth()]} ${d.getFullYear()}`])
  }
  return out
}

function monthLabel(iso: string): string {
  const [year, month] = iso.split('-').map(Number)
  return `${MONTHS[(month ?? 1) - 1]} ${year}`
}

export function PausePanel({ childId }: { childId: string }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const options = monthOptions()
  const [open, setOpen] = useState(false)
  const [month, setMonth] = useState(options[1]?.[0] ?? '')
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const key = ['org', organizationId, 'children', childId, 'pauses']
  const pauses = useQuery({ queryKey: key, queryFn: () => childrenApi.pauses(childId) })

  const add = useMutation({
    mutationFn: () => childrenApi.addPause(childId, { month, reason }),
    onSuccess: () => {
      setOpen(false)
      setReason('')
      setError(null)
      void queryClient.invalidateQueries({ queryKey: key })
      invalidateMoney(queryClient, organizationId)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const rows = pauses.data ?? []
  if (rows.length === 0 && !can('children.create')) return null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <CalendarOff className="h-4 w-4 text-slate-500" />
          {t('Bir oylik ariza')}
        </h2>
        {can('children.create') && !open && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-lg px-2.5 py-1.5 text-sm font-medium text-brand-700 hover:bg-brand-50"
          >
            {t('Qoʻshish')}
          </button>
        )}
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {t('Shu oy uchun 0 soʻm hisoblanadi, bolaning joyi saqlanadi.')}
      </p>

      {open && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            add.mutate()
          }}
          className="mt-3 grid gap-2 sm:grid-cols-[180px_1fr_auto]"
        >
          <div>
            <label htmlFor="pause-month" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Oy')}
            </label>
            <select
              id="pause-month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            >
              {options.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="pause-reason" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Sabab')}
            </label>
            <input
              id="pause-reason"
              required
              maxLength={255}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
          </div>
          <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={add.isPending || !reason.trim()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {t('Saqlash')}
            </button>
          </div>
          {error && (
            <p role="alert" className="text-sm text-red-700 sm:col-span-3">
              {error}
            </p>
          )}
        </form>
      )}

      {rows.length > 0 && (
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {rows.map((row) => (
            <li key={row.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2">
              <span className="font-medium text-slate-900">
                {row.month_from === row.month_to
                  ? monthLabel(row.month_from)
                  : `${monthLabel(row.month_from)} — ${monthLabel(row.month_to)}`}
              </span>
              <span className="text-slate-600">
                {row.reason}
                {row.created_by_name && (
                  <span className="text-slate-500"> · {row.created_by_name}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
