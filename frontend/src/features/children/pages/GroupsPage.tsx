/**
 * Guruhlar (docs/04 §7.3).
 *
 * Sig'im `0` = cheklovsiz. Bu default ataylab: yangi guruh yaratayotgan
 * odam sig'imni bilmasligi mumkin va uni majburan so'rash ishqalanish
 * qo'shardi. Cheklov kerak bo'lganda keyin qo'yiladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Users2 } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { GroupChildrenModal } from '@/features/children/components/GroupChildrenModal'
import { groupsApi } from '@/features/children/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { avatarTone, cn, initials } from '@/lib/utils'

export default function GroupsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [form, setForm] = useState({ name: '', capacity: '' })
  const [openGroup, setOpenGroup] = useState<{ id: string; name: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.groups(organizationId) })

  const createMutation = useMutation({
    mutationFn: groupsApi.create,
    onSuccess: () => {
      setForm({ name: '', capacity: '' })
      setError(null)
      void invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Xatolik yuz berdi.'),
  })

  const removeMutation = useMutation({
    mutationFn: groupsApi.remove,
    onSuccess: invalidate,
    // Backend to'la guruhni o'chirishga 422 qaytaradi — xabarni ko'rsatamiz.
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Xatolik yuz berdi.'),
  })

  return (
    <div className="space-y-6">
      {openGroup && (
        <GroupChildrenModal
          groupId={openGroup.id}
          groupName={openGroup.name}
          onClose={() => setOpenGroup(null)}
        />
      )}

      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Guruhlar</h1>
        <p className="mt-1 text-sm text-slate-500">
          Sig'im bo'sh qoldirilsa — cheklovsiz.
        </p>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {can('children.create') && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate({
              name: form.name,
              capacity: form.capacity ? Number(form.capacity) : 0,
            })
          }}
          className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4"
        >
          <div className="min-w-[200px] flex-1">
            <label htmlFor="group-name" className="mb-1 block text-xs font-medium text-slate-600">
              Guruh nomi
            </label>
            <input
              id="group-name"
              required
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <div className="w-32">
            <label
              htmlFor="group-capacity"
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              Sig'im
            </label>
            <input
              id="group-capacity"
              type="number"
              min={0}
              placeholder="cheksiz"
              value={form.capacity}
              onChange={(e) => setForm((p) => ({ ...p, capacity: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            <Plus className="h-4 w-4" />
            Qo'shish
          </button>
        </form>
      )}

      {groupsQuery.isPending && (
        <p className="py-8 text-center text-sm text-slate-400">Yuklanmoqda…</p>
      )}

      {groupsQuery.data?.items.length === 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center">
          <Users2 className="mx-auto mb-3 h-10 w-10 text-slate-200" />
          <p className="text-sm text-slate-500">Hozircha guruh yo'q.</p>
        </div>
      )}

      {groupsQuery.data && groupsQuery.data.items.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {groupsQuery.data.items.map((group) => {
            const limited = group.capacity > 0
            const full = limited && group.enrolled_count >= group.capacity
            const free = limited ? Math.max(group.capacity - group.enrolled_count, 0) : null
            const percent = limited
              ? Math.min(Math.round((group.enrolled_count / group.capacity) * 100), 100)
              : 0
            // Sariq faqat 90% dan oshganda: erta ogohlantirish shovqin bo'ladi,
            // kech ogohlantirish esa foydasiz.
            const nearFull = limited && percent >= 90

            return (
              <div
                key={group.id}
                className="group rounded-2xl border border-slate-200 bg-white p-4 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md"
              >
                <div className="flex items-start gap-3">
                  <button
                    type="button"
                    onClick={() => setOpenGroup({ id: group.id, name: group.name })}
                    title="Guruh tarkibini ko'rish"
                    className="flex min-w-0 flex-1 items-start gap-3 text-left"
                  >
                    <span
                      className={cn(
                        'grid h-11 w-11 shrink-0 place-items-center rounded-xl text-sm font-bold',
                        avatarTone(group.name),
                      )}
                    >
                      {initials(group.name)}
                    </span>

                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-semibold text-slate-900">
                        {group.name}
                      </span>
                      <span className="mt-0.5 flex items-center gap-1 text-xs text-slate-400">
                        <Users2 className="h-3.5 w-3.5" />
                        {group.enrolled_count} ta bola
                        {limited && ` / ${group.capacity}`}
                      </span>
                    </span>
                  </button>

                  {can('children.delete') && (
                    <button
                      type="button"
                      onClick={() => removeMutation.mutate(group.id)}
                      className="shrink-0 rounded-lg p-1.5 text-slate-300 opacity-0 transition hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
                      title="O'chirish"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>

                {limited ? (
                  <div className="mt-4">
                    <div className="mb-1.5 flex items-baseline justify-between">
                      <span
                        className={cn(
                          'text-xs font-medium',
                          full ? 'text-amber-700' : 'text-slate-500',
                        )}
                      >
                        {full ? "Guruh to'lgan" : `${free} ta joy bo'sh`}
                      </span>
                      <span className="text-xs font-semibold tabular-nums text-slate-400">
                        {percent}%
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all duration-500',
                          nearFull ? 'bg-amber-500' : 'bg-brand-500',
                        )}
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <p className="mt-4 inline-flex rounded-full bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-500">
                    Sig'im cheklanmagan
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
