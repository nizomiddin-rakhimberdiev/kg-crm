/**
 * Rollar va ularning ruxsatlari (docs/04 §6).
 *
 * docs/02 §11.2 matritsasi — har bir tashkilot uchun **boshlang'ich holat**,
 * abadiy cheklov emas: bog'chalarning ish taqsimoti har xil, shuning uchun
 * tashkilot egasi istalgan rolning ruxsatlarini o'zgartira oladi va o'z
 * rollarini qo'sha oladi. Tizim rolining faqat KODI qotib qoladi — unga kod
 * ichida tekshiruvlar tayanadi.
 */

import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Lock, Plus, Save, ShieldCheck, Trash2 } from 'lucide-react'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { rolesApi } from '@/features/staff/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Permission } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

/** "Kassir yordamchisi" → "kassir_yordamchisi" */
const toCode = (name: string) =>
  name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

const ACTION_LABELS: Record<string, string> = {
  read: t('Koʻrish'),
  create: t('Yaratish'),
  update: t('Tahrirlash'),
  delete: t('Oʻchirish'),
  export: t('Eksport'),
  approve: t('Tasdiqlash'),
}

export function RolesPanel() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const { user } = useAuth()
  const isOwner = user?.role?.code === 'org_owner'
  // Delegatsiya (ADR-25): o'zida yo'q ruxsatni bera olmaydi.
  const grantable = (code: string) => isOwner || Boolean(user?.permissions.includes(code))

  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [newRoleName, setNewRoleName] = useState<string | null>(null)

  const rolesQuery = useQuery({
    queryKey: queryKeys.roles(organizationId),
    queryFn: rolesApi.list,
  })

  const permissionsQuery = useQuery({
    queryKey: queryKeys.permissions(organizationId),
    queryFn: rolesApi.permissions,
  })

  const roles = rolesQuery.data?.items ?? []
  const selectedRole = roles.find((r) => r.id === selectedRoleId) ?? roles[0] ?? null

  // Rol almashganda qoralamani serverdagi holatdan qayta tiklaymiz —
  // aks holda bir roldan boshqasiga o'tganda saqlanmagan belgilar
  // ko'chib qolardi.
  useEffect(() => {
    if (selectedRole) {
      setDraft(new Set(selectedRole.permissions))
      setSaved(false)
      setError(null)
    }
    // Bog'liqlik ATAYLAB `selectedRole` OBYEKTI emas, uning id'si va
    // ruxsatlar MAZMUNI. Obyekt har bir `refetch` da yangi havola
    // bo'ladi, ya'ni to'liq bog'liqlik foydalanuvchi belgilab turgan
    // qoralamani fon yangilanishida tozalab yuborardi.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRole?.id, selectedRole?.permissions.join(',')])

  const grouped = useMemo(() => {
    const byModule = new Map<string, Permission[]>()
    for (const permission of permissionsQuery.data ?? []) {
      const list = byModule.get(permission.module) ?? []
      list.push(permission)
      byModule.set(permission.module, list)
    }
    return [...byModule.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [permissionsQuery.data])

  const saveMutation = useMutation({
    mutationFn: (codes: string[]) => rolesApi.setPermissions(selectedRole!.id, codes),
    onSuccess: () => {
      setSaved(true)
      setError(null)
      void queryClient.invalidateQueries({ queryKey: queryKeys.roles(organizationId) })
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : t('Saqlab boʻlmadi.'))
    },
  })

  const createMutation = useMutation({
    mutationFn: rolesApi.create,
    onSuccess: (role) => {
      setNewRoleName(null)
      setError(null)
      setSelectedRoleId(role.id)
      void queryClient.invalidateQueries({ queryKey: queryKeys.roles(organizationId) })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Rol yaratilmadi.')),
  })

  const deleteMutation = useMutation({
    mutationFn: rolesApi.remove,
    onSuccess: () => {
      setSelectedRoleId(null)
      setError(null)
      void queryClient.invalidateQueries({ queryKey: queryKeys.roles(organizationId) })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Oʻchirib boʻlmadi.')),
  })

  const toggle = (code: string) => {
    setDraft((prev) => {
      const next = new Set(prev)
      if (next.has(code)) next.delete(code)
      else next.add(code)
      return next
    })
    setSaved(false)
  }

  // `can_edit` — backend hukmi: o'z roli, egasi roli va sizdan kengroq rol
  // tahrirlanmaydi.
  const editable = Boolean(selectedRole && can('users.update') && selectedRole.can_edit !== false)
  const dirty =
    selectedRole &&
    (draft.size !== selectedRole.permissions.length ||
      selectedRole.permissions.some((code) => !draft.has(code)))

  if (rolesQuery.isPending || permissionsQuery.isPending) {
    return <p className="py-8 text-center text-sm text-slate-500">{t('Yuklanmoqda…')}</p>
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
      {/* Rollar ro'yxati */}
      <div className="space-y-1 rounded-2xl border border-slate-200 bg-white p-2">
        {roles.map((role) => (
          <button
            key={role.id}
            type="button"
            onClick={() => setSelectedRoleId(role.id)}
            className={cn(
              'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition',
              selectedRole?.id === role.id
                ? 'bg-brand-50 font-medium text-brand-700'
                : 'text-slate-600 hover:bg-slate-50',
            )}
          >
            {role.is_system ? (
              <Lock className="h-3.5 w-3.5 shrink-0 text-slate-500" />
            ) : (
              <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-slate-500" />
            )}
            <span className="truncate">{role.name}</span>
          </button>
        ))}

        {can('users.create') && (
          <div className="mt-1 border-t border-slate-100 pt-1">
            {newRoleName === null ? (
              <button
                type="button"
                onClick={() => setNewRoleName('')}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-brand-700 transition hover:bg-brand-50"
              >
                <Plus className="h-3.5 w-3.5 shrink-0" />
                {t('Yangi rol')}
              </button>
            ) : (
              <form
                className="space-y-2 p-1"
                onSubmit={(event) => {
                  event.preventDefault()
                  const name = newRoleName.trim()
                  if (name) createMutation.mutate({ name, code: toCode(name) })
                }}
              >
                <input
                  autoFocus
                  value={newRoleName}
                  onChange={(e) => setNewRoleName(e.target.value)}
                  placeholder={t('Rol nomi')}
                  aria-label={t('Rol nomi')}
                  className="w-full rounded-lg border border-slate-200 px-2 py-1.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
                <div className="flex gap-1">
                  <button
                    type="submit"
                    disabled={!newRoleName.trim() || createMutation.isPending}
                    className="flex-1 rounded-lg bg-brand-600 px-2 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
                  >
                    {createMutation.isPending ? '…' : t('Qoʻshish')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewRoleName(null)}
                    className="rounded-lg border border-slate-200 px-2 py-1.5 text-xs text-slate-600 transition hover:bg-slate-50"
                  >
                    {t('Bekor')}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>

      {/* Ruxsatlar */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        {!selectedRole ? (
          <p className="py-8 text-center text-sm text-slate-500">{t('Rol tanlang.')}</p>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">{selectedRole.name}</h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  {selectedRole.is_system
                    ? t('Tizim roli: ruxsatlarini oʻzgartirish mumkin, nomi va kodi oʻzgarmaydi.')
                    : t('Maxsus rol — ruxsatlari ham, oʻzi ham toʻliq sizning ixtiyoringizda.')}
                </p>
                {selectedRole.can_edit === false && (
                  <p className="mt-1 text-xs text-amber-700">
                    {t(
                      'Bu rolni oʻzgartira olmaysiz: u sizning rolingiz, tashkilot egasi roli yoki sizdan kengroq huquqli rol.',
                    )}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2">
                {editable && (
                  <button
                    type="button"
                    disabled={!dirty || saveMutation.isPending}
                    onClick={() => saveMutation.mutate([...draft])}
                    className={cn(
                      'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition',
                      dirty && !saveMutation.isPending
                        ? 'bg-brand-600 text-white hover:bg-brand-700'
                        : 'bg-slate-100 text-slate-500',
                    )}
                  >
                    <Save className="h-4 w-4" />
                    {saveMutation.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
                  </button>
                )}
                {!selectedRole.is_system && can('users.delete') && editable && (
                  <button
                    type="button"
                    disabled={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(selectedRole.id)}
                    className="rounded-lg p-2 text-slate-500 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    title={t('Rolni oʻchirish')}
                    aria-label={t('Rolni oʻchirish')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
              >
                {error}
              </div>
            )}
            {saved && !dirty && (
              <div className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                {t('Saqlandi.')}
              </div>
            )}

            <div className="space-y-4">
              {grouped.map(([module, permissions]) => (
                <div key={module}>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {permissions[0]?.label.split(' — ')[0] ?? module}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {permissions.map((permission) => {
                      const active = draft.has(permission.code)
                      // Faol bo'lmagan va sizda yo'q ruxsatni yoqib bo'lmaydi.
                      const locked = !editable || (!active && !grantable(permission.code))
                      return (
                        <label
                          key={permission.code}
                          className={cn(
                            'flex cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition',
                            active
                              ? 'border-brand-200 bg-brand-50 text-brand-700'
                              : 'border-slate-200 text-slate-500',
                            locked && 'cursor-not-allowed opacity-70',
                          )}
                          title={
                            editable && locked
                              ? t('Sizda bu ruxsat yoʻq — uni bera olmaysiz.')
                              : undefined
                          }
                        >
                          <input
                            type="checkbox"
                            className="sr-only"
                            checked={active}
                            disabled={locked}
                            onChange={() => toggle(permission.code)}
                          />
                          {ACTION_LABELS[permission.action] ?? permission.action}
                        </label>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
