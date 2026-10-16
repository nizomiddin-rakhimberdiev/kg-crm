/**
 * Avansni ota-onaga qaytarish (Bosqich 13.2b).
 *
 * Toʻlovni bekor qilishdan farqi: bekor qilish — "toʻlov boʻlmagan"
 * (xato kiritilgan); qaytarish — pul haqiqatan kelgan va uning
 * ishlatilmagan qismi oilaga qaytdi. Faktura yopgan pul qaytarilmaydi —
 * server buni summasi bilan aytadi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { cashApi } from '@/features/cash/api'
import { paymentsApi } from '@/features/payments/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError, type Payment } from '@/lib/api/types'
import { money } from '@/lib/format'
import { t } from '@/lib/i18n'

const field =
  'mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'

export function RefundModal({ payment, onClose }: { payment: Payment; onClose: () => void }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const accounts = useQuery({
    queryKey: ['org', organizationId, 'cash', 'accounts'],
    queryFn: cashApi.accounts,
  })
  const pots = (accounts.data?.items ?? []).filter(
    (account) => account.is_active && (account.kind === 'cash' || account.kind === 'bank'),
  )
  const [amount, setAmount] = useState('')
  const [potId, setPotId] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const pot = potId || pots.find((row) => row.kind === 'cash')?.id || ''

  const refund = useMutation({
    mutationFn: () =>
      paymentsApi.refund(payment.id, { amount, cash_account_id: pot, reason: reason.trim() }),
    onSuccess: () => {
      invalidateMoney(queryClient, organizationId)
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <form
        className="p-5"
        onSubmit={(event) => {
          event.preventDefault()
          refund.mutate()
        }}
      >
        <h2 className="text-base font-semibold text-slate-900">{t('Ota-onaga pul qaytarish')}</h2>
        <p className="mt-1 text-sm text-slate-500">
          {payment.child_name} · {money(payment.amount)}
        </p>
        <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {t('Faqat fakturani yopmagan (avans) qismi qaytariladi. Toʻlovning oʻzi saqlanadi.')}
        </p>
        {error && (
          <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <label htmlFor="refund-amount" className="mt-4 block text-xs font-medium text-slate-600">
          {t('Summa')}
        </label>
        <input
          id="refund-amount"
          required
          inputMode="numeric"
          value={amount ? money(Number(amount)) : ''}
          onChange={(event) => setAmount(event.target.value.replace(/\D/g, ''))}
          className={field}
        />
        <label htmlFor="refund-pot" className="mt-3 block text-xs font-medium text-slate-600">
          {t('Qaysi puldan')}
        </label>
        <select
          id="refund-pot"
          value={pot}
          onChange={(event) => setPotId(event.target.value)}
          className={field}
        >
          {pots.map((row) => (
            <option key={row.id} value={row.id}>
              {row.name}
            </option>
          ))}
        </select>
        <label htmlFor="refund-reason" className="mt-3 block text-xs font-medium text-slate-600">
          {t('Sabab (majburiy)')}
        </label>
        <input
          id="refund-reason"
          required
          maxLength={255}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          className={field}
        />
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="submit"
            disabled={refund.isPending || !amount || !reason.trim() || !pot}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {t('Qaytarish')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
