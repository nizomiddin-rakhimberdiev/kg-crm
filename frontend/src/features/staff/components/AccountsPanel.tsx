/**
 * Tizim hisoblari — `/users` ustida (docs/04 §6).
 *
 * Bular login-parol bilan kiradigan odamlar: direktor, kassir, davomat
 * menejeri. Ro'yxat filial bo'yicha ham cheklanadi: Org Owner barcha
 * filiallarni ko'radi, Direktor faqat o'zinikini — bu backend'da hal
 * qilinadi, bu yerda filial filtri yozilmaydi.
 */

import { useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Pencil, Plus, Search, UserCheck, UserX } from 'lucide-react'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { Modal } from '@/components/ui/Modal'
import { Pagination } from '@/components/ui/primitives'
import { branchesApi } from '@/features/branches/api'
import { staffApi, type StaffInput } from '@/features/staff/api'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { usePageState } from '@/hooks/usePageState'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type StaffUser } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { avatarTone, cn, formatDateTime, initials } from '@/lib/utils'
import { t } from '@/lib/i18n'

const EMPTY_FORM: StaffInput = {
  full_name: '',
  email: '',
  phone: '',
  password: '',
  role_id: '',
  branch_id: '',
}

const dateTime = formatDateTime

const inputClass = (invalid?: boolean) =>
  cn(
    'w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2',
    invalid
      ? 'border-red-300 focus:ring-red-100'
      : 'border-slate-200 focus:border-brand-500 focus:ring-brand-100',
  )

export function AccountsPanel() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const { user } = useAuth()
  const isOwner = user?.role?.code === 'org_owner'
  // Filiallar ro'yxati (`branches.read`) bo'lmasa ham hisob ochish ishlashi
  // kerak: filialga bog'langan xodim faqat O'Z filialiga qo'sha oladi
  // (ADR-25), ya'ni tanlov baribir bitta. Avval forma `/branches` ni har
  // doim so'rardi va menejerda `403` bilan bo'sh qolib, hisob ochilmasdi.
  const canListBranches = can('branches.read')
  /** Hisobni boshqarish mumkinmi — backend qoidasining UI ko'zgusi. */
  const manageable = (member: StaffUser) =>
    isOwner || (member.id !== user?.id && Boolean(member.role?.can_assign))
  const { selectedBranchId } = useBranchScope()

  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim())
  const [pageSize, setPageSize] = useState(25)
  const [page, setPage] = usePageState(
    JSON.stringify([debouncedSearch, selectedBranchId, pageSize]),
  )
  const [showForm, setShowForm] = useState(false)
  // `null` — yangi hisob; obyekt — mavjudi tahrirlanyapti.
  const [editing, setEditing] = useState<StaffUser | null>(null)
  const [form, setForm] = useState<StaffInput>(EMPTY_FORM)
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
    setEditing(null)
    setForm(!isOwner && user?.branch ? { ...EMPTY_FORM, branch_id: user.branch.id } : EMPTY_FORM)
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  const openEdit = (member: StaffUser) => {
    setEditing(member)
    setForm({
      full_name: member.full_name,
      email: member.email,
      phone: member.phone ?? '',
      password: '', // bo'sh qoldirilsa parol o'zgarmaydi
      role_id: member.role?.id ?? '',
      branch_id: member.branch?.id ?? '',
    })
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  const params = {
    page,
    page_size: pageSize,
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(selectedBranchId ? { branch: selectedBranchId } : {}),
  }

  const staffQuery = useQuery({
    queryKey: queryKeys.users(organizationId, params),
    queryFn: () => staffApi.list(params),
    placeholderData: keepPreviousData,
  })
  const rolesQuery = useQuery({
    queryKey: queryKeys.roles(organizationId),
    queryFn: staffApi.roles,
    enabled: showForm,
  })
  const branchesQuery = useQuery({
    queryKey: queryKeys.branches(organizationId),
    queryFn: branchesApi.list,
    enabled: showForm && canListBranches,
  })
  const branchOptions = canListBranches
    ? (branchesQuery.data?.items ?? [])
    : user?.branch
      ? [user.branch]
      : []

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'users'] })

  const handleError = (err: unknown) => {
    if (err instanceof ApiError) {
      setError(err.message)
      setFieldErrors(err.fieldErrors())
    } else {
      setError(t('Xatolik yuz berdi.'))
    }
  }

  const createMutation = useMutation({
    mutationFn: staffApi.create,
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: handleError,
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<StaffInput> }) =>
      staffApi.update(id, payload),
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: handleError,
  })
  const deactivateMutation = useMutation({
    mutationFn: staffApi.deactivate,
    onSuccess: invalidate,
    onError: handleError,
  })
  const reactivateMutation = useMutation({
    mutationFn: staffApi.reactivate,
    onSuccess: invalidate,
    onError: handleError,
  })

  const saving = createMutation.isPending || updateMutation.isPending

  const submitForm = () => {
    const payload: Partial<StaffInput> = {
      full_name: form.full_name,
      email: form.email,
      phone: form.phone,
      role_id: form.role_id,
      branch_id: form.branch_id || null,
    }
    // Bo'sh parol "o'zgartirmaslik" degani — uni yubormaymiz, aks holda
    // serializer kuchsiz parol deb rad etadi.
    if (form.password) payload.password = form.password

    if (editing) {
      updateMutation.mutate({ id: editing.id, payload })
    } else {
      createMutation.mutate(payload as StaffInput)
    }
  }

  const selectedRole = rolesQuery.data?.items.find((r) => r.id === form.role_id)
  const branchRequired = selectedRole ? selectedRole.code !== 'org_owner' : true

  const pagination = staffQuery.data?.pagination
  const members = staffQuery.data?.items ?? []

  const renderName = (member: StaffUser) => (
    <div className="flex min-w-0 items-center gap-3">
      <span
        className={cn(
          'grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold',
          avatarTone(member.full_name),
        )}
      >
        {initials(member.full_name)}
      </span>
      <div className="min-w-0">
        {can('users.update') && manageable(member) ? (
          <button
            type="button"
            onClick={() => openEdit(member)}
            className="block max-w-full truncate text-left font-medium text-slate-800 transition hover:text-brand-700"
          >
            {member.full_name}
          </button>
        ) : (
          <p className="truncate font-medium text-slate-800">{member.full_name}</p>
        )}
        <p className="truncate text-xs text-slate-400">{member.email}</p>
        {member.phone && <p className="text-xs text-slate-400">{member.phone}</p>}
      </div>
    </div>
  )

  const renderStatus = (member: StaffUser) => (
    <span
      className={cn(
        'inline-flex shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium',
        member.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500',
      )}
    >
      {member.is_active ? t('Faol') : t('Faol emas')}
    </span>
  )

  const renderActions = (member: StaffUser) => (
    <div className="flex items-center justify-end gap-1">
      {can('users.update') && manageable(member) && (
        <button
          type="button"
          onClick={() => openEdit(member)}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          title={t('Tahrirlash')}
          aria-label={t('Tahrirlash')}
        >
          <Pencil className="h-4 w-4" />
        </button>
      )}
      {member.is_active
        ? can('users.delete') &&
          manageable(member) && (
            <button
              type="button"
              disabled={deactivateMutation.isPending}
              onClick={() => deactivateMutation.mutate(member.id)}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
              title={t('Faolsizlantirish')}
              aria-label={t('Faolsizlantirish')}
            >
              <UserX className="h-4 w-4" />
            </button>
          )
        : can('users.update') &&
          manageable(member) && (
            <button
              type="button"
              disabled={reactivateMutation.isPending}
              onClick={() => reactivateMutation.mutate(member.id)}
              className="rounded-lg p-2 text-slate-400 transition hover:bg-emerald-50 hover:text-emerald-700 disabled:opacity-50"
              title={t('Qayta faollashtirish')}
              aria-label={t('Qayta faollashtirish')}
            >
              <UserCheck className="h-4 w-4" />
            </button>
          )}
    </div>
  )

  return (
    <div className="space-y-4">
      {error && !showForm && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="relative flex-1 sm:min-w-[220px] sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('Ism yoki email boʻyicha qidirish…')}
            aria-label={t('Ism yoki email boʻyicha qidirish…')}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        {can('users.create') && (
          <button
            type="button"
            onClick={openCreate}
            className="flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 sm:ml-auto"
          >
            <Plus className="h-4 w-4" />
            {t('Hisob ochish')}
          </button>
        )}
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {staffQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
        )}
        {staffQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-red-600">
            {staffQuery.error instanceof ApiError
              ? staffQuery.error.message
              : t('Maʼlumotni yuklab boʻlmadi.')}
          </p>
        )}
        {staffQuery.data && members.length === 0 && (
          <div className="px-4 py-12 text-center">
            <KeyRound className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm text-slate-500">
              {debouncedSearch
                ? t('Shartga mos hisob topilmadi.')
                : t('Hozircha tizim hisobi yoʻq.')}
            </p>
          </div>
        )}

        {members.length > 0 && (
          <div className={cn('transition-opacity', staffQuery.isPlaceholderData && 'opacity-60')}>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="border-b border-slate-100 bg-slate-50/70 text-left text-xs uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t('Hisob')}</th>
                    <th className="px-4 py-3 font-medium">{t('Rol')}</th>
                    <th className="px-4 py-3 font-medium">{t('Filial')}</th>
                    <th className="px-4 py-3 font-medium">{t('Oxirgi kirish')}</th>
                    <th className="px-4 py-3 font-medium">{t('Holat')}</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {members.map((member) => (
                    <tr key={member.id} className="transition-colors hover:bg-slate-50/70">
                      <td className="px-4 py-3">{renderName(member)}</td>
                      <td className="px-4 py-3 text-slate-600">{member.role?.name ?? '—'}</td>
                      <td className="px-4 py-3 text-slate-600">
                        {member.branch?.name ?? t('Barcha filiallar')}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500 tabular-nums">
                        {dateTime(member.last_login_at)}
                      </td>
                      <td className="px-4 py-3">{renderStatus(member)}</td>
                      <td className="px-4 py-3">{renderActions(member)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="divide-y divide-slate-100 md:hidden">
              {members.map((member) => (
                <li key={member.id} className="space-y-3 px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    {renderName(member)}
                    {renderStatus(member)}
                  </div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-500">
                    <p className="truncate">
                      <span className="text-slate-400">{t('Rol:')}</span>{' '}
                      <span className="text-slate-700">{member.role?.name ?? '—'}</span>
                    </p>
                    <p className="truncate">
                      <span className="text-slate-400">{t('Filial:')}</span>{' '}
                      <span className="text-slate-700">{member.branch?.name ?? t('Barchasi')}</span>
                    </p>
                    <p className="col-span-2">
                      <span className="text-slate-400">{t('Oxirgi kirish:')}</span>{' '}
                      <span className="text-slate-700 tabular-nums">
                        {dateTime(member.last_login_at)}
                      </span>
                    </p>
                  </div>
                  <div className="flex justify-end">{renderActions(member)}</div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {pagination && (
          <Pagination
            page={pagination.page}
            totalPages={pagination.total_pages}
            count={pagination.count}
            pageSize={pagination.page_size}
            onPageChange={setPage}
            onPageSizeChange={setPageSize}
          />
        )}
      </div>

      <Modal open={showForm} onClose={closeForm} className="max-w-2xl">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            submitForm()
          }}
          className="space-y-4 p-5 sm:p-6"
        >
          <div className="pr-8">
            <h2 className="text-base font-semibold text-slate-900">
              {editing
                ? t('{full_name} — tahrirlash', { full_name: editing.full_name })
                : t('Yangi tizim hisobi')}
            </h2>
            {editing ? (
              <dl className="mt-2 grid gap-x-6 gap-y-1 text-xs text-slate-500 sm:grid-cols-3">
                <div className="flex gap-2">
                  <dt>{t('Holat:')}</dt>
                  <dd className={editing.is_active ? 'text-emerald-700' : 'text-slate-500'}>
                    {editing.is_active ? t('Faol') : t('Faol emas')}
                  </dd>
                </div>
                <div className="flex gap-2">
                  <dt>{t('Oxirgi kirish:')}</dt>
                  <dd>{dateTime(editing.last_login_at)}</dd>
                </div>
                <div className="flex gap-2">
                  <dt>{t('Qoʻshilgan:')}</dt>
                  <dd>{dateTime(editing.created_at)}</dd>
                </div>
              </dl>
            ) : (
              <p className="mt-0.5 text-xs text-slate-500">
                {t(
                  'Hisob egasi koʻrsatilgan email va parol bilan tizimga kiradi; nimani koʻrishi rolga bogʻliq.',
                )}
              </p>
            )}
          </div>

          {error && (
            <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            {(
              [
                ['full_name', t('Ism familiya'), 'text'],
                ['email', t('Email'), 'email'],
                ['phone', t('Telefon'), 'tel'],
                ['password', editing ? t('Yangi parol (ixtiyoriy)') : t('Parol'), 'password'],
              ] as const
            ).map(([key, label, type]) => (
              <div key={key}>
                <label
                  htmlFor={`acc-${key}`}
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {label}
                </label>
                <input
                  id={`acc-${key}`}
                  type={type}
                  required={key !== 'phone' && !(key === 'password' && editing)}
                  placeholder={
                    key === 'password' && editing
                      ? t('Oʻzgartirmaslik uchun boʻsh qoldiring')
                      : undefined
                  }
                  autoComplete={
                    key === 'password' ? 'new-password' : key === 'email' ? 'off' : undefined
                  }
                  value={form[key] ?? ''}
                  onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))}
                  className={inputClass(Boolean(fieldErrors[key]))}
                />
                {fieldErrors[key] && (
                  <p className="mt-1 text-xs text-red-600">{fieldErrors[key]}</p>
                )}
              </div>
            ))}

            <div>
              <label htmlFor="acc-role" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Rol')}
              </label>
              <select
                id="acc-role"
                required
                value={form.role_id}
                onChange={(e) => setForm((p) => ({ ...p, role_id: e.target.value }))}
                className={inputClass(Boolean(fieldErrors.role_id))}
              >
                <option value="">{t('Tanlang…')}</option>
                {/* Faqat bera oladigan rollar (ADR-25); tahrirlanayotgan
                    hisobning joriy roli ham ro'yxatda qoladi. */}
                {rolesQuery.data?.items
                  .filter((role) => role.can_assign !== false || role.id === form.role_id)
                  .map((role) => (
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
              <label htmlFor="acc-branch" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Filial')} {branchRequired && <span className="text-red-500">*</span>}
              </label>
              <select
                id="acc-branch"
                required={branchRequired}
                value={form.branch_id ?? ''}
                onChange={(e) => setForm((p) => ({ ...p, branch_id: e.target.value }))}
                className={inputClass(Boolean(fieldErrors.branch_id))}
              >
                {/* Egasi bo'lmagan xodim faqat o'z filialini ko'radi. */}
                {(isOwner || !branchRequired) && (
                  <option value="">
                    {branchRequired ? t('Tanlang…') : t('Barcha filiallar (Org Owner)')}
                  </option>
                )}
                {branchOptions.map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.name}
                  </option>
                ))}
              </select>
              {fieldErrors.branch_id && (
                <p className="mt-1 text-xs text-red-600">{fieldErrors.branch_id}</p>
              )}
            </div>
          </div>

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {saving ? t('Saqlanmoqda…') : t('Saqlash')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
