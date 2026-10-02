/**
 * Bolalar — tizimning markaziy ro'yxati (docs/04 §7).
 *
 * Filtr va qidiruv backend'da bajariladi: 300 bolali bog'chada butun
 * ro'yxatni brauzerga yuklab, u yerda filtrlash sahifani sekinlashtiradi
 * va sahifalash bilan ziddiyatga kiradi.
 *
 * Sahifalash ham serverda (docs/04 §3): `page`/`page_size` so'rovga
 * ketadi, `meta.pagination` javobdan o'qiladi. Filtr o'zgarganda sahifa
 * 1 ga qaytadi — aks holda "3-sahifa" yangi filtrda bo'sh chiqib,
 * "bola yo'q" degan noto'g'ri xulosa berardi.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Phone, Plus, Search, Trash2, Upload, Users } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { Pagination } from '@/components/ui/primitives'
import { childrenApi, groupsApi, type ChildInput } from '@/features/children/api'
import { ImportWizard } from '@/features/children/components/ImportWizard'
import { PricePicker } from '@/features/children/components/PricePicker'
import { priceFromChild, priceToPayload, type PriceValue } from '@/features/children/price'
import { tariffsApi } from '@/features/payments/api'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { usePageState } from '@/hooks/usePageState'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Child } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { avatarTone, cn, initials } from '@/lib/utils'
import { t } from '@/lib/i18n'

const STATUS_LABELS: Record<string, string> = {
  prospect: t('Nomzod'),
  active: t('Faol'),
  paused: t("To'xtatilgan"),
  graduated: t('Bitirgan'),
  withdrawn: t('Chiqib ketgan'),
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
  const debouncedSearch = useDebouncedValue(search.trim())
  const [statusFilter, setStatusFilter] = useState('')
  const [pageSize, setPageSize] = useState(25)
  const [showImport, setShowImport] = useState(false)
  const [showForm, setShowForm] = useState(false)
  // `null` — yangi bola qo'shilyapti; obyekt — mavjudi tahrirlanyapti.
  const [editing, setEditing] = useState<Child | null>(null)
  const [form, setForm] = useState<ChildInput>(EMPTY_FORM)
  // Guruh bolaning MAYDONI emas — u alohida biriktirish (`/children/{id}/enroll`),
  // chunki bola guruhdan guruhga ko'chadi va har ko'chish tarixda qoladi.
  // Shuning uchun u formada alohida holat sifatida yuriladi.
  const [formGroupId, setFormGroupId] = useState('')
  // Narx — tarif yoki individual summa (PricePicker).
  const [price, setPrice] = useState<PriceValue>({ tariffId: null, monthlyFee: null })
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)

  const closeForm = () => {
    setShowForm(false)
    setEditing(null)
    setForm(EMPTY_FORM)
    setPrice({ tariffId: null, monthlyFee: null })
    setFormGroupId('')
    setFieldErrors({})
    setError(null)
  }

  const openCreate = () => {
    if (showForm && !editing) return closeForm()
    setEditing(null)
    setForm(EMPTY_FORM)
    setPrice({ tariffId: null, monthlyFee: null })
    setFormGroupId('')
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
    setPrice(priceFromChild(child))
    setFormGroupId(child.current_group?.id ?? '')
    setFieldErrors({})
    setError(null)
    setShowForm(true)
  }

  // Filtr yoki sahifa hajmi o'zgarsa — birinchi sahifadan (hosila, effekt emas).
  const [page, setPage] = usePageState(
    JSON.stringify([debouncedSearch, statusFilter, selectedBranchId, pageSize]),
  )

  const params = {
    page,
    page_size: pageSize,
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(statusFilter ? { enrollment_status: statusFilter } : {}),
    ...(selectedBranchId ? { branch: selectedBranchId } : {}),
  }

  const childrenQuery = useQuery({
    queryKey: queryKeys.children(organizationId, params),
    queryFn: () => childrenApi.list(params),
    // Sahifa almashganda eski qatorlar yangisi kelguncha turadi —
    // jadval har bosishda bo'shab-to'lib "lipillamaydi".
    placeholderData: keepPreviousData,
  })

  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })

  // Tarif bolani qo'shayotganda darhol biriktiriladi: tarifsiz bolaga
  // hisob-faktura chiqarib bo'lmaydi (docs/03 §13.3), ya'ni uni keyinroq
  // qo'shish — oy oxirida "nega bu bola hisobga tushmadi?" degan savol.
  const tariffsQuery = useQuery({
    queryKey: queryKeys.tariffs(organizationId),
    queryFn: tariffsApi.list,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'children'] })

  const handleError = (err: unknown) => {
    if (err instanceof ApiError) {
      setError(err.message)
      setFieldErrors(err.fieldErrors())
    } else {
      setError(t('Xatolik yuz berdi.'))
    }
  }

  /**
   * Guruh bolaning maydoni emas, alohida biriktirish — shuning uchun
   * saqlash IKKI chaqiruvdan iborat. Biriktirish alohida `try` ichida:
   * guruh to'lgan bo'lsa (sig'im chegarasi) bola baribir saqlanib qolsin
   * va foydalanuvchi "bola yo'qoldi" deb o'ylamasin — xabar ko'rsatiladi,
   * guruhni keyin tanlaydi.
   */
  const enrollIfChosen = async (childId: string, groupId: string) => {
    if (!groupId) return
    try {
      await childrenApi.enroll(childId, groupId)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('Xatolik.'))
    }
  }

  const createMutation = useMutation({
    mutationFn: async (payload: ChildInput & { groupId: string }) => {
      const { groupId, ...childPayload } = payload
      const child = await childrenApi.create(childPayload)
      await enrollIfChosen(child.id, groupId)
      return child
    },
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: handleError,
  })

  const updateMutation = useMutation({
    mutationFn: async ({
      id,
      payload,
      groupId,
    }: {
      id: string
      payload: Partial<ChildInput>
      groupId: string
    }) => {
      const child = await childrenApi.update(id, payload)
      if (groupId !== (editing?.current_group?.id ?? '')) await enrollIfChosen(id, groupId)
      return child
    },
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: handleError,
  })

  const saving = createMutation.isPending || updateMutation.isPending

  const submitForm = () => {
    const { payload: pricePayload, error: priceError } = priceToPayload(price)
    if (priceError) {
      setError(priceError)
      setFieldErrors((prev) => ({ ...prev, monthly_fee: priceError }))
      return
    }
    const body = { ...form, ...pricePayload }
    if (editing) {
      updateMutation.mutate({ id: editing.id, payload: body, groupId: formGroupId })
    } else {
      createMutation.mutate({ ...body, branch_id: selectedBranchId, groupId: formGroupId })
    }
  }

  const removeMutation = useMutation({ mutationFn: childrenApi.remove, onSuccess: invalidate })

  const enrollMutation = useMutation({
    mutationFn: ({ childId, groupId }: { childId: string; groupId: string }) =>
      childrenApi.enroll(childId, groupId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik.')),
  })

  const pagination = childrenQuery.data?.pagination
  const total = pagination?.count ?? 0
  const children = childrenQuery.data?.items ?? []

  const primaryGuardian = (child: Child) =>
    child.guardians.find((g) => g.is_primary) ?? child.guardians[0] ?? null

  // Jadval va kartochka bir xil hujayralarni ishlatadi — ikki qobiq,
  // bitta mazmun: tugma yoki holat o'zgarsa, ikkalasi birga o'zgaradi.
  // Bular KOMPONENT emas, render-funksiya: sahifa ichida yangi komponent
  // tipi yaratilsa React uni har renderda qayta o'rnatadi va `<select>`
  // fokusi yo'qoladi.
  const renderName = (child: Child) => (
    <Link to={`/children/${child.id}`} className="group/name flex min-w-0 items-center gap-3">
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
          <span className="block truncate text-xs text-slate-400">{child.middle_name}</span>
        )}
      </span>
    </Link>
  )

  const renderStatus = (status: Child['enrollment_status']) => (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500',
      )}
    >
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          status === 'active' ? 'bg-emerald-500' : 'bg-slate-400',
        )}
      />
      {STATUS_LABELS[status] ?? status}
    </span>
  )

  const renderGroup = (child: Child) =>
    can('children.update') ? (
      <select
        aria-label={t('Guruh')}
        value={child.current_group?.id ?? ''}
        onChange={(e) =>
          e.target.value && enrollMutation.mutate({ childId: child.id, groupId: e.target.value })
        }
        className="max-w-[180px] rounded-lg border border-slate-200 px-2 py-1 text-xs outline-none focus:border-brand-500"
      >
        <option value="">{t('— guruhsiz —')}</option>
        {groupsQuery.data?.items.map((group) => (
          <option key={group.id} value={group.id}>
            {group.name}
            {group.capacity ? ` (${group.enrolled_count}/${group.capacity})` : ''}
          </option>
        ))}
      </select>
    ) : (
      <span className="text-sm text-slate-600">{child.current_group?.name ?? '—'}</span>
    )

  const renderActions = (child: Child) => (
    <div className="flex items-center justify-end gap-1">
      {can('children.update') && (
        <button
          type="button"
          onClick={() => openEdit(child)}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          title={t('Tahrirlash')}
        >
          <Pencil className="h-4 w-4" />
        </button>
      )}
      {can('children.delete') && (
        <button
          type="button"
          onClick={() => removeMutation.mutate(child.id)}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
          title={t("Arxivga o'tkazish")}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      {showImport && <ImportWizard onClose={() => setShowImport(false)} />}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Bolalar')}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {total > 0 ? t('Jami {total} ta bola', { total }) : t("Ro'yxat bo'sh")}
          </p>
        </div>
        <div className="flex w-full gap-2 sm:w-auto">
          {can('children.create') && (
            <>
              <button
                type="button"
                onClick={() => setShowImport(true)}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 sm:flex-none"
              >
                <Upload className="h-4 w-4" />
                {t('Import')}
              </button>
              <button
                type="button"
                onClick={openCreate}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 sm:flex-none"
              >
                <Plus className="h-4 w-4" />
                {t("Bola qo'shish")}
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
            {editing
              ? t('{full_name} — tahrirlash', { full_name: editing.full_name })
              : t('Yangi bola')}
          </h2>

          {(
            [
              ['last_name', t('Familiya'), 'text'],
              ['first_name', t('Ism'), 'text'],
              ['middle_name', t('Otasining ismi'), 'text'],
              ['date_of_birth', t("Tug'ilgan sana"), 'date'],
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
              {t('Jinsi')}
            </label>
            <select
              id="gender"
              value={form.gender}
              onChange={(e) =>
                setForm((p) => ({ ...p, gender: e.target.value as 'male' | 'female' }))
              }
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="male">{t("O'g'il bola")}</option>
              <option value="female">{t('Qiz bola')}</option>
            </select>
          </div>

          {/* Guruh va tarif — AYNAN shu yerda, qo'shish paytida.
              Ilgari ular ro'yxatdan va bola kartasidan alohida
              qo'yilardi: 40 ta bola kiritgan odam har biri uchun yana
              ikki joyga qaytishi kerak edi, tarifsiz qolgan bola esa
              oy oxirida hisob-fakturasiz qolardi. */}
          <div>
            <label htmlFor="form-group" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Guruh')}
            </label>
            <select
              id="form-group"
              value={formGroupId}
              onChange={(e) => setFormGroupId(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">{t('— guruhsiz —')}</option>
              {groupsQuery.data?.items.map((group) => {
                const full = group.capacity > 0 && group.enrolled_count >= group.capacity
                return (
                  <option key={group.id} value={group.id} disabled={full}>
                    {group.name}
                    {group.capacity ? ` (${group.enrolled_count}/${group.capacity})` : ''}
                    {full ? ` — ${t("Guruh to'lgan")}` : ''}
                  </option>
                )
              })}
            </select>
          </div>

          <div>
            <p className="mb-1 block text-xs font-medium text-slate-600">{t('Oylik narx')}</p>
            <PricePicker
              idPrefix="form"
              value={price}
              onChange={(next) => {
                setPrice(next)
                setFieldErrors(({ monthly_fee: _drop, ...rest }) => rest)
              }}
              tariffs={tariffsQuery.data?.items ?? []}
            />
            {fieldErrors.monthly_fee && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.monthly_fee}</p>
            )}
          </div>

          <div className="flex gap-2 sm:col-span-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {saving ? t('Saqlanmoqda…') : t('Saqlash')}
            </button>
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
        <div className="relative flex-1 sm:min-w-[220px] sm:max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={t("Ism yoki familiya bo'yicha…")}
            className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label={t('Holat')}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
        >
          <option value="">{t('Barcha holatlar')}</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
        {childrenQuery.isPending && (
          <p className="px-4 py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
        )}
        {childrenQuery.isError && (
          <p className="px-4 py-8 text-center text-sm text-red-600">
            {childrenQuery.error instanceof ApiError
              ? childrenQuery.error.message
              : t("Ma'lumotni yuklab bo'lmadi.")}
          </p>
        )}
        {childrenQuery.data && children.length === 0 && (
          <div className="px-4 py-12 text-center">
            <Users className="mx-auto mb-3 h-10 w-10 text-slate-200" />
            <p className="text-sm text-slate-500">
              {debouncedSearch || statusFilter
                ? t('Shartga mos bola topilmadi.')
                : t("Hozircha bola yo'q.")}
            </p>
            {can('children.create') && !debouncedSearch && !statusFilter && (
              <button
                type="button"
                onClick={() => setShowImport(true)}
                className="mt-3 text-sm font-medium text-brand-600 hover:underline"
              >
                {t('Excel/CSV dan import qilish')}
              </button>
            )}
          </div>
        )}

        {children.length > 0 && (
          <div
            className={cn('transition-opacity', childrenQuery.isPlaceholderData && 'opacity-60')}
          >
            {/* Jadval — planshet va undan keng ekranlar. */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="border-b border-slate-100 bg-slate-50/70 text-left text-[11px] uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t('Bola')}</th>
                    <th className="px-4 py-3 font-medium">{t('Yosh')}</th>
                    <th className="px-4 py-3 font-medium">{t('Guruh')}</th>
                    <th className="px-4 py-3 font-medium">{t('Vasiy')}</th>
                    <th className="px-4 py-3 font-medium">{t('Holat')}</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {children.map((child) => {
                    const primary = primaryGuardian(child)
                    return (
                      <tr key={child.id} className="transition-colors hover:bg-slate-50/70">
                        <td className="px-4 py-3">{renderName(child)}</td>
                        <td className="whitespace-nowrap px-4 py-3 text-slate-600 tabular-nums">
                          {t('{age_years} yosh', { age_years: child.age_years })}
                        </td>
                        <td className="px-4 py-3">{renderGroup(child)}</td>
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
                        <td className="px-4 py-3">{renderStatus(child.enrollment_status)}</td>
                        <td className="px-4 py-3">{renderActions(child)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Kartochkalar — telefon. Gorizontal skroll jadvali barmoq
                bilan ishlatib bo'lmaydigan darajada tor bo'lardi. */}
            <ul className="divide-y divide-slate-100 md:hidden">
              {children.map((child) => {
                const primary = primaryGuardian(child)
                return (
                  <li key={child.id} className="space-y-3 px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      {renderName(child)}
                      {renderStatus(child.enrollment_status)}
                    </div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-500">
                      <p>
                        <span className="text-slate-400">{t('Yosh:')}</span>{' '}
                        <span className="text-slate-700 tabular-nums">{child.age_years}</span>
                      </p>
                      <p className="truncate">
                        <span className="text-slate-400">{t('Vasiy:')}</span>{' '}
                        <span className="text-slate-700">{primary?.guardian.full_name ?? '—'}</span>
                      </p>
                      {primary && (
                        <a
                          href={`tel:${primary.guardian.phone}`}
                          className="col-span-2 flex items-center gap-1 text-slate-500 hover:text-brand-600"
                        >
                          <Phone className="h-3 w-3" />
                          {primary.guardian.phone}
                        </a>
                      )}
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      {renderGroup(child)}
                      {renderActions(child)}
                    </div>
                  </li>
                )
              })}
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
    </div>
  )
}
