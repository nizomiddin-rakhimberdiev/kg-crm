/**
 * HR xodimlari — `/employees` ustida (docs/04 §11.1).
 *
 * Oylik oladigan har bir odam shu yerda: tarbiyachi, oshpaz, hamshira.
 * Tizimga kirish huquqi bu ro'yxatga aloqasi yo'q — u "Tizim hisoblari"
 * tabida.
 *
 * Ro'yxat serverda sahifalanadi (docs/04 §3) va sukut bo'yicha faqat
 * ishlayotganlarni ko'rsatadi: bo'shaganlar tarix uchun saqlanadi, lekin
 * kundalik ro'yxatni to'ldirib turmasligi kerak.
 */

import { useState } from 'react'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Briefcase, Pencil, Phone, Plus, Search, UserMinus, UserPlus } from 'lucide-react'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { Modal } from '@/components/ui/Modal'
import { Pagination } from '@/components/ui/primitives'
import { branchesApi } from '@/features/branches/api'
import { employeesApi, positionsApi, type EmployeeInput } from '@/features/staff/api'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { usePageState } from '@/hooks/usePageState'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Employee } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { avatarTone, cn, formatDate, formatMoney, initials } from '@/lib/utils'
import { t } from '@/lib/i18n'

const STATUS: Record<Employee['employment_status'], [string, string]> = {
  active: [t('Ishlayapti'), 'bg-emerald-50 text-emerald-700'],
  on_leave: [t("Ta'tilda"), 'bg-amber-50 text-amber-700'],
  terminated: [t("Bo'shagan"), 'bg-slate-100 text-slate-500'],
}

const EMPTY_FORM: EmployeeInput = {
  last_name: '',
  first_name: '',
  phone: '',
  position_id: '',
  hire_date: '',
  base_salary: '',
  official_salary: '',
  employment_status: 'active',
  termination_date: '',
}

const inputClass = (invalid?: boolean) =>
  cn(
    'w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2',
    invalid
      ? 'border-red-300 focus:ring-red-100'
      : 'border-slate-200 focus:border-brand-500 focus:ring-brand-100',
  )

export function EmployeesPanel() {
  const organizationId = useOrganizationId()
  const { user } = useAuth()
  const { selectedBranchId } = useBranchScope()
  // Org Owner'ning o'z filiali yo'q — xodim qaysi filialga tegishli
  // ekanini u ko'rsatishi kerak (ko'p filialli tashkilotda backend buni
  // talab qiladi). Qolgan rollarda filial backend'da o'zi aniqlanadi.
  const isOrgOwner = user?.role?.code === 'org_owner'
  const [branchId, setBranchId] = useState('')
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [search, setSearch] = useState('')
  const debouncedSearch = useDebouncedValue(search.trim())
  const [statusFilter, setStatusFilter] = useState<Employee['employment_status'] | ''>('active')
  const [pageSize, setPageSize] = useState(25)

  // `null` — yangi xodim; obyekt — mavjudi tahrirlanyapti.
  const [editing, setEditing] = useState<Employee | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<EmployeeInput>(EMPTY_FORM)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [confirmTerminate, setConfirmTerminate] = useState<Employee | null>(null)

  // Lavozim tez qo'shish — alohida sahifaga o'tmasdan.
  const [newPosition, setNewPosition] = useState('')

  const [page, setPage] = usePageState(
    JSON.stringify([debouncedSearch, statusFilter, selectedBranchId, pageSize]),
  )

  const params = {
    page,
    page_size: pageSize,
    ordering: 'last_name',
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(statusFilter ? { employment_status: statusFilter } : {}),
    ...(selectedBranchId ? { branch: selectedBranchId } : {}),
  }

  const employeesQuery = useQuery({
    queryKey: queryKeys.employees(organizationId, params),
    queryFn: () => employeesApi.list(params),
    placeholderData: keepPreviousData,
  })
  const positionsQuery = useQuery({
    queryKey: queryKeys.positions(organizationId),
    queryFn: positionsApi.list,
  })
  const branchesQuery = useQuery({
    queryKey: queryKeys.branches(organizationId),
    queryFn: branchesApi.list,
    enabled: isOrgOwner && showForm,
  })
  const branches = branchesQuery.data?.items ?? []
  const branchRequired = isOrgOwner && branches.length > 1

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'employees'] })
    // Oylik hisoblash xodimlar ro'yxatidan tuziladi — u ham yangilansin.
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'payroll'] })
  }

  const handleError = (err: unknown) => {
    if (err instanceof ApiError) {
      setError(err.message)
      setFieldErrors(err.fieldErrors())
    } else {
      setError(t('Xatolik yuz berdi.'))
    }
  }

  const closeForm = () => {
    setShowForm(false)
    setEditing(null)
    setForm(EMPTY_FORM)
    setFieldErrors({})
    setError(null)
    setNewPosition('')
  }

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    // Topbar'da filial tanlangan bo'lsa — o'sha; tanlov keyin o'zgartirilishi mumkin.
    setBranchId(selectedBranchId ?? '')
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  const openEdit = (employee: Employee) => {
    setEditing(employee)
    setForm({
      last_name: employee.last_name,
      first_name: employee.first_name,
      phone: employee.phone ?? '',
      position_id: employee.position ?? '',
      hire_date: employee.hire_date,
      base_salary: employee.base_salary,
      official_salary: employee.official_salary ?? '',
      employment_status: employee.employment_status,
      termination_date: employee.termination_date ?? '',
    })
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  const createMutation = useMutation({
    mutationFn: employeesApi.create,
    onSuccess: () => {
      closeForm()
      invalidate()
    },
    onError: handleError,
  })
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<EmployeeInput> }) =>
      employeesApi.update(id, payload),
    onSuccess: () => {
      closeForm()
      invalidate()
    },
    onError: handleError,
  })
  const terminateMutation = useMutation({
    mutationFn: employeesApi.terminate,
    onSuccess: () => {
      setConfirmTerminate(null)
      invalidate()
    },
    onError: (err) => {
      setConfirmTerminate(null)
      handleError(err)
    },
  })
  const createPosition = useMutation({
    mutationFn: (title: string) =>
      positionsApi.create({ title, ...(branchId ? { branch_id: branchId } : {}) }),
    onSuccess: (position) => {
      setNewPosition('')
      setForm((prev) => ({ ...prev, position_id: position.id }))
      void queryClient.invalidateQueries({ queryKey: queryKeys.positions(organizationId) })
    },
    onError: handleError,
  })

  const saving = createMutation.isPending || updateMutation.isPending

  const submitForm = () => {
    const payload: EmployeeInput = {
      last_name: form.last_name.trim(),
      first_name: form.first_name.trim(),
      phone: form.phone?.trim() ?? '',
      position_id: form.position_id || null,
      hire_date: form.hire_date,
      base_salary: form.base_salary,
      official_salary: form.official_salary || '0',
    }
    if (editing) {
      payload.employment_status = form.employment_status
      payload.termination_date =
        form.employment_status === 'terminated' && form.termination_date
          ? form.termination_date
          : null
      updateMutation.mutate({ id: editing.id, payload })
    } else {
      createMutation.mutate({ ...payload, ...(branchId ? { branch_id: branchId } : {}) })
    }
  }

  const pagination = employeesQuery.data?.pagination
  const employees = employeesQuery.data?.items ?? []
  const canWrite = can('payroll.update')

  const renderName = (employee: Employee) => (
    <div className="flex min-w-0 items-center gap-3">
      <span
        className={cn(
          'grid h-9 w-9 shrink-0 place-items-center rounded-full text-xs font-bold',
          avatarTone(employee.full_name),
        )}
      >
        {initials(employee.full_name)}
      </span>
      <div className="min-w-0">
        {canWrite ? (
          <button
            type="button"
            onClick={() => openEdit(employee)}
            className="block max-w-full truncate text-left font-medium text-slate-800 transition hover:text-brand-700"
          >
            {employee.full_name}
          </button>
        ) : (
          <p className="truncate font-medium text-slate-800">{employee.full_name}</p>
        )}
        {employee.phone ? (
          <a
            href={`tel:${employee.phone}`}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-brand-600"
          >
            <Phone className="h-3 w-3" />
            {employee.phone}
          </a>
        ) : (
          <p className="text-xs text-slate-300">{t("telefon yo'q")}</p>
        )}
      </div>
    </div>
  )

  const renderStatus = (status: Employee['employment_status']) => {
    const [label, tone] = STATUS[status]
    return (
      <span
        className={cn('inline-flex shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium', tone)}
      >
        {label}
      </span>
    )
  }

  const renderActions = (employee: Employee) =>
    canWrite ? (
      <div className="flex items-center justify-end gap-1">
        <button
          type="button"
          onClick={() => openEdit(employee)}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          title={t('Tahrirlash')}
        >
          <Pencil className="h-4 w-4" />
        </button>
        {employee.employment_status !== 'terminated' && can('payroll.delete') && (
          <button
            type="button"
            onClick={() => setConfirmTerminate(employee)}
            className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
            title={t("Ishdan bo'shatish")}
          >
            <UserMinus className="h-4 w-4" />
          </button>
        )}
      </div>
    ) : null

  return (
    <div className="space-y-4">
      {error && !showForm && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Filtrlar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="relative flex-1 sm:min-w-[220px] sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t('Ism, familiya yoki telefon…')}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
          aria-label={t('Holat')}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
        >
          <option value="active">{t('Ishlayotganlar')}</option>
          <option value="on_leave">{t("Ta'tildagilar")}</option>
          <option value="terminated">{t("Bo'shaganlar")}</option>
          <option value="">{t('Barchasi')}</option>
        </select>
        {can('payroll.create') && (
          <button
            type="button"
            onClick={openCreate}
            className="flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 sm:ml-auto"
          >
            <UserPlus className="h-4 w-4" />
            {t("Xodim qo'shish")}
          </button>
        )}
      </div>

      {/* Ro'yxat */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {employeesQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
        )}
        {employeesQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-red-600">
            {employeesQuery.error instanceof ApiError
              ? employeesQuery.error.message
              : t("Ma'lumotni yuklab bo'lmadi.")}
          </p>
        )}
        {employeesQuery.data && employees.length === 0 && (
          <div className="px-4 py-12 text-center">
            <Briefcase className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm text-slate-500">
              {debouncedSearch || statusFilter !== 'active'
                ? t('Shartga mos xodim topilmadi.')
                : t("Hozircha xodim yo'q.")}
            </p>
            {can('payroll.create') && !debouncedSearch && statusFilter === 'active' && (
              <button
                type="button"
                onClick={openCreate}
                className="mt-3 text-sm font-medium text-brand-600 hover:underline"
              >
                {t("Birinchi xodimni qo'shing")}
              </button>
            )}
          </div>
        )}

        {employees.length > 0 && (
          <div
            className={cn('transition-opacity', employeesQuery.isPlaceholderData && 'opacity-60')}
          >
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="border-b border-slate-100 bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t('Xodim')}</th>
                    <th className="px-4 py-3 font-medium">{t('Lavozim')}</th>
                    <th className="px-4 py-3 font-medium">{t('Ishga kirgan')}</th>
                    <th className="px-4 py-3 font-medium">{t('Holat')}</th>
                    <th className="px-4 py-3 text-right font-medium">{t('Maosh')}</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {employees.map((employee) => (
                    <tr key={employee.id} className="transition-colors hover:bg-slate-50/70">
                      <td className="px-4 py-3">{renderName(employee)}</td>
                      <td className="px-4 py-3 text-slate-600">{employee.position_title ?? '—'}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-slate-600 tabular-nums">
                        {formatDate(employee.hire_date)}
                      </td>
                      <td className="px-4 py-3">{renderStatus(employee.employment_status)}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-slate-700 tabular-nums">
                        {t("{formatMoney} so'm", {
                          formatMoney: formatMoney(Number(employee.base_salary)),
                        })}
                      </td>
                      <td className="px-4 py-3">{renderActions(employee)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="divide-y divide-slate-100 md:hidden">
              {employees.map((employee) => (
                <li key={employee.id} className="space-y-3 px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    {renderName(employee)}
                    {renderStatus(employee.employment_status)}
                  </div>
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-500">
                    <p className="truncate">
                      <span className="text-slate-400">{t('Lavozim:')}</span>{' '}
                      <span className="text-slate-700">{employee.position_title ?? '—'}</span>
                    </p>
                    <p>
                      <span className="text-slate-400">{t('Ishga kirgan:')}</span>{' '}
                      <span className="text-slate-700 tabular-nums">
                        {formatDate(employee.hire_date)}
                      </span>
                    </p>
                    <p className="col-span-2">
                      <span className="text-slate-400">{t('Maosh:')}</span>{' '}
                      <span className="font-medium text-slate-800 tabular-nums">
                        {t("{formatMoney} so'm", {
                          formatMoney: formatMoney(Number(employee.base_salary)),
                        })}
                      </span>
                    </p>
                  </div>
                  {canWrite && <div className="flex justify-end">{renderActions(employee)}</div>}
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

      {/* Forma — modal: telefonda ro'yxat ustida ochilgan forma sahifani
          uzaytirib yuborardi va foydalanuvchi qayerdaligini yo'qotardi. */}
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
                : t('Yangi xodim')}
            </h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {t(
                "Bazaviy maosh oylik hisoblashda nusxalanadi — keyin o'zgartirilsa, o'tgan oylar o'zgarmaydi.",
              )}
            </p>
          </div>

          {error && (
            <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            {(
              [
                ['last_name', t('Familiya'), 'text', true],
                ['first_name', t('Ism'), 'text', true],
                ['phone', t('Telefon'), 'tel', false],
                ['hire_date', t('Ishga kirgan sana'), 'date', true],
                ['base_salary', t("Oylik maosh (so'm)"), 'number', true],
                // Rasmiy qism (ADR-18): bankka, soliq ushlab qolingan
                // holda. Bo'sh qoldirilsa 0 — ya'ni hammasi naqd, va
                // hech bir eski raqam siljimaydi.
                ['official_salary', t("Shundan rasmiy (so'm)"), 'number', false],
              ] as const
            ).map(([key, label, type, required]) => (
              <div key={key}>
                <label
                  htmlFor={`emp-${key}`}
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {label}
                  {required && <span className="text-red-500"> *</span>}
                </label>
                <input
                  id={`emp-${key}`}
                  type={type}
                  required={required}
                  min={type === 'number' ? 0 : undefined}
                  step={type === 'number' ? '1000' : undefined}
                  inputMode={type === 'number' ? 'numeric' : type === 'tel' ? 'tel' : undefined}
                  placeholder={key === 'phone' ? '+998 90 123 45 67' : undefined}
                  value={form[key] ?? ''}
                  onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
                  className={inputClass(Boolean(fieldErrors[key]))}
                />
                {fieldErrors[key] && (
                  <p className="mt-1 text-xs text-red-600">{fieldErrors[key]}</p>
                )}
              </div>
            ))}

            {!editing && isOrgOwner && branches.length > 0 && (
              <div>
                <label
                  htmlFor="emp-branch"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {t('Filial')}
                  {branchRequired && <span className="text-red-500"> *</span>}
                </label>
                <select
                  id="emp-branch"
                  required={branchRequired}
                  value={branchId}
                  onChange={(e) => setBranchId(e.target.value)}
                  className={inputClass(Boolean(fieldErrors.branch_id))}
                >
                  <option value="">{branchRequired ? t('Tanlang…') : branches[0]?.name}</option>
                  {branches.map((branch) => (
                    <option key={branch.id} value={branch.id}>
                      {branch.name}
                    </option>
                  ))}
                </select>
                {fieldErrors.branch_id && (
                  <p className="mt-1 text-xs text-red-600">{fieldErrors.branch_id}</p>
                )}
              </div>
            )}

            <div>
              <label
                htmlFor="emp-position"
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t('Lavozim')}
              </label>
              <select
                id="emp-position"
                value={form.position_id ?? ''}
                onChange={(e) => setForm((prev) => ({ ...prev, position_id: e.target.value }))}
                className={inputClass(Boolean(fieldErrors.position_id))}
              >
                <option value="">{t('— tanlanmagan —')}</option>
                {positionsQuery.data?.items.map((position) => (
                  <option key={position.id} value={position.id}>
                    {position.title}
                    {position.department ? ` · ${position.department}` : ''}
                  </option>
                ))}
              </select>
              {fieldErrors.position_id && (
                <p className="mt-1 text-xs text-red-600">{fieldErrors.position_id}</p>
              )}
              {can('payroll.create') && (
                <div className="mt-2 flex gap-2">
                  <input
                    type="text"
                    value={newPosition}
                    onChange={(e) => setNewPosition(e.target.value)}
                    placeholder={t('Yangi lavozim nomi…')}
                    aria-label={t('Yangi lavozim')}
                    className="min-w-0 flex-1 rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-xs outline-none focus:border-brand-500"
                  />
                  <button
                    type="button"
                    disabled={
                      !newPosition.trim() ||
                      createPosition.isPending ||
                      (branchRequired && !branchId)
                    }
                    onClick={() => createPosition.mutate(newPosition.trim())}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    {t("Qo'shish")}
                  </button>
                </div>
              )}
            </div>

            {editing && (
              <>
                <div>
                  <label
                    htmlFor="emp-status"
                    className="mb-1 block text-xs font-medium text-slate-600"
                  >
                    {t('Holat')}
                  </label>
                  <select
                    id="emp-status"
                    value={form.employment_status}
                    onChange={(e) =>
                      setForm((prev) => ({
                        ...prev,
                        employment_status: e.target.value as Employee['employment_status'],
                      }))
                    }
                    className={inputClass(Boolean(fieldErrors.employment_status))}
                  >
                    {(Object.keys(STATUS) as Employee['employment_status'][]).map((status) => (
                      <option key={status} value={status}>
                        {STATUS[status][0]}
                      </option>
                    ))}
                  </select>
                </div>
                {form.employment_status === 'terminated' && (
                  <div>
                    <label
                      htmlFor="emp-termination"
                      className="mb-1 block text-xs font-medium text-slate-600"
                    >
                      {t("Bo'shagan sana")}
                    </label>
                    <input
                      id="emp-termination"
                      type="date"
                      min={form.hire_date || undefined}
                      value={form.termination_date ?? ''}
                      onChange={(e) =>
                        setForm((prev) => ({ ...prev, termination_date: e.target.value }))
                      }
                      className={inputClass(Boolean(fieldErrors.termination_date))}
                    />
                    {fieldErrors.termination_date && (
                      <p className="mt-1 text-xs text-red-600">{fieldErrors.termination_date}</p>
                    )}
                  </div>
                )}
              </>
            )}
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

      {/* Bo'shatish — tasdiq bilan: bu qaytarish uchun tahrirlash kerak
          bo'ladigan amal, bexosdan bosilmasin. */}
      <Modal
        open={Boolean(confirmTerminate)}
        onClose={() => setConfirmTerminate(null)}
        className="max-w-md"
      >
        {confirmTerminate && (
          <div className="p-5 sm:p-6">
            <h2 className="pr-8 text-base font-semibold text-slate-900">
              {t("Ishdan bo'shatish")}
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              <strong>{confirmTerminate.full_name}</strong>{' '}
              {t(
                "\"bo'shagan\" holatiga o'tadi va keyingi oylik hisoblashga kirmaydi. O'tgan oylardagi maosh tarixi saqlanib qoladi.",
              )}
            </p>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={() => setConfirmTerminate(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
              >
                {t('Bekor qilish')}
              </button>
              <button
                type="button"
                disabled={terminateMutation.isPending}
                onClick={() => terminateMutation.mutate(confirmTerminate.id)}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
              >
                {terminateMutation.isPending ? t('Bajarilmoqda…') : t("Bo'shatish")}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
