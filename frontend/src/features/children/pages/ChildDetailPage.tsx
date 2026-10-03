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
import { Archive, ArrowLeft, Pencil, Phone, Star, Unlink, UserPlus } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { childrenApi, groupsApi } from '@/features/children/api'
import { PricePicker } from '@/features/children/components/PricePicker'
import { priceFromChild, priceToPayload, type PriceValue } from '@/features/children/price'
import { tariffsApi } from '@/features/payments/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { ChildBalanceCard } from '@/features/children/components/ChildBalanceCard'
import { ChildEditDialog } from '@/features/children/components/ChildEditDialog'
import { ChildStatusDialog } from '@/features/children/components/ChildStatusDialog'
import { ChildTabs } from '@/features/children/components/ChildTabs'
import { TelegramLinkButton } from '@/features/children/components/TelegramLinkButton'
import { GroupOptions } from '@/features/children/components/GroupOptions'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate, formatUZS } from '@/lib/utils'
import { t } from '@/lib/i18n'

const RELATIONS: Array<[string, string]> = [
  ['mother', t('Onasi')],
  ['father', t('Otasi')],
  ['grandparent', 'Buvi/bobo'],
  ['sibling', 'Aka/opa'],
  ['other', t('Boshqa')],
]

const STATUS_LABEL: Record<string, string> = {
  prospect: t('Nomzod'),
  active: t('Faol'),
  paused: t('Toʻxtatilgan'),
  graduated: t('Bitirgan'),
  withdrawn: t('Chiqib ketgan'),
}

const STATUS_TONE: Record<string, string> = {
  active: 'bg-nihol-50 text-nihol-700',
  prospect: 'bg-ildiz-50 text-ildiz-700',
  paused: 'bg-orik-50 text-orik-700',
  graduated: 'bg-tosh-100 text-tosh-600',
  withdrawn: 'bg-tosh-100 text-tosh-600',
}

const EMPTY_GUARDIAN = {
  last_name: '',
  first_name: '',
  phone: '',
  relation: 'mother',
  is_primary: false,
  // Bo'sh — bog'chaning sukut tili. Ruscha gaplashadigan oila
  // ruscha SMS olishi kerak (PLAN 3.4).
  language: '',
}

export default function ChildDetailPage() {
  const { childId = '' } = useParams()
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const [guardianForm, setGuardianForm] = useState(EMPTY_GUARDIAN)
  const [showGuardianForm, setShowGuardianForm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Guruh TASDIQ bilan o'zgaradi (PLAN 1.4): sichqoncha g'ildiragining
  // bitta aylanishi bolani boshqa guruhga ko'chirib yuborardi. Narx esa
  // aniq "Saqlash" tugmasi bilan (PricePicker) — u ham tasdiq.
  const [pendingGroup, setPendingGroup] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [changingStatus, setChangingStatus] = useState(false)
  const [archiving, setArchiving] = useState(false)
  // Narx qoralamasi: `null` — tahrirlanmagan, serverdagi qiymat ko'rsatiladi.
  // Summa yozilayotganda har harfda saqlamaslik uchun qoralama + "Saqlash".
  const [priceDraft, setPriceDraft] = useState<PriceValue | null>(null)

  const childQuery = useQuery({
    queryKey: queryKeys.child(organizationId, childId),
    queryFn: () => childrenApi.get(childId),
    enabled: Boolean(childId),
  })

  const groupsQuery = useQuery({
    queryKey: queryKeys.groups(organizationId),
    queryFn: groupsApi.list,
  })

  const tariffsQuery = useQuery({
    queryKey: queryKeys.tariffs(organizationId),
    queryFn: tariffsApi.list,
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
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const savePrice = useMutation({
    mutationFn: (payload: { tariff_id: string | null; monthly_fee: string | null }) =>
      childrenApi.update(childId, payload),
    onSuccess: () => {
      setPriceDraft(null)
      setError(null)
      invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const enroll = useMutation({
    mutationFn: (groupId: string) => childrenApi.enroll(childId, groupId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const archive = useMutation({
    mutationFn: () =>
      childQuery.data?.archived_at ? childrenApi.restore(childId) : childrenApi.archive(childId),
    onSuccess: () => {
      setArchiving(false)
      invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const unlinkGuardian = useMutation({
    mutationFn: (linkId: string) => childrenApi.unlinkGuardian(childId, linkId),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const makePrimary = useMutation({
    mutationFn: (linkId: string) =>
      childrenApi.updateGuardianLink(childId, linkId, { is_primary: true }),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  if (childQuery.isPending) {
    return <p className="py-12 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
  }

  if (childQuery.isError || !childQuery.data) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-red-600">
          {childQuery.error instanceof ApiError ? childQuery.error.message : t('Bola topilmadi.')}
        </p>
        <Link to="/children" className="mt-3 inline-block text-sm text-brand-600 hover:underline">
          {t('Roʻyxatga qaytish')}
        </Link>
      </div>
    )
  }

  const child = childQuery.data

  return (
    <div className="space-y-6">
      {/* Guruh va tarif TASDIQ bilan o'zgaradi (PLAN 1.4, Q4). */}
      <ConfirmDialog
        open={pendingGroup !== null}
        title={t('Guruhni oʻzgartirish')}
        body={t('{name}: {from} guruhidan {to} guruhiga', {
          name: child.full_name,
          from: child.current_group?.name ?? t('guruhsiz'),
          to: groupsQuery.data?.items.find((g) => g.id === pendingGroup)?.name ?? t('guruhsiz'),
        })}
        busy={enroll.isPending}
        onCancel={() => setPendingGroup(null)}
        onConfirm={() => {
          if (pendingGroup) enroll.mutate(pendingGroup)
          setPendingGroup(null)
        }}
      />

      <Link
        to="/children"
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('Bolalar')}
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">{child.full_name}</h1>
            <span
              className={cn(
                'rounded-full px-2.5 py-0.5 text-xs font-medium',
                STATUS_TONE[child.enrollment_status] ?? 'bg-tosh-100 text-tosh-600',
              )}
            >
              {STATUS_LABEL[child.enrollment_status] ?? child.enrollment_status}
            </span>
            {child.archived_at && (
              <span className="rounded-full bg-tosh-100 px-2.5 py-0.5 text-xs font-medium text-tosh-600">
                {t('Arxivda')}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {t('{age_years} yosh ·', { age_years: child.age_years })}{' '}
            {child.gender === 'male' ? t('Oʻgʻil bola') : t('Qiz bola')}{' '}
            {t('· tugʻilgan {date_of_birth}', { date_of_birth: formatDate(child.date_of_birth) })}
            {child.enrolled_on && t(' · qabul {date}', { date: formatDate(child.enrolled_on) })}
          </p>
          {/* Holat SABABI ko'rinib turadi: "qachondan buyon va nega"
              degan savol har safar pul bilan birga keladi (Q5). */}
          {child.status_reason && child.status_changed_on && (
            <p className="mt-1 text-xs text-slate-500">
              {t('{date} dan: {reason}', {
                date: formatDate(child.status_changed_on),
                reason: child.status_reason,
              })}
            </p>
          )}
        </div>

        {can('children.update') && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              <Pencil className="h-3.5 w-3.5" />
              {t('Tahrirlash')}
            </button>
            <button
              type="button"
              onClick={() => setChangingStatus(true)}
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              {t('Holat')}
            </button>
            <button
              type="button"
              onClick={() => setArchiving(true)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-500 transition hover:bg-slate-50"
            >
              <Archive className="h-3.5 w-3.5" />
              {child.archived_at ? t('Arxivdan qaytarish') : t('Arxivlash')}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <ChildBalanceCard childId={childId} />
        {/* Guruh */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">{t('Guruh')}</h2>
          {can('children.update') ? (
            <select
              aria-label={t('Guruh')}
              value={child.current_group?.id ?? ''}
              onChange={(e) => e.target.value && setPendingGroup(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            >
              <GroupOptions
                groups={groupsQuery.data?.items ?? []}
                currentId={child.current_group?.id}
              />
            </select>
          ) : (
            <p className="text-sm text-slate-600">{child.current_group?.name ?? '—'}</p>
          )}
        </div>

        {/* Oylik narx — tarif yoki individual summa */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">{t('Oylik narx')}</h2>
          {can('payments.update') ? (
            (() => {
              const current = priceFromChild(child)
              const shown = priceDraft ?? current
              const dirty =
                priceDraft !== null &&
                (priceDraft.tariffId !== current.tariffId ||
                  priceDraft.monthlyFee !== current.monthlyFee)
              return (
                <>
                  <PricePicker
                    idPrefix="child"
                    value={shown}
                    onChange={setPriceDraft}
                    disabled={savePrice.isPending}
                    tariffs={tariffsQuery.data?.items ?? []}
                  />
                  {dirty && (
                    <div className="mt-3 flex gap-2">
                      <button
                        type="button"
                        disabled={savePrice.isPending}
                        onClick={() => {
                          const { payload, error: priceError } = priceToPayload(shown)
                          if (priceError) {
                            setError(priceError)
                            return
                          }
                          savePrice.mutate(payload)
                        }}
                        className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
                      >
                        {savePrice.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
                      </button>
                      <button
                        type="button"
                        onClick={() => setPriceDraft(null)}
                        className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
                      >
                        {t('Bekor qilish')}
                      </button>
                    </div>
                  )}
                  {dirty && (
                    // Q4: narx keyingi hujjatdan — joriy faktura o'zgarmaydi.
                    <p className="mt-2 text-xs text-slate-500">
                      {t(
                        'Yangi tarif KEYINGI hisob-fakturadan kuchga kiradi. Joriy hujjat oʻzgarmaydi.',
                      )}
                    </p>
                  )}
                </>
              )
            })()
          ) : (
            <p className="text-sm text-slate-600">
              {child.monthly_fee !== null
                ? t('Individual narx: {v}', { v: formatUZS(Number(child.monthly_fee)) })
                : (child.tariff_name ?? '—')}
            </p>
          )}
        </div>

        {/* Vasiylar */}
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">{t('Vasiylar')}</h2>
            {can('children.update') && (
              <button
                type="button"
                onClick={() => setShowGuardianForm((v) => !v)}
                className="flex items-center gap-1.5 text-sm font-medium text-brand-600 hover:underline"
              >
                <UserPlus className="h-3.5 w-3.5" />
                {t('Qoʻshish')}
              </button>
            )}
          </div>

          {child.guardians.length === 0 && !showGuardianForm && (
            <p className="text-sm text-slate-400">{t('Vasiy biriktirilmagan.')}</p>
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
                  {/* Asosiy kanal — Telegram (ADR-23): ulanmagan
                      ota-ona hech qanday xabar olmaydi, shuning uchun
                      bu holat bola kartasida ko'rinib turadi. */}
                  <div className="mt-1.5">
                    <TelegramLinkButton
                      guardianId={link.guardian.id}
                      linked={link.guardian.telegram_linked}
                      onChange={invalidate}
                    />
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-500">
                    {RELATIONS.find(([code]) => code === link.relation)?.[1] ?? link.relation}
                  </span>
                  {can('children.update') && !link.is_primary && (
                    <button
                      type="button"
                      title={t('Asosiy qilish')}
                      aria-label={t('Asosiy qilish')}
                      onClick={() => makePrimary.mutate(link.id)}
                      className="rounded p-1 text-slate-300 transition hover:bg-orik-50 hover:text-orik-600"
                    >
                      <Star className="h-3.5 w-3.5" />
                    </button>
                  )}
                  {can('children.update') && (
                    <button
                      type="button"
                      title={t('Bogʻlanishni uzish')}
                      aria-label={t('Bogʻlanishni uzish')}
                      onClick={() => unlinkGuardian.mutate(link.id)}
                      className="rounded p-1 text-slate-300 transition hover:bg-red-50 hover:text-red-600"
                    >
                      <Unlink className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
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
                  placeholder={t('Familiya')}
                  aria-label={t('Familiya')}
                  value={guardianForm.last_name}
                  onChange={(e) => setGuardianForm((p) => ({ ...p, last_name: e.target.value }))}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
                <input
                  placeholder={t('Ism')}
                  aria-label={t('Ism')}
                  value={guardianForm.first_name}
                  onChange={(e) => setGuardianForm((p) => ({ ...p, first_name: e.target.value }))}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <input
                required
                type="tel"
                placeholder="+998 90 123 45 67"
                aria-label="+998 90 123 45 67"
                value={guardianForm.phone}
                onChange={(e) => setGuardianForm((p) => ({ ...p, phone: e.target.value }))}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
              <div className="flex items-center gap-2">
                <select
                  aria-label={t('Kim boʻladi')}
                  value={guardianForm.relation}
                  onChange={(e) => setGuardianForm((p) => ({ ...p, relation: e.target.value }))}
                  className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                >
                  {RELATIONS.map(([code, label]) => (
                    <option key={code} value={code}>
                      {label}
                    </option>
                  ))}
                </select>
                <select
                  aria-label={t('Xabar tili')}
                  value={guardianForm.language}
                  onChange={(e) => setGuardianForm((p) => ({ ...p, language: e.target.value }))}
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                >
                  <option value="">{t('Xabar tili: bogʻcha tili')}</option>
                  <option value="uz">{t('Oʻzbekcha')}</option>
                  <option value="ru">{t('Ruscha')}</option>
                </select>
                <label className="flex items-center gap-1.5 text-sm text-slate-600">
                  <input
                    type="checkbox"
                    checked={guardianForm.is_primary}
                    onChange={(e) =>
                      setGuardianForm((p) => ({ ...p, is_primary: e.target.checked }))
                    }
                  />
                  {t('Asosiy')}
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
                {addGuardian.isPending ? t('Saqlanmoqda…') : t('Vasiyni biriktirish')}
              </button>
              <p className="text-xs text-slate-400">
                {t(
                  'Bu telefon bilan vasiy allaqachon mavjud boʻlsa, yangi yozuv yaratilmaydi — mavjudi biriktiriladi.',
                )}
              </p>
            </form>
          )}
        </div>
      </div>

      {/* Hisob-fakturalar, to'lovlar va tarix — mudiraning savollari
          endi bitta kartada, boshqa ekranga o'tmasdan (PLAN 2.1). */}
      <ChildTabs childId={childId} />

      {editing && (
        <ChildEditDialog child={child} onClose={() => setEditing(false)} onDone={invalidate} />
      )}
      {changingStatus && (
        <ChildStatusDialog
          child={child}
          onClose={() => setChangingStatus(false)}
          onDone={invalidate}
        />
      )}
      <ConfirmDialog
        open={archiving}
        title={child.archived_at ? t('Arxivdan qaytarish') : t('Arxivlash')}
        body={
          child.archived_at
            ? t('Bola yana roʻyxatlarda koʻrinadi.')
            : t('Bola roʻyxatlardan chiqadi, lekin hisob-faktura, toʻlov va davomat joyida qoladi.')
        }
        busy={archive.isPending}
        onCancel={() => setArchiving(false)}
        onConfirm={() => archive.mutate()}
      />
    </div>
  )
}
