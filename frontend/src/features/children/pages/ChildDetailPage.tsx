/**
 * Bola tafsiloti — vasiylar va guruh (docs/04 §7).
 *
 * Vasiy telefon bo'yicha topiladi yoki yaratiladi: bir oilaning ikkinchi
 * bolasini qo'shganda ota-ona takroriy yozuv sifatida yaratilmasligi kerak
 * (docs/03 §11.2). Bu backend'da hal qilinadi.
 */

import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Phone, Star, UserPlus } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { childrenApi, groupsApi } from '@/features/children/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const RELATIONS: Array<[string, string]> = [
  ['mother', 'Onasi'],
  ['father', 'Otasi'],
  ['grandparent', 'Buvi/bobo'],
  ['sibling', 'Aka/opa'],
  ['other', 'Boshqa'],
]

const EMPTY_GUARDIAN = {
  last_name: '',
  first_name: '',
  phone: '',
  relation: 'mother',
  is_primary: false,
}

export default function ChildDetailPage() {
  const { childId = '' } = useParams()
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [guardianForm, setGuardianForm] = useState(EMPTY_GUARDIAN)
  const [showGuardianForm, setShowGuardianForm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const childQuery = useQuery({
    queryKey: queryKeys.child(organizationId, childId),
    queryFn: () => childrenApi.get(childId),
    enabled: Boolean(childId),
  })

  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.child(organizationId, childId) })
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'children'] })
  }

  const addGuardian = useMutation({
    mutationFn: () => childrenApi.addGuardian(childId, guardianForm),
    onSuccess: () => {
      setGuardianForm(EMPTY_GUARDIAN)
      setShowGuardianForm(false)
      setError(null)
      invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Xatolik yuz berdi.'),
  })

  const enroll = useMutation({
    mutationFn: (groupId: string) => childrenApi.enroll(childId, groupId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : 'Xatolik yuz berdi.'),
  })

  if (childQuery.isPending) {
    return <p className="py-12 text-center text-sm text-slate-400">Yuklanmoqda…</p>
  }

  if (childQuery.isError || !childQuery.data) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-red-600">
          {childQuery.error instanceof ApiError ? childQuery.error.message : 'Bola topilmadi.'}
        </p>
        <Link to="/children" className="mt-3 inline-block text-sm text-brand-600 hover:underline">
          Ro'yxatga qaytish
        </Link>
      </div>
    )
  }

  const child = childQuery.data

  return (
    <div className="space-y-6">
      <Link
        to="/children"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft className="h-4 w-4" />
        Bolalar
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{child.full_name}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {child.age_years} yosh · {child.gender === 'male' ? "O'g'il bola" : 'Qiz bola'} ·
            tug'ilgan {child.date_of_birth}
          </p>
        </div>
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Guruh */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Guruh</h2>
          {can('children.update') ? (
            <select
              aria-label="Guruh"
              value={child.current_group?.id ?? ''}
              onChange={(e) => e.target.value && enroll.mutate(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
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
            <p className="text-sm text-slate-600">{child.current_group?.name ?? '—'}</p>
          )}
        </div>

        {/* Vasiylar */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Vasiylar</h2>
            {can('children.update') && (
              <button
                type="button"
                onClick={() => setShowGuardianForm((v) => !v)}
                className="flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:underline"
              >
                <UserPlus className="h-3.5 w-3.5" />
                Qo'shish
              </button>
            )}
          </div>

          {child.guardians.length === 0 && !showGuardianForm && (
            <p className="text-sm text-slate-400">Vasiy biriktirilmagan.</p>
          )}

          <ul className="space-y-2">
            {child.guardians.map((link) => (
              <li
                key={link.id}
                className="flex items-start justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="flex items-center gap-1.5 text-sm font-medium text-slate-800">
                    {link.guardian.full_name}
                    {link.is_primary && (
                      <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                    )}
                  </p>
                  <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-500">
                    <Phone className="h-3 w-3" />
                    {link.guardian.phone}
                  </p>
                </div>
                <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-xs text-slate-500">
                  {RELATIONS.find(([code]) => code === link.relation)?.[1] ?? link.relation}
                </span>
              </li>
            ))}
          </ul>

          {showGuardianForm && can('children.update') && (
            <form
              onSubmit={(event) => {
                event.preventDefault()
                addGuardian.mutate()
              }}
              className="mt-3 space-y-2 border-t border-slate-100 pt-3"
            >
              <div className="grid grid-cols-2 gap-2">
                <input
                  required
                  placeholder="Familiya"
                  value={guardianForm.last_name}
                  onChange={(e) =>
                    setGuardianForm((p) => ({ ...p, last_name: e.target.value }))
                  }
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
                <input
                  placeholder="Ism"
                  value={guardianForm.first_name}
                  onChange={(e) =>
                    setGuardianForm((p) => ({ ...p, first_name: e.target.value }))
                  }
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <input
                required
                type="tel"
                placeholder="+998 90 123 45 67"
                value={guardianForm.phone}
                onChange={(e) => setGuardianForm((p) => ({ ...p, phone: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
              <div className="flex items-center gap-2">
                <select
                  aria-label="Kim bo'ladi"
                  value={guardianForm.relation}
                  onChange={(e) =>
                    setGuardianForm((p) => ({ ...p, relation: e.target.value }))
                  }
                  className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                >
                  {RELATIONS.map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-1.5 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={guardianForm.is_primary}
                    onChange={(e) =>
                      setGuardianForm((p) => ({ ...p, is_primary: e.target.checked }))
                    }
                  />
                  Asosiy
                </label>
              </div>
              <button
                type="submit"
                disabled={addGuardian.isPending}
                className={cn(
                  'w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white',
                  addGuardian.isPending ? 'opacity-60' : 'hover:bg-brand-700',
                )}
              >
                {addGuardian.isPending ? 'Saqlanmoqda…' : 'Vasiyni biriktirish'}
              </button>
              <p className="text-xs text-slate-400">
                Bu telefon bilan vasiy allaqachon mavjud bo'lsa, yangi yozuv
                yaratilmaydi — mavjudi biriktiriladi.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
