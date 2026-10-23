/**
 * Imtiyoz va oila — bola kartasida (Bosqich 12.2).
 *
 * Toifa FAQAT shu yerda belgilanadi — rang yoki erkin matn bilan emas (brif
 * §1). Har bir imtiyozning turi, sababi, muddati va kim kiritgani bor.
 * Imtiyoz tahrirlanmaydi va oʻchirilmaydi: oʻzgarish — eskisini tugatish va
 * yangisini kiritish, shunda tarix oʻzi saqlanadi.
 *
 * Aka-uka chegirmasi bu yerda KIRITILMAYDI: u umumiy vasiy orqali oʻzi
 * qoʻllanadi, panel faqat oilani koʻrsatadi — "nega chegirma oladi?"
 * degan savolga javob familiyada emas, vasiyda.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BadgePercent, Users } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { DateInput } from '@/components/ui/DateInput'
import { benefitsApi, type Benefit, type BenefitKind } from '@/features/payments/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { formatDate, today } from '@/lib/format'
import { useCan } from '@/lib/rbac/useCan'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'

const BENEFIT_LABEL: Record<BenefitKind, string> = {
  sibling: t('Aka-uka'),
  staff_child: t('Xodim farzandi'),
  low_income: t('Kam taʼminlangan'),
  full: t('Toʻliq imtiyoz'),
  custom: t('Boshqa'),
}

const field =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'

function isCurrent(benefit: Benefit, on: string): boolean {
  return benefit.valid_from <= on && (!benefit.valid_to || benefit.valid_to >= on)
}

export function BenefitsPanel({ childId }: { childId: string }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const key = ['org', organizationId, 'children', childId, 'benefits']

  const benefits = useQuery({
    queryKey: key,
    queryFn: () => benefitsApi.list(childId),
    enabled: can('payments.read'),
  })
  const family = useQuery({
    queryKey: [...key, 'family'],
    queryFn: () => benefitsApi.family(childId),
  })

  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    kind: 'staff_child' as Exclude<BenefitKind, 'sibling'>,
    reason: '',
    valid_from: today(),
    discount_type: 'percent' as 'percent' | 'fixed',
    value: '',
  })
  const [ending, setEnding] = useState<{ id: string; date: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: key })
    invalidateMoney(queryClient, organizationId)
  }
  const fail = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.'))

  const create = useMutation({
    mutationFn: () =>
      benefitsApi.create({
        child_id: childId,
        kind: form.kind,
        reason: form.reason,
        valid_from: form.valid_from,
        ...(form.kind === 'custom' ? { discount_type: form.discount_type, value: form.value } : {}),
      }),
    onSuccess: () => {
      setOpen(false)
      setForm((p) => ({ ...p, reason: '', value: '' }))
      setError(null)
      refresh()
    },
    onError: fail,
  })
  const end = useMutation({
    mutationFn: (draft: { id: string; date: string }) => benefitsApi.end(draft.id, draft.date),
    onSuccess: () => {
      setEnding(null)
      setError(null)
      refresh()
    },
    onError: fail,
  })

  const rows = benefits.data?.items ?? []
  const now = today()
  const current = rows.find((row) => isCurrent(row, now))
  const siblings = (family.data ?? []).filter((member) => !member.is_self)

  if (!can('payments.read') && siblings.length === 0) return null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <BadgePercent className="h-4 w-4 text-slate-500" />
          {t('Imtiyoz')}
        </h2>
        {can('payments.create') && !open && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-lg px-2.5 py-1.5 text-sm font-medium text-brand-700 hover:bg-brand-50"
          >
            {t('Imtiyoz qoʻshish')}
          </button>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {/* Hozirgi holat — bir qarashda */}
      <div className="mt-3 rounded-xl bg-slate-50 px-3 py-2.5 text-sm">
        {current ? (
          <p>
            <span className="font-semibold text-slate-900">
              {BENEFIT_LABEL[current.kind]} · {current.terms}
            </span>
            <span className="text-slate-600"> — {current.reason}</span>
          </p>
        ) : siblings.length > 0 ? (
          <p className="text-slate-700">
            <span className="font-semibold text-slate-900">{t('Aka-uka chegirmasi')}</span>{' '}
            {t('— oilada yana {n} bola, chegirma avtomatik.', { n: siblings.length })}
          </p>
        ) : (
          <p className="text-slate-600">{t('Imtiyoz yoʻq — toʻliq narx.')}</p>
        )}
        {siblings.length > 0 && (
          <p className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-slate-600">
            <Users className="h-3.5 w-3.5" />
            {t('Oila (umumiy vasiy):')} {siblings.map((member) => member.full_name).join(', ')}
          </p>
        )}
      </div>

      {open && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            create.mutate()
          }}
          className="mt-3 grid gap-2 sm:grid-cols-2"
        >
          <div>
            <label htmlFor="benefit-kind" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Turi')}
            </label>
            <Select
              id="benefit-kind"
              value={form.kind}
              onChange={(e) =>
                setForm((p) => ({
                  ...p,
                  kind: e.target.value as Exclude<BenefitKind, 'sibling'>,
                }))
              }
              className="mt-1"
            >
              {(['staff_child', 'low_income', 'full', 'custom'] as const).map((kind) => (
                <option key={kind} value={kind}>
                  {BENEFIT_LABEL[kind]}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <label htmlFor="benefit-from" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Boshlanishi')}
            </label>
            <DateInput
              id="benefit-from"
              required
              value={form.valid_from}
              onChange={(iso) => setForm((p) => ({ ...p, valid_from: iso }))}
            />
          </div>
          {form.kind === 'custom' && (
            <>
              <div>
                <label
                  htmlFor="benefit-type"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {t('Chegirma turi')}
                </label>
                <Select
                  id="benefit-type"
                  value={form.discount_type}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, discount_type: e.target.value as 'percent' | 'fixed' }))
                  }
                  className="mt-1"
                >
                  <option value="percent">{t('Foiz')}</option>
                  <option value="fixed">{t('Belgilangan summa')}</option>
                </Select>
              </div>
              <div>
                <label
                  htmlFor="benefit-value"
                  className="mb-1 block text-xs font-medium text-slate-600"
                >
                  {form.discount_type === 'percent' ? t('Foiz') : t('Summa')}
                </label>
                <input
                  id="benefit-value"
                  required
                  inputMode="numeric"
                  value={form.value}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, value: e.target.value.replace(/[^\d.]/g, '') }))
                  }
                  className={field}
                />
              </div>
            </>
          )}
          <div className="sm:col-span-2">
            <label
              htmlFor="benefit-reason"
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {t('Sabab (majburiy)')}
            </label>
            <input
              id="benefit-reason"
              required
              maxLength={255}
              value={form.reason}
              onChange={(e) => setForm((p) => ({ ...p, reason: e.target.value }))}
              className={field}
            />
          </div>
          <div className="flex justify-end gap-2 sm:col-span-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={create.isPending || !form.reason.trim()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {t('Saqlash')}
            </button>
          </div>
        </form>
      )}

      {/* Tarix — tugaganlari ham qoladi */}
      {rows.length > 0 && (
        <ul className="mt-3 divide-y divide-slate-100 text-sm">
          {rows.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span>
                <span className="font-medium text-slate-900">
                  {BENEFIT_LABEL[row.kind]} · {row.terms}
                </span>
                <span className="text-slate-600"> — {row.reason}</span>
                <span className="block text-xs text-slate-500">
                  {formatDate(row.valid_from)} —{' '}
                  {row.valid_to ? formatDate(row.valid_to) : t('hozirgacha')}
                  {row.created_by_name && ` · ${row.created_by_name}`}
                </span>
              </span>
              {can('payments.update') && !row.valid_to && (
                <span className="flex items-center gap-2">
                  {ending?.id === row.id ? (
                    <>
                      <DateInput
                        id={`end-${row.id}`}
                        aria-label={t('Tugash sanasi')}
                        value={ending.date}
                        onChange={(iso) => setEnding({ id: row.id, date: iso })}
                      />
                      <button
                        type="button"
                        disabled={end.isPending}
                        onClick={() => end.mutate(ending)}
                        className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white"
                      >
                        {t('Tugatish')}
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setEnding({ id: row.id, date: now })}
                      className="rounded-lg px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                    >
                      {t('Tugatish')}
                    </button>
                  )}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
