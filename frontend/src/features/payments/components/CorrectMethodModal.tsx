/**
 * Toʻlov usulini oʻsha kuni tuzatish (mijoz soʻrovi, 2026-10-28).
 *
 * Kassir shoshib "naqd" ni bosadi, pul esa terminaldan tushadi.
 * Ilgari yagona yoʻl butun toʻlovni bekor qilib qaytadan yozish edi —
 * ota-onadagi kvitansiya raqami oʻzgarardi va jurnalda bitta pul ikki
 * marta koʻrinardi.
 *
 * SUMMA bu yerda yoʻq va bu ataylab: notoʻgʻri summa — boshqa hodisa,
 * u qaytarish bilan tuzatiladi.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { paymentsApi } from '@/features/payments/api'
import { ALL_PAYMENT_METHODS, paymentMethodLabel } from '@/features/payments/methods'
import { formatUZS } from '@/lib/utils'
import { ApiError, type Payment } from '@/lib/api/types'
import { t } from '@/lib/i18n'

export function CorrectMethodModal({
  payment,
  onClose,
  onDone,
}: {
  payment: Payment
  onClose: () => void
  onDone: () => void
}) {
  const [method, setMethod] = useState<string>(payment.method)
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () => paymentsApi.correctMethod(payment.id, { method, reason }),
    onSuccess: () => {
      onDone()
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  // Oylikdan ushlash — boshqa mexanizm (pul qopga umuman tushmaydi),
  // shuning uchun u bu roʻyxatda yoʻq.
  const choices = ALL_PAYMENT_METHODS.filter((value) => value !== 'payroll')

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <form
        className="p-6"
        onSubmit={(event) => {
          event.preventDefault()
          save.mutate()
        }}
      >
        <h2 className="pr-10 text-lg font-bold text-slate-900">{t('Toʻlov usulini tuzatish')}</h2>
        <p className="mt-0.5 text-sm text-slate-500">
          {payment.child_name} · {formatUZS(Number(payment.amount))}
        </p>

        {error && (
          <div role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="mt-4 space-y-3">
          <div>
            <label htmlFor="cm-method" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Toʻlov usuli')} <span className="text-red-500">*</span>
            </label>
            <Select
              id="cm-method"
              value={method}
              onChange={(event) => setMethod(event.target.value)}
            >
              {choices.map((value) => (
                <option key={value} value={value}>
                  {paymentMethodLabel(value)}
                </option>
              ))}
            </Select>
            <p className="mt-1 text-xs text-slate-500">
              {t('Pul boshqa kassaga koʻchadi, komissiya esa qaytadan hisoblanadi.')}
            </p>
          </div>

          <div>
            <label htmlFor="cm-reason" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Sabab')} <span className="text-red-500">*</span>
            </label>
            <input
              id="cm-reason"
              required
              maxLength={255}
              placeholder={t('Masalan: pul terminaldan tushgan')}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="h-10 w-full rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
        </div>

        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="submit"
            disabled={save.isPending || method === payment.method}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
          </button>
        </div>
      </form>
    </Modal>
  )
}
