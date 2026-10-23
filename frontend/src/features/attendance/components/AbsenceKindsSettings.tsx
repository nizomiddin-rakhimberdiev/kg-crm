/**
 * Qayta hisob turlari va qoidalari — sozlamalarda (Bosqich 12.3, ADR-33).
 *
 * Bu bogʻchaning PUL siyosati: qaysi hujjat bilan qancha qaytariladi.
 * Shuning uchun `settings.update` bilan, davomat sahifasida emas.
 *
 * Maʼlumotnoma qoidasi ikki maydonning birikmasi: "kuniga qatʼiy summa"
 * (ovqat puli) + "shuncha kundan boshlab toʻliq stavka" = 3. Kod
 * oʻzgarmaydi — daʼvolar unga bogʻlangan; tur oʻchirilmaydi, oʻchiriladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { absenceKindsApi, type AbsenceKind } from '@/features/attendance/api'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'

const MODES: Array<[AbsenceKind['refund_mode'], string]> = [
  ['full_rate', t('Toʻliq kunlik stavka')],
  ['fixed_per_day', t('Kuniga qatʼiy summa')],
  ['none', t('Qaytarilmaydi')],
]

const cell =
  'w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus:border-brand-500 disabled:bg-slate-50'

export function AbsenceKindsSettings() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const editable = can('settings.update')
  const key = ['org', organizationId, 'absence-kinds']
  const kinds = useQuery({ queryKey: key, queryFn: absenceKindsApi.list })
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState({ code: '', name: '' })

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['org', organizationId] })
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<AbsenceKind> }) =>
      absenceKindsApi.update(id, patch),
    onSuccess: () => {
      setError(null)
      refresh()
    },
    onError: fail,
  })
  const create = useMutation({
    mutationFn: () =>
      absenceKindsApi.create({
        code: draft.code,
        name: draft.name,
        refund_mode: 'full_rate',
        daily_amount: null,
        min_days: 1,
        full_rate_from_days: null,
        requires_document: false,
      }),
    onSuccess: () => {
      setDraft({ code: '', name: '' })
      setError(null)
      refresh()
    },
    onError: fail,
  })

  const rows = kinds.data?.items ?? []
  const patch = (id: string, value: Partial<AbsenceKind>) => update.mutate({ id, patch: value })

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 sm:p-5">
      <h2 className="text-sm font-semibold text-slate-900">{t('Qayta hisob turlari')}</h2>
      <p className="mt-0.5 text-xs text-slate-500">
        {t(
          'Kelmagan kunlar uchun qancha qaytarilishi. Maʼlumotnoma: kuniga ovqat puli, belgilangan kundan boshlab — hamma kunlar toʻliq stavkada.',
        )}
      </p>
      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="py-2 pr-2 font-medium">{t('Nomi')}</th>
              <th className="py-2 pr-2 font-medium">{t('Qaytarish')}</th>
              <th className="py-2 pr-2 font-medium">{t('Kuniga (soʻm)')}</th>
              <th className="py-2 pr-2 font-medium">{t('Kamida (kun)')}</th>
              <th className="py-2 pr-2 font-medium">{t('Toʻliq stavka (kundan)')}</th>
              <th className="py-2 font-medium">{t('Faol')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="py-2 pr-2">
                  <input
                    aria-label={t('Nomi')}
                    defaultValue={row.name}
                    disabled={!editable}
                    onBlur={(e) =>
                      e.target.value !== row.name && patch(row.id, { name: e.target.value })
                    }
                    className={cell}
                  />
                </td>
                <td className="py-2 pr-2">
                  <Select
                    aria-label={t('Qaytarish')}
                    value={row.refund_mode}
                    disabled={!editable}
                    onChange={(e) =>
                      patch(row.id, { refund_mode: e.target.value as AbsenceKind['refund_mode'] })
                    }
                  >
                    {MODES.map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </td>
                <td className="py-2 pr-2">
                  <input
                    aria-label={t('Kuniga (soʻm)')}
                    inputMode="numeric"
                    placeholder={t('ovqat puli')}
                    defaultValue={row.daily_amount ?? ''}
                    disabled={!editable || row.refund_mode !== 'fixed_per_day'}
                    onBlur={(e) => {
                      const next = e.target.value.trim() || null
                      if (next !== row.daily_amount) patch(row.id, { daily_amount: next })
                    }}
                    className={cell}
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    aria-label={t('Kamida (kun)')}
                    type="number"
                    min={1}
                    defaultValue={row.min_days}
                    disabled={!editable}
                    onBlur={(e) => {
                      const next = Number(e.target.value)
                      if (next >= 1 && next !== row.min_days) patch(row.id, { min_days: next })
                    }}
                    className={cell}
                  />
                </td>
                <td className="py-2 pr-2">
                  <input
                    aria-label={t('Toʻliq stavka (kundan)')}
                    type="number"
                    min={1}
                    defaultValue={row.full_rate_from_days ?? ''}
                    disabled={!editable || row.refund_mode === 'full_rate'}
                    onBlur={(e) => {
                      const next = e.target.value ? Number(e.target.value) : null
                      if (next !== row.full_rate_from_days)
                        patch(row.id, { full_rate_from_days: next })
                    }}
                    className={cell}
                  />
                </td>
                <td className="py-2">
                  <input
                    type="checkbox"
                    aria-label={t('Faol')}
                    checked={row.is_active}
                    disabled={!editable}
                    onChange={(e) => patch(row.id, { is_active: e.target.checked })}
                    className="h-4 w-4 rounded border-slate-300 focus-visible:ring-2 focus-visible:ring-brand-500"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editable && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            create.mutate()
          }}
          className="mt-3 flex flex-wrap items-end gap-2"
        >
          <div>
            <label htmlFor="ak-name" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Yangi tur')}
            </label>
            <input
              id="ak-name"
              required
              value={draft.name}
              onChange={(e) => setDraft((p) => ({ ...p, name: e.target.value }))}
              className={cell}
            />
          </div>
          <div>
            <label htmlFor="ak-code" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Kod (lotin, oʻzgarmaydi)')}
            </label>
            <input
              id="ak-code"
              required
              pattern="[a-z0-9_-]+"
              value={draft.code}
              onChange={(e) => setDraft((p) => ({ ...p, code: e.target.value.toLowerCase() }))}
              className={cell}
            />
          </div>
          <button
            type="submit"
            disabled={create.isPending}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {t('Qoʻshish')}
          </button>
        </form>
      )}
    </section>
  )
}
