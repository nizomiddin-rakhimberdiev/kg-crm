/**
 * Guruhlar (docs/04 §7.3).
 *
 * Sig'im `0` = cheklovsiz. Bu default ataylab: yangi guruh yaratayotgan
 * odam sig'imni bilmasligi mumkin va uni majburan so'rash ishqalanish
 * qo'shardi. Cheklov kerak bo'lganda keyin qo'yiladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Pencil, Plus, Trash2, Users2 } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { GroupChildrenModal } from '@/features/children/components/GroupChildrenModal'
import { groupsApi } from '@/features/children/api'
import { employeesApi } from '@/features/staff/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Group } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { avatarTone, cn, initials } from '@/lib/utils'
import { t } from '@/lib/i18n'

export default function GroupsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const EMPTY = { name: '', capacity: '', age_min: '', age_max: '', teacher_id: '' }
  const [form, setForm] = useState(EMPTY)
  // `null` — yangi guruh, obyekt — mavjudi tahrirlanyapti. Tahrir AYNI
  // formada ochiladi: guruh kartochkasi kichik, alohida modal ortiqcha.
  const [editing, setEditing] = useState<Group | null>(null)
  const [openGroup, setOpenGroup] = useState<{ id: string; name: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.groups(organizationId) })

  // Tarbiyachi tanlash uchun xodimlar ro'yxati (PLAN 2.6).
  const employeesQuery = useQuery({
    queryKey: queryKeys.employees(organizationId),
    queryFn: () => employeesApi.list({ page_size: 200 }),
  })

  const closeForm = () => {
    setEditing(null)
    setForm(EMPTY)
    setError(null)
  }

  const openEdit = (group: Group) => {
    setEditing(group)
    setForm({
      name: group.name,
      capacity: group.capacity ? String(group.capacity) : '',
      age_min: group.age_min === null ? '' : String(group.age_min),
      age_max: group.age_max === null ? '' : String(group.age_max),
      teacher_id: group.teacher_id ?? '',
    })
  }

  const payload = () => ({
    name: form.name,
    capacity: form.capacity ? Number(form.capacity) : 0,
    age_min: form.age_min === '' ? null : Number(form.age_min),
    age_max: form.age_max === '' ? null : Number(form.age_max),
    // Tarbiyachi (PLAN 2.6): biriktirilgandan keyin u FAQAT shu
    // guruhni ko'radi va faqat uning davomatini belgilaydi.
    teacher_id: form.teacher_id || null,
  })

  const createMutation = useMutation({
    mutationFn: groupsApi.create,
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, ...rest }: { id: string } & ReturnType<typeof payload>) =>
      groupsApi.update(id, rest),
    onSuccess: () => {
      closeForm()
      void invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const removeMutation = useMutation({
    mutationFn: groupsApi.remove,
    onSuccess: invalidate,
    // Backend to'la guruhni o'chirishga 422 qaytaradi — xabarni ko'rsatamiz.
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
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
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Guruhlar')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {editing
            ? t('{name} — tahrirlash', { name: editing.name })
            : t('Sigʻim boʻsh qoldirilsa — cheklovsiz.')}
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
            if (editing) updateMutation.mutate({ id: editing.id, ...payload() })
            else createMutation.mutate(payload())
          }}
          className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4"
        >
          <div className="min-w-[200px] flex-1">
            <label htmlFor="group-name" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Guruh nomi')}
            </label>
            <input
              id="group-name"
              required
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <div className="w-28">
            <label
              htmlFor="group-capacity"
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {t('Sigʻim')}
            </label>
            <input
              id="group-capacity"
              type="number"
              min={0}
              placeholder={t('cheksiz')}
              value={form.capacity}
              onChange={(e) => setForm((p) => ({ ...p, capacity: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          {/* Yosh oralig'i bazada boshidan bor edi, formada esa yo'q edi.
              U guruhni tanlashda yo'l ko'rsatadi: "3-4 yosh" degan guruhga
              6 yoshli bolani qo'yish xato ekanini odam darhol ko'radi. */}
          <div className="w-40">
            <label
              htmlFor="group-age-min"
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {t('Yosh oraligʻi')}
            </label>
            <div className="flex items-center gap-1">
              <input
                id="group-age-min"
                type="number"
                min={0}
                max={18}
                placeholder={t('dan')}
                value={form.age_min}
                onChange={(e) => setForm((p) => ({ ...p, age_min: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
              <span className="text-slate-400">–</span>
              <input
                id="group-age-max"
                type="number"
                min={0}
                max={18}
                placeholder={t('gacha')}
                value={form.age_max}
                onChange={(e) => setForm((p) => ({ ...p, age_max: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>
          </div>
          <div>
            <label
              htmlFor="group-teacher"
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {t('Tarbiyachi')}
            </label>
            <select
              id="group-teacher"
              value={form.teacher_id}
              onChange={(e) => setForm((p) => ({ ...p, teacher_id: e.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <option value="">{t('— biriktirilmagan —')}</option>
              {(employeesQuery.data?.items ?? []).map((employee) => (
                <option key={employee.id} value={employee.id}>
                  {employee.full_name}
                  {employee.position_title ? ` — ${employee.position_title}` : ''}
                </option>
              ))}
            </select>
            <p className="mt-1 text-[11px] text-slate-500">
              {t('Tizim hisobi bogʻlangan tarbiyachi faqat shu guruhni koʻradi.')}
            </p>
          </div>

          <button
            type="submit"
            disabled={createMutation.isPending || updateMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {editing ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {editing ? t('Saqlash') : t('Qoʻshish')}
          </button>
          {editing && (
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
          )}
        </form>
      )}

      {groupsQuery.isPending && (
        <p className="py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
      )}

      {groupsQuery.data?.items.length === 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center">
          <Users2 className="mx-auto mb-3 h-10 w-10 text-slate-200" />
          <p className="text-sm text-slate-500">{t('Hozircha guruh yoʻq.')}</p>
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
                    title={t('Guruh tarkibini koʻrish')}
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
                      {/* Nom QIRQILMAYDI (PLAN 4.7): "Quyoshli
                          bolalar guruhi" bir qatorda "Quyoshli
                          bola…" bo'lib qolardi va mudira ikki
                          o'xshash guruhni ajrata olmasdi. Ikki
                          qator + to'liq nom `title` da. */}
                      <span
                        title={group.name}
                        className="line-clamp-2 block font-semibold leading-tight text-slate-900"
                      >
                        {group.name}
                      </span>
                      <span className="mt-0.5 flex items-center gap-1 text-xs text-slate-400">
                        <Users2 className="h-3.5 w-3.5" />
                        {t('{enrolled_count} ta bola', { enrolled_count: group.enrolled_count })}
                        {limited && ` / ${group.capacity}`}
                      </span>
                      {group.teacher_name && (
                        <span
                          title={group.teacher_name}
                          className="block truncate text-xs text-slate-500"
                        >
                          {group.teacher_name}
                        </span>
                      )}
                      {(group.age_min !== null || group.age_max !== null) && (
                        <span className="mt-0.5 block text-xs text-slate-400">
                          {group.age_min ?? '0'}–{group.age_max ?? '∞'} {t('yosh')}
                        </span>
                      )}
                    </span>
                  </button>

                  <span className="flex shrink-0 items-center gap-0.5">
                    {can('children.update') && (
                      <button
                        type="button"
                        onClick={() => openEdit(group)}
                        className="rounded-lg p-1.5 text-slate-300 opacity-0 transition hover:bg-slate-100 hover:text-slate-700 focus:opacity-100 group-hover:opacity-100"
                        title={t('Tahrirlash')}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                    )}
                    {can('children.delete') && (
                      <button
                        type="button"
                        onClick={() => removeMutation.mutate(group.id)}
                        className="rounded-lg p-1.5 text-slate-300 opacity-0 transition hover:bg-red-50 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
                        title={t('Oʻchirish')}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </span>
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
                        {full ? t('Guruh toʻlgan') : t('{free} ta joy boʻsh', { free })}
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
                    {t('Sigʻim cheklanmagan')}
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
