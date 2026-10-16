/**
 * Fiskal chek (Bosqich 13.8, brif §9).
 *
 * Naqd va karta (terminal) toʻlovida chekni bogʻcha beradi — onlayn-NKM
 * yoki virtual kassa. Bu yerda uning raqami yoki QR havolasi yoziladi.
 * Click/Payme chekini toʻlov tizimi beradi, bogʻcha hech narsa yozmaydi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { paymentsApi } from '@/features/payments/api'
import { ApiError, type Payment } from '@/lib/api/types'
import { formatDateTime, money } from '@/lib/format'
import { t } from '@/lib/i18n'

const field =
  'mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'

const KIND: Record<string, string> = {
  advance: t('Avans'),
  sale: t('Sotuv'),
  credit: t('Kredit'),
}

export function FiscalModal({ payment, onClose }: { payment: Payment; onClose: () => void }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const key = ['org', organizationId, 'payments', 'detail', payment.id]
  const detail = useQuery({ queryKey: key, queryFn: () => paymentsApi.detail(payment.id) })
  const [number, setNumber] = useState('')
  const [qr, setQr] = useState('')
  const [error, setError] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: () => paymentsApi.fiscal(payment.id, { number: number.trim(), qr: qr.trim() }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'payments'] })
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'reports'] })
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })
  const fiscal = detail.data?.fiscal

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <form
        className="space-y-3 p-6"
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        <h2 className="pr-10 text-lg font-bold text-slate-900">{t('Fiskal chek')}</h2>
        <p className="text-sm text-slate-600">
          {payment.child_name} · {money(payment.amount)} · {formatDateTime(payment.paid_at)}
        </p>
        {fiscal && (
          <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
            {fiscal.status === 'issued'
              ? t('Chek yozilgan: {number}', { number: fiscal.number || fiscal.qr || '' })
              : t('Chek turi: {kind}', { kind: KIND[fiscal.kind] ?? fiscal.kind })}
          </p>
        )}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <label className="block text-sm font-medium text-slate-700">
          {t('Chek raqami')}
          <input value={number} onChange={(e) => setNumber(e.target.value)} className={field} />
        </label>
        <label className="block text-sm font-medium text-slate-700">
          {t('QR havolasi')}
          <input value={qr} onChange={(e) => setQr(e.target.value)} className={field} />
        </label>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="submit"
            disabled={save.isPending || (!number.trim() && !qr.trim())}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {t('Saqlash')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
