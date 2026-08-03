/**
 * Xodimlar — haqiqiy `/users` endpointi ustida (docs/04 §6).
 *
 * Ro'yxat filial bo'yicha ham cheklanadi: Org Owner barcha filiallarni
 * ko'radi, Direktor faqat o'zinikini. Bu backend'da hal qilinadi —
 * bu yerda hech qanday filial filtri yozilmaydi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, UserX } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { branchesApi } from '@/features/branches/api'
import { RolesPanel } from '@/features/staff/components/RolesPanel'
import { staffApi, type StaffInput } from '@/features/staff/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const EMPTY_FORM: StaffInput = {
  full_name: '',
  email: '',
  phone: '',
  password: '',
  role_id: '',
  branch_id: '',
}

export default function StaffPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [tab, setTab] = useState<'staff' | 'roles'>('staff')
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<StaffInput>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  // Topbar'dagi filial tanlovi ro'yxatga qo'llanadi. Bu qulaylik, himoya
  // emas: backend queryset'i allaqachon tashkilot bilan cheklangan.
  const { selectedBranchId } = useBranchScope()

  const staffQuery = useQuery({
    queryKey: queryKeys.users(organizationId, { search, branch: selectedBranchId }),
    queryFn: () =>
      staffApi.list({
        ...(search ? { search } : {}),
        ...(selectedBranchId ? { branch: selectedBranchId } : {}),
      }),
  })

  const rolesQuery = useQuery({
    queryKey: queryKeys.roles(organizationId),
    queryFn: staffApi.roles,
    enabled: showForm,
  })

  const branchesQuery = useQuery({
    queryKey: queryKeys.branches(organizationId),
    queryFn: branchesApi.list,
    enabled: showForm,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'users'] })

  const createMutation = useMutation({
    mutationFn: staffApi.create,
    onSuccess: () => {
      setForm(EMPTY_FORM)
      setShowForm(false)
      setError(null)
      setFieldErrors({})
      void invalidate()
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setError(err.message)
        setFieldErrors(err.fieldErrors())
      } else {
        setError('Xatolik yuz berdi.')
      }
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: staffApi.deactivate,
    onSuccess: invalidate,
  })

  const selectedRole = rolesQuery.data?.items.find((r) => r.id === form.role_id)
  const branchRequired = selectedRole ? selectedRole.code !== 'org_owner' : true

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Xodimlar</h1>
          <p className="mt-1 text-sm text-slate-500">
            Xodimlar soni cheklanmagan — narx faqat bolalar soniga bog'liq.
          </p>
        </div>
        {tab === 'staff' && can('users.create') && (
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            <Plus className="h-4 w-4" />
            Xodim qo'shish
          </button>
        )}
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(
          [
            ['staff', 'Xodimlar'],
            ['roles', 'Rollar va ruxsatlar'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
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

      {tab === 'roles' && <RolesPanel />}

      {tab === 'staff' && error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {tab === 'staff' && showForm && can('users.create') && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate({ ...form, branch_id: form.branch_id || null })
          }}
          className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2"
        >
          {(
            [
              ['full_name', 'Ism familiya', 'text'],
              ['email', 'Email', 'email'],
              ['phone', 'Telefon', 'tel'],
              ['password', 'Parol', 'password'],
            ] as const
          ).map(([key, label, type]) => (
            <div key={key}>
              <label htmlFor={key} className="mb-1 block text-xs font-medium text-slate-600">
                {label}
              </label>
              <input
                id={key}
                type={type}
                required={key !== 'phone'}
                value={form[key] ?? ''}
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
            <label htmlFor="role_id" className="mb-1 block text-xs font-medium text-slate-600">
              Rol
            </label>
            <select
              id="role_id"
              required
              value={form.role_id}
              onChange={(e) => setForm((p) => ({ ...p, role_id: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">Tanlang…</option>
              {rolesQuery.data?.items.map((role) => (
                <option key={role.id} value={role.id}>
                  {role.name}
                </option>
              ))}
            </select>
            {fieldErrors.role_id && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.role_id}</p>
            )}
          </div>

          <div>
            <label htmlFor="branch_id" className="mb-1 block text-xs font-medium text-slate-600">
              Filial {branchRequired && <span className="text-red-500">*</span>}
            </label>
            <select
              id="branch_id"
              required={branchRequired}
              value={form.branch_id ?? ''}
              onChange={(e) => setForm((p) => ({ ...p, branch_id: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">
                {branchRequired ? 'Tanlang…' : 'Barcha filiallar (Org Owner)'}
              </option>
              {branchesQuery.data?.items.map((branch) => (
                <option key={branch.id} value={branch.id}>
                  {branch.name}
                </option>
              ))}
            </select>
            {fieldErrors.branch_id && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.branch_id}</p>
            )}
          </div>

          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {createMutation.isPending ? 'Saqlanmoqda…' : 'Saqlash'}
            </button>
          </div>
        </form>
      )}

      {tab === 'staff' && (
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Ism yoki email bo'yicha qidirish…"
          className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
      </div>
      )}

      {tab === 'staff' && (
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {staffQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">Yuklanmoqda…</p>
        )}
        {staffQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-red-600">
            {staffQuery.error instanceof ApiError
              ? staffQuery.error.message
              : "Ma'lumotni yuklab bo'lmadi."}
          </p>
        )}
        {staffQuery.data?.items.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">Xodim topilmadi.</p>
        )}

        {staffQuery.data && staffQuery.data.items.length > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Xodim</th>
                <th className="px-4 py-3 font-medium">Rol</th>
                <th className="px-4 py-3 font-medium">Filial</th>
                <th className="px-4 py-3 font-medium">Holat</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {staffQuery.data.items.map((member) => (
                <tr key={member.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-800">{member.full_name}</p>
                    <p className="text-xs text-slate-400">{member.email}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{member.role?.name ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {member.branch?.name ?? 'Barcha filiallar'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-medium',
                        member.is_active
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-500',
                      )}
                    >
                      {member.is_active ? 'Faol' : 'Faol emas'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {can('users.delete') && member.is_active && (
                      <button
                        type="button"
                        onClick={() => deactivateMutation.mutate(member.id)}
                        className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                        title="Faolsizlantirish"
                      >
                        <UserX className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      )}
    </div>
  )
}
