/**
 * Filiallar — backend bilan ishlaydigan birinchi to'liq CRUD ekrani.
 *
 * Filiallar soni hech qachon cheklanmaydi va tarifga ta'sir qilmaydi
 * (docs/01 §4.5) — narx faqat bolalar soniga bog'liq.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Plus, Trash2 } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { branchesApi, type BranchInput } from '@/features/branches/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { EmptyRow } from '@/components/ui/EmptyState'
import { t } from '@/lib/i18n'

export default function BranchesPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [form, setForm] = useState<BranchInput>({ name: '', code: '' })
  const [formError, setFormError] = useState<string | null>(null)

  const branchesQuery = useQuery({
    queryKey: queryKeys.branches(organizationId),
    queryFn: branchesApi.list,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.branches(organizationId) })

  const createMutation = useMutation({
    mutationFn: branchesApi.create,
    onSuccess: () => {
      setForm({ name: '', code: '' })
      setFormError(null)
      void invalidate()
    },
    onError: (error) => {
      setFormError(error instanceof ApiError ? error.message : t('Xatolik yuz berdi.'))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: branchesApi.remove,
    onSuccess: invalidate,
    onError: (error) => {
      setFormError(error instanceof ApiError ? error.message : t('Xatolik yuz berdi.'))
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Filiallar')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('Bitta obuna — cheksiz filial. Toʻlov faqat bolalar soniga bogʻliq.')}
        </p>
      </div>

      {formError && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {formError}
        </div>
      )}

      {can('branches.create') && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate(form)
          }}
          className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4"
        >
          <div className="min-w-[200px] flex-1">
            <label htmlFor="branch-name" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Filial nomi')}
            </label>
            <input
              id="branch-name"
              required
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <div className="w-32">
            <label htmlFor="branch-code" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Kod')}
            </label>
            <input
              id="branch-code"
              required
              maxLength={20}
              value={form.code}
              onChange={(e) => setForm((p) => ({ ...p, code: e.target.value.toUpperCase() }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm uppercase outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className={cn(
              'flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition',
              createMutation.isPending ? 'opacity-60' : 'hover:bg-brand-700',
            )}
          >
            <Plus className="h-4 w-4" />
            {t('Qoʻshish')}
          </button>
        </form>
      )}

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {branchesQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
        )}

        {branchesQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-red-600">
            {branchesQuery.error instanceof ApiError
              ? branchesQuery.error.message
              : t('Maʼlumotni yuklab boʻlmadi.')}
          </p>
        )}

        {branchesQuery.data?.items.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">
            {t('Hozircha filial yoʻq.')}
          </p>
        )}

        {branchesQuery.data && branchesQuery.data.items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">{t('Nomi')}</th>
                  <th className="px-4 py-3 font-medium">{t('Kod')}</th>
                  <th className="px-4 py-3 font-medium">{t('Valyuta')}</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {branchesQuery.data.items.map((branch) => (
                  <tr key={branch.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-slate-400" />
                        <span className="font-medium text-slate-800">{branch.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{branch.code}</td>
                    <td className="px-4 py-3 text-slate-500">{branch.currency}</td>
                    <td className="px-4 py-3 text-right">
                      {can('branches.delete') && (
                        <button
                          type="button"
                          onClick={() => deleteMutation.mutate(branch.id)}
                          disabled={deleteMutation.isPending}
                          className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                          title={t('Oʻchirish')}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {branchesQuery.data.items.length === 0 && (
                  <EmptyRow
                    colSpan={5}
                    icon={Building2}
                    title={t('Filial yoʻq')}
                    hint={t(
                      'Bogʻchaning birinchi filiali roʻyxatdan oʻtishda yaratiladi. Yangi bino ochsangiz shu yerdan qoʻshasiz.',
                    )}
                  />
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
