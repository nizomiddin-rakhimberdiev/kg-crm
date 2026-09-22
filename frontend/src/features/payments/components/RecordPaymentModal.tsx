/**
 * To'lov qabul qilish oynasi.
 *
 * Qoldiqdan ortiq summa kiritishga ruxsat berilmaydi — backend ham rad
 * etadi (docs/03 §13.5), lekin uni bu yerda ham to'sish kassirni keraksiz
 * xatodan saqlaydi. Ortiqcha pul kelsa, u hisob-fakturasiz avans sifatida
 * kiritiladi.
 */

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Banknote } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { paymentsApi } from '@/features/payments/api'
import { ApiError, type Invoice } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const METHODS: Array<[string, string]> = [
  ['cash', t('Naqd')],
  ['card', t('Karta')],
  ['bank_transfer', t("Bank o'tkazmasi")],
]

const money = (value: string) => new Intl.NumberFormat('uz-UZ').format(Number(value))

export function RecordPaymentModal({
  invoice,
  onClose,
}: {
  invoice: Invoice
  onClose: () => void
}) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()

  const outstanding = Number(invoice.amount_outstanding)
  const [amount, setAmount] = useState(invoice.amount_outstanding)
  const [method, setMethod] = useState('cash')
  const [reference, setReference] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Kalit MODAL OCHILGANDA bir marta yaratiladi va qayta urinishda
  // o'zgarmaydi — aynan shu narsa uni ishlatadigan qiladi. Har bosishda
  // yangi kalit yaratilsa, server ikkita mustaqil to'lov ko'rardi va
  // himoyaning ma'nosi qolmasdi (P1-003).
  //
  // `useState` ning boshlang'ich funksiyasi: `crypto.randomUUID()` har
  // render'da emas, BIR marta chaqiriladi.
  const [idempotencyKey] = useState(() => crypto.randomUUID())

  const record = useMutation({
    mutationFn: () =>
      paymentsApi.record(
        {
          child_id: invoice.child,
          invoice_id: invoice.id,
          amount,
          method,
          reference,
        },
        idempotencyKey,
      ),
    onSuccess: () => {
      // Hisob-faktura, to'lov, qarzdorlar va balans — hammasi o'zgardi.
      for (const key of ['invoices', 'payments', 'debtors', 'children']) {
        void queryClient.invalidateQueries({ queryKey: ['org', organizationId, key] })
      }
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const tooMuch = Number(amount) > outstanding

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <div className="p-6">
        <div className="mb-4 pr-10">
          <h2 className="text-lg font-bold text-slate-900">{t("To'lov qabul qilish")}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {invoice.child_name} · {invoice.number}
          </p>
        </div>

        <div className="mb-4 rounded-lg bg-slate-50 px-3 py-2 text-sm">
          <span className="text-slate-500">{t("To'lanishi kerak:")} </span>
          <span className="font-semibold text-slate-900">
            {t("{money} so'm", { money: money(invoice.amount_outstanding) })}
          </span>
        </div>

        {error && (
          <div role="alert" className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <form
          onSubmit={(event) => {
            event.preventDefault()
            record.mutate()
          }}
          className="space-y-3"
        >
          <div>
            <label htmlFor="amount" className="mb-1 block text-xs font-medium text-slate-600">
              {t('Summa')}
            </label>
            <input
              id="amount"
              type="number"
              required
              min="0.01"
              step="0.01"
              max={outstanding}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className={cn(
                'w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2',
                tooMuch
                  ? 'border-red-300 focus:ring-red-100'
                  : 'border-slate-200 focus:border-brand-500 focus:ring-brand-100',
              )}
            />
            {tooMuch && (
              <p className="mt-1 text-xs text-red-600">
                {t('Qoldiqdan ortiq. Ortiqcha summani alohida avans sifatida kiriting.')}
              </p>
            )}
          </div>

          <div>
            <span className="mb-1 block text-xs font-medium text-slate-600">
              {t("To'lov usuli")}
            </span>
            <div className="flex gap-2">
              {METHODS.map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setMethod(value)}
                  className={cn(
                    'flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition',
                    method === value
                      ? 'border-brand-300 bg-brand-50 text-brand-700'
                      : 'border-slate-200 text-slate-600 hover:bg-slate-50',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {method !== 'cash' && (
            <div>
              <label htmlFor="reference" className="mb-1 block text-xs font-medium text-slate-600">
                {t("Ma'lumotnoma (ixtiyoriy)")}
              </label>
              <input
                id="reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder={t('Tranzaksiya raqami')}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={record.isPending || tooMuch}
            className={cn(
              'flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-white transition',
              record.isPending || tooMuch ? 'bg-slate-300' : 'bg-emerald-600 hover:bg-emerald-700',
            )}
          >
            <Banknote className="h-4 w-4" />
            {record.isPending
              ? t('Saqlanmoqda…')
              : t("{money} so'm qabul qilish", { money: money(amount || '0') })}
          </button>
        </form>
      </div>
    </Modal>
  )
}
