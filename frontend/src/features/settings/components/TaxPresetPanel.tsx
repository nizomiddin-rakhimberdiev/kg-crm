/**
 * Soliq rejimi preseti (Bosqich 13.8, brif §9).
 *
 * Preset — bir bosishda stavkalarni yozadigan boshlangʻich qiymatlar:
 * keyin har birini pastdagi sozlamalarda alohida oʻzgartirish mumkin.
 * Qiymatlarni buxgalter tasdiqlaydi — bu huquqiy maslahat emas.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { settingsApi } from '@/features/notifications/api'
import { ApiError } from '@/lib/api/types'
import { t } from '@/lib/i18n'

export function TaxPresetPanel({ editable }: { editable: boolean }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: ['org', organizationId, 'settings', 'tax-presets'],
    queryFn: settingsApi.taxPresets,
  })
  const [chosen, setChosen] = useState('')
  const [error, setError] = useState<string | null>(null)
  const apply = useMutation({
    mutationFn: (preset: string) => settingsApi.applyTaxPreset(preset),
    onSuccess: () => {
      setError(null)
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'settings'] })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })
  const data = query.data
  if (!data) return null
  const value = chosen || data.current
  const preset = data.presets.find((row) => row.id === value)

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <h2 className="border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-900">
        {t('Soliq rejimi')}
      </h2>
      <div className="space-y-3 px-4 py-3">
        <p className="text-xs text-slate-500">{data.note}</p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="tax-preset" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Rejim')}
            </label>
            <select
              id="tax-preset"
              value={value}
              disabled={!editable}
              onChange={(event) => setChosen(event.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 disabled:bg-slate-50"
            >
              {data.presets.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.title}
                </option>
              ))}
            </select>
          </div>
          {editable && (
            <button
              type="button"
              disabled={apply.isPending}
              onClick={() => apply.mutate(value)}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {t('Stavkalarni qoʻllash')}
            </button>
          )}
        </div>
        {preset && (
          <ul className="grid gap-x-4 gap-y-0.5 text-xs text-slate-600 sm:grid-cols-2">
            {Object.entries(preset.values).map(([key, item]) => (
              <li key={key} className="flex justify-between gap-2">
                <span className="font-mono">{key}</span>
                <span className="tabular-nums">{String(item)}</span>
              </li>
            ))}
          </ul>
        )}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
      </div>
    </section>
  )
}
