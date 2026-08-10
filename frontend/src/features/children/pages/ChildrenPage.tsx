/**
 * Bolalar — tizimning markaziy ro'yxati (docs/04 §7).
 *
 * Filtr va qidiruv backend'da bajariladi: 300 bolali bog'chada butun
 * ro'yxatni brauzerga yuklab, u yerda filtrlash sahifani sekinlashtiradi
 * va sahifalash bilan ziddiyatga kiradi.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Phone, Plus, Search, Trash2, Upload, Users } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { childrenApi, groupsApi, type ChildInput } from '@/features/children/api'
import { ImportWizard } from '@/features/children/components/ImportWizard'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Child } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { avatarTone, cn, initials } from '@/lib/utils'

const STATUS_LABELS: Record<string, string> = {
  prospect: 'Nomzod',
  active: 'Faol',
  paused: "To'xtatilgan",
  graduated: 'Bitirgan',
  withdrawn: 'Chiqib ketgan',
}

const EMPTY_FORM: ChildInput = {
  first_name: '',
  last_name: '',
  middle_name: '',
  date_of_birth: '',
  gender: 'male',
}

export default function ChildrenPage() {
  const organizationId = useOrganizationId()
  const { selectedBranchId } = useBranchScope()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showImport, setShowImport] = useState(false)
  const [showForm, setShowForm] = useState(false)
  // `null` — yangi bola qo'shilyapti; obyekt — mavjudi tahrirlanyapti.
  const [editing, setEditing] = useState<Child | null>(null)
  const [form, setForm] = useState<ChildInput>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  const closeForm = () => {
    setShowForm(false)
    setEditing(null)
    setForm(EMPTY_FORM)
    setFieldErrors({})
    setError(null)
  }

  const openCreate = () => {
    if (showForm && !editing) return closeForm()
    setEditing(null)
    setForm(EMPTY_FORM)
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  const openEdit = (child: Child) => {
    setEditing(child)
    setForm({
      first_name: child.first_name,
      last_name: child.last_name,
      middle_name: child.middle_name ?? '',
      date_of_birth: child.date_of_birth,
      gender: child.gender,
    })
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  const params = {
    ...(search ? { search } : {}),
    ...(statusFilter ? { enrollment_status: statusFilter } : {}),
    ...(selectedBranchId ? { branch: selectedBranchId } : {}),
  }

  const childrenQuery = useQuery({
    queryKey: queryKeys.children(organizationId, params),
    queryFn: () => childrenApi.list(params),
  })

  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'children'] })

  const handleError = (err: unknown) => {
    if (err instanceof ApiError) {
      setError(err.message)
      setFieldErrors(err.fieldErrors())
    } else {
      setError('Xatolik yuz berdi.')
    }
  }

  const createMutation = useMutation({
    mutationFn: childrenApi.create,
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: handleError,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<ChildInput> }) =>
      childrenApi.update(id, payload),
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: handleError,
  })

  const saving = createMutation.isPending || updateMutation.isPending

  const submitForm = () => {
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload: form })
    } else {
      createMutation.mutate({ ...form, branch_id: selectedBranchId })
    }
  }

  const removeMutation = useMutation({ mutationFn: childrenApi.remove, onSuccess: invalidate })

  const enrollMutation = useMutation({
    mutationFn: ({ childId, groupId }: { childId: string; groupId: string }) =>
      childrenApi.enroll(childId, groupId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Xatolik.'),
  })

  const total = childrenQuery.data?.pagination?.count ?? 0

  return (
    <div className="space-y-6">
      {showImport && <ImportWizard onClose={() => setShowImport(false)} />}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Bolalar</h1>
          <p className="mt-1 text-sm text-slate-500">
            {total > 0 ? `Jami ${total} ta bola` : "Ro'yxat bo'sh"}
          </p>
        </div>
        <div className="flex gap-2">
          {can('children.create') && (
            <>
              <button
                type="button"
                onClick={() => setShowImport(true)}
                className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                <Upload className="h-4 w-4" />
                Import
              </button>
              <button
                type="button"
                onClick={openCreate}
                className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
              >
                <Plus className="h-4 w-4" />
                Bola qo'shish
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {showForm && can(editing ? 'children.update' : 'children.create') && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            submitForm()
          }}
          className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2"
        >
          <h2 className="text-sm font-semibold text-slate-800 sm:col-span-2">
            {editing ? `${editing.full_name} — tahrirlash` : 'Yangi bola'}
          </h2>

          {(
            [
              ['last_name', 'Familiya', 'text'],
              ['first_name', 'Ism', 'text'],
              ['middle_name', 'Otasining ismi', 'text'],
              ['date_of_birth', "Tug'ilgan sana", 'date'],
            ] as const
          ).map(([key, label, type]) => (
            <div key={key}>
              <label htmlFor={key} className="mb-1 block text-xs font-medium text-slate-600">
                {label}
              </label>
              <input
                id={key}
                type={type}
                required={key !== 'middle_name'}
                value={(form[key] as string) ?? ''}
                onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                className={cn(
                  'w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2',
                  fieldErrors[key]
                    ? 'border-red-300 focus:ring-red-100'
                    : 'border-slate-200 focus:border-brand-500 focus:ring-brand-100',
                )}
              />
              {fieldErrors[key] && <p className="mt-1 text-xs text-red-600">{fieldErrors[key]}</p>}
            </div>
          ))}

          <div>
            <label htmlFor="gender" className="mb-1 block text-xs font-medium text-slate-600">
              Jinsi
            </label>
            <select
              id="gender"
              value={form.gender}
              onChange={(e) =>
                setForm((p) => ({ ...p, gender: e.target.value as 'male' | 'female' }))
              }
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="male">O'g'il bola</option>
              <option value="female">Qiz bola</option>
            </select>
          </div>

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {saving ? 'Saqlanmoqda…' : 'Saqlash'}
            </button>
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              Bekor qilish
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Ism yoki familiya bo'yicha…"
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Holat"
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
        >
          <option value="">Barcha holatlar</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {childrenQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">Yuklanmoqda…</p>
        )}
        {childrenQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-red-600">
            {childrenQuery.error instanceof ApiError
              ? childrenQuery.error.message
              : "Ma'lumotni yuklab bo'lmadi."}
          </p>
        )}
        {childrenQuery.data?.items.length === 0 && (
          <div className="px-4 py-12 text-center">
            <Users className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm text-slate-500">Hozircha bola yo'q.</p>
            {can('children.create') && (
              <button
                type="button"
                onClick={() => setShowImport(true)}
                className="mt-3 text-sm font-medium text-brand-600 hover:underline"
              >
                Excel/CSV dan import qilish
              </button>
            )}
          </div>
        )}

        {childrenQuery.data && childrenQuery.data.items.length > 0 && (
          <table className="w-full text-sm">
            <thead className="border-b border-slate-100 bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3 font-medium">Bola</th>
                <th className="px-4 py-3 font-medium">Yosh</th>
                <th className="px-4 py-3 font-medium">Guruh</th>
                <th className="px-4 py-3 font-medium">Vasiy</th>
                <th className="px-4 py-3 font-medium">Holat</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {childrenQuery.data.items.map((child) => {
                const primary =
                  child.guardians.find((g) => g.is_primary) ?? child.guardians[0] ?? null
                return (
                  <tr key={child.id} className="transition-colors hover:bg-slate-50/70">
                    <td className="px-4 py-3">
                      <Link
                        to={`/children/${child.id}`}
                        className="group/name flex items-center gap-3"
                      >
                        <span
                          className={cn(
                            'grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold',
                            avatarTone(child.full_name),
                          )}
                        >
                          {initials(child.full_name)}
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-slate-800 transition-colors group-hover/name:text-brand-700">
                            {child.last_name} {child.first_name}
                          </span>
                          {child.middle_name && (
                            <span className="block truncate text-xs text-slate-400">
                              {child.middle_name}
                            </span>
                          )}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-600 tabular-nums">
                      {child.age_years} yosh
                    </td>
                    <td className="px-4 py-3">
                      {can('children.update') ? (
                        <select
                          aria-label="Guruh"
                          value={child.current_group?.id ?? ''}
                          onChange={(e) =>
                            e.target.value &&
                            enrollMutation.mutate({ childId: child.id, groupId: e.target.value })
                          }
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs outline-none focus:border-brand-500"
                        >
                          <option value="">— guruhsiz —</option>
                          {groupsQuery.data?.items.map((group) => (
                            <option key={group.id} value={group.id}>
                              {group.name}
                              {group.capacity ? ` (${group.enrolled_count}/${group.capacity})` : ''}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-slate-600">{child.current_group?.name ?? '—'}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {primary ? (
                        <>
                          <p className="truncate">{primary.guardian.full_name}</p>
                          <a
                            href={`tel:${primary.guardian.phone}`}
                            className="mt-0.5 flex items-center gap-1 text-xs text-slate-400 transition-colors hover:text-brand-600"
                          >
                            <Phone className="h-3 w-3" />
                            {primary.guardian.phone}
                          </a>
                        </>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
                          child.enrollment_status === 'active'
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-slate-100 text-slate-500',
                        )}
                      >
                        <span
                          className={cn(
                            'h-1.5 w-1.5 rounded-full',
                            child.enrollment_status === 'active'
                              ? 'bg-emerald-500'
                              : 'bg-slate-400',
                          )}
                        />
                        {STATUS_LABELS[child.enrollment_status] ?? child.enrollment_status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {can('children.update') && (
                          <button
                            type="button"
                            onClick={() => openEdit(child)}
                            className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                            title="Tahrirlash"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                        )}
                        {can('children.delete') && (
                          <button
                            type="button"
                            onClick={() => removeMutation.mutate(child.id)}
                            className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                            title="Arxivga o'tkazish"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
