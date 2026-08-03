/**
 * Rollar va ularning ruxsatlari (docs/04 §6).
 *
 * Tizim rollari **faqat o'qish** uchun: ular docs/02 §11.2 matritsasidan
 * seed qilinadi va UI'dan o'zgartirilsa, hujjat bilan kod bir-biridan
 * ajralib ketardi. Maxsus rollar esa to'liq tahrirlanadi.
 */

import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Lock, Save, ShieldCheck } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { rolesApi } from '@/features/staff/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Permission } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const ACTION_LABELS: Record<string, string> = {
  read: "Ko'rish",
  create: 'Yaratish',
  update: 'Tahrirlash',
  delete: "O'chirish",
  export: 'Eksport',
  approve: 'Tasdiqlash',
}

export function RolesPanel() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

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
      setError(err instanceof ApiError ? err.message : 'Saqlab bo\'lmadi.')
    },
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

  const editable = Boolean(selectedRole && !selectedRole.is_system && can('users.update'))
  const dirty =
    selectedRole &&
    (draft.size !== selectedRole.permissions.length ||
      selectedRole.permissions.some((code) => !draft.has(code)))

  if (rolesQuery.isPending || permissionsQuery.isPending) {
    return <p className="py-8 text-center text-sm text-slate-400">Yuklanmoqda…</p>
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
              <Lock className="h-3.5 w-3.5 shrink-0 text-slate-400" />
            ) : (
              <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-slate-400" />
            )}
            <span className="truncate">{role.name}</span>
          </button>
        ))}
      </div>

      {/* Ruxsatlar */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        {!selectedRole ? (
          <p className="py-8 text-center text-sm text-slate-400">Rol tanlang.</p>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">{selectedRole.name}</h3>
                {selectedRole.is_system && (
                  <p className="mt-0.5 text-xs text-slate-500">
                    Tizim roli — ruxsatlari hujjatdagi matritsadan olinadi va
                    o'zgartirilmaydi.
                  </p>
                )}
              </div>

              {editable && (
                <button
                  type="button"
                  disabled={!dirty || saveMutation.isPending}
                  onClick={() => saveMutation.mutate([...draft])}
                  className={cn(
                    'flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition',
                    dirty && !saveMutation.isPending
                      ? 'bg-brand-600 text-white hover:bg-brand-700'
                      : 'bg-slate-100 text-slate-400',
                  )}
                >
                  <Save className="h-4 w-4" />
                  {saveMutation.isPending ? 'Saqlanmoqda…' : 'Saqlash'}
                </button>
              )}
            </div>

            {error && (
              <div role="alert" className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </div>
            )}
            {saved && !dirty && (
              <div className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                Saqlandi.
              </div>
            )}

            <div className="space-y-4">
              {grouped.map(([module, permissions]) => (
                <div key={module}>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    {permissions[0]?.label.split(' — ')[0] ?? module}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {permissions.map((permission) => {
                      const active = draft.has(permission.code)
                      return (
                        <label
                          key={permission.code}
                          className={cn(
                            'flex cursor-pointer items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs transition',
                            active
                              ? 'border-brand-200 bg-brand-50 text-brand-700'
                              : 'border-slate-200 text-slate-500',
                            !editable && 'cursor-not-allowed opacity-70',
                          )}
                        >
                          <input
                            type="checkbox"
                            className="sr-only"
                            checked={active}
                            disabled={!editable}
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
