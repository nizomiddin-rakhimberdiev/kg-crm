/**
 * «Kassadagi qoldiqni toʻgʻrilash» (ADR-29).
 *
 * Nega kerak. Bogʻcha tizimga yil oʻrtasida keladi: seyfida va bank
 * hisobida allaqachon pul bor, lekin tizimda yoʻq — chunki tushumlar
 * faqat shu kundan boshlab yoziladi. Natijada birinchi chiqimdayoq
 * qoldiq manfiyga tushadi va boshqaruv panelida «−6 752 500 soʻm»
 * koʻrinadi. Bu raqam bogʻchaning holatini emas, YETISHMAYOTGAN
 * YOZUVni bildiradi.
 *
 * Toʻgʻrilash — oddiy kassa harakati: jurnal append-only qoladi va
 * «qoldiq qayerdan kelgan?» degan savolga SABAB bilan javob beradi.
 * Shuning uchun sabab majburiy.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Modal } from '@/components/ui/Modal'
import { DateInput } from '@/components/ui/DateInput'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { cashApi } from '@/features/cash/api'
import { ApiError } from '@/lib/api/types'
import { money, today } from '@/lib/format'
import { t } from '@/lib/i18n'

export function CashAdjustModal({ onClose }: { onClose: () => void }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const [form, setForm] = useState({
    account: '',
    amount: '',
    reason: '',
    opening: true,
    occurred_on: today(),
  })
  const [error, setError] = useState<string | null>(null)

  const accounts = useQuery({
    queryKey: ['org', organizationId, 'cash-accounts'],
    queryFn: () => cashApi.accounts(),
  })
  const balances = useQuery({
    queryKey: ['org', organizationId, 'cash-balances'],
    queryFn: () => cashApi.balances(),
  })

  const current = balances.data?.find((row) => row.id === form.account)

  const save = useMutation({
    mutationFn: () =>
      cashApi.adjust(form.account, {
        amount: form.amount,
        reason: form.reason,
        opening: form.opening,
        occurred_on: form.occurred_on,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId] })
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <form
        className="p-5 sm:p-6"
        onSubmit={(event) => {
          event.preventDefault()
          setError(null)
          save.mutate()
        }}
      >
        <div className="pr-8">
          <h2 className="text-base font-semibold text-slate-900">{t('Qoldiqni toʻgʻrilash')}</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {t(
              'Tizimga oʻtishdan oldin qoʻlda turgan pul yoki sanoqdagi farq. Yozuv oʻchirilmaydi — jurnalda sababi bilan qoladi.',
            )}
          </p>
        </div>

        {error && (
          <div role="alert" className="mt-3 rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-900">
            {error}
          </div>
        )}

        <div className="mt-4 grid gap-3">
          <div>
            <label htmlFor="adj-account" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Qaysi hisob')} <span className="text-red-500">*</span>
            </label>
            <select
              id="adj-account"
              required
              value={form.account}
              onChange={(event) => setForm((prev) => ({ ...prev, account: event.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            >
              <option value="">{t('Tanlang…')}</option>
              {accounts.data?.items.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
            {current && (
              <p className="num mt-1 text-xs text-slate-500">
                {t('Hozirgi qoldiq: {money} soʻm', { money: money(current.balance) })}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="adj-amount" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Summa (soʻm)')} <span className="text-red-500">*</span>
            </label>
            <input
              id="adj-amount"
              required
              type="number"
              step="1000"
              inputMode="numeric"
              value={form.amount}
              onChange={(event) => setForm((prev) => ({ ...prev, amount: event.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
            <p className="mt-1 text-xs text-slate-500">
              {t('Manfiy summa — qoldiqni kamaytirish (sanoqda kam chiqdi).')}
            </p>
          </div>

          <div>
            <label htmlFor="adj-date" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Sana')}
            </label>
            <DateInput
              id="adj-date"
              value={form.occurred_on}
              onChange={(iso) => setForm((prev) => ({ ...prev, occurred_on: iso }))}
            />
          </div>

          <div>
            <label htmlFor="adj-reason" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Sabab')} <span className="text-red-500">*</span>
            </label>
            <input
              id="adj-reason"
              required
              maxLength={255}
              value={form.reason}
              onChange={(event) => setForm((prev) => ({ ...prev, reason: event.target.value }))}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
          </div>

          <label className="flex items-start gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.opening}
              onChange={(event) => setForm((prev) => ({ ...prev, opening: event.target.checked }))}
              className="mt-0.5 h-5 w-5 shrink-0 accent-nihol-600"
            />
            <span>{t('Bu — boshlangʻich qoldiq (tizimga oʻtishdan oldingi pul)')}</span>
          </label>
        </div>

        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="submit"
            disabled={save.isPending}
            className="rounded-lg bg-nihol-600 px-4 py-2 text-sm font-semibold text-white hover:bg-nihol-700 disabled:opacity-60"
          >
            {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
