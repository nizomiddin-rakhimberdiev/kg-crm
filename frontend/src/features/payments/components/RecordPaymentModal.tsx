/**
 * To'lov qabul qilish oynasi — IKKI rejimda, BIR NECHTA usulda.
 *
 * `invoice` berilsa: aniq hisob-fakturaga to'lov.
 * `invoice` berilmasa: fakturasiz to'lov (avans) — pul bolaning
 * balansiga tushadi va keyingi hisob-fakturani o'zi yopadi.
 *
 * Har ikki rejimda ham bir nechta usul qo'shsa bo'ladi (docs/03 §13.5a):
 * ota-ona 1 400 000 ni naqd, 100 000 ni terminalda berishi mumkin va bu
 * BITTA harakat. Ortiqcha summa endi rad etilmaydi — u avansga tushadi
 * va oynada shu haqda aytiladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Banknote, Plus, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { childrenApi } from '@/features/children/api'
import { paymentsApi } from '@/features/payments/api'
import { PAYMENT_METHODS, paymentMethodLabel } from '@/features/payments/methods'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type Invoice } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { money } from '@/lib/format'
import { t } from '@/lib/i18n'

interface Line {
  key: string
  method: string
  amount: string
  reference: string
}

const newLine = (method: string, amount = ''): Line => ({
  key: crypto.randomUUID(),
  method,
  amount,
  reference: '',
})

export function RecordPaymentModal({
  invoice,
  onClose,
}: {
  /** Berilmasa — fakturasiz to'lov (avans). */
  invoice?: Invoice
  onClose: () => void
}) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()

  // Fakturasiz rejimda bolani tanlash kerak. Ro'yxat bir marta yuklanadi:
  // bog'chada bolalar soni yuzlab emas, qidiruvli murakkab tanlagich
  // ortiqcha bo'lardi.
  const childrenQuery = useQuery({
    queryKey: queryKeys.children(organizationId, { page_size: 500 }),
    queryFn: () => childrenApi.list({ page_size: 500 }),
    enabled: !invoice,
  })
  const [childId, setChildId] = useState('')

  const outstanding = invoice ? Number(invoice.amount_outstanding) : 0
  const [lines, setLines] = useState<Line[]>(() => [
    newLine('cash', invoice?.amount_outstanding ?? ''),
  ])
  const [error, setError] = useState<string | null>(null)

  // Kalit MODAL OCHILGANDA bir marta yaratiladi va qayta urinishda
  // o'zgarmaydi — aynan shu narsa uni ishlatadigan qiladi. Har bosishda
  // yangi kalit yaratilsa, server ikkita mustaqil to'lov ko'rardi va
  // himoyaning ma'nosi qolmasdi (P1-003).
  const [idempotencyKey] = useState(() => crypto.randomUUID())

  const total = lines.reduce((sum, line) => sum + (Number(line.amount) || 0), 0)
  const advance = invoice ? Math.max(0, total - outstanding) : total
  const settled = invoice ? Math.min(total, outstanding) : 0

  const update = (key: string, patch: Partial<Line>) =>
    setLines((prev) => prev.map((line) => (line.key === key ? { ...line, ...patch } : line)))

  const addLine = () => {
    // Qolgan summani oldindan qo'yamiz — kassir odatda aynan shuni
    // kiritadi, va allaqachon ishlatilgan usul takrorlanmasin.
    const used = new Set(lines.map((line) => line.method))
    const next = PAYMENT_METHODS.find((method) => !used.has(method)) ?? 'cash'
    const left = invoice ? Math.max(0, outstanding - total) : 0
    setLines((prev) => [...prev, newLine(next, left > 0 ? String(left) : '')])
  }

  const record = useMutation({
    mutationFn: () =>
      paymentsApi.recordBatch(
        {
          child_id: invoice ? invoice.child : childId,
          ...(invoice ? { invoice_id: invoice.id } : {}),
          lines: lines
            .filter((line) => Number(line.amount) > 0)
            .map((line) => ({
              method: line.method,
              amount: line.amount,
              ...(line.reference ? { reference: line.reference } : {}),
            })),
        },
        idempotencyKey,
      ),
    onSuccess: () => {
      // Hisob-faktura, to'lov, qarzdorlar va balans — hammasi o'zgardi.
      for (const key of ['invoices', 'payments', 'debtors', 'children', 'cash']) {
        void queryClient.invalidateQueries({ queryKey: ['org', organizationId, key] })
      }
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const ready = total > 0 && (invoice ? true : Boolean(childId))

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <div className="p-6">
        <div className="mb-4 pr-10">
          <h2 className="text-lg font-bold text-slate-900">{t("To'lov qabul qilish")}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {invoice
              ? `${invoice.child_name} · ${invoice.number}`
              : t('Hisob-fakturasiz — pul bolaning balansiga tushadi')}
          </p>
        </div>

        {invoice && (
          <div className="mb-4 rounded-lg bg-slate-50 px-3 py-2 text-sm">
            <span className="text-slate-500">{t("To'lanishi kerak:")} </span>
            <span className="font-semibold tabular-nums text-slate-900">
              {t("{money} so'm", { money: money(outstanding) })}
            </span>
          </div>
        )}

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
          {!invoice && (
            <div>
              <label htmlFor="pay-child" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Bola')}
              </label>
              <select
                id="pay-child"
                required
                value={childId}
                onChange={(e) => setChildId(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              >
                <option value="">{t('Tanlang…')}</option>
                {childrenQuery.data?.items.map((child) => (
                  <option key={child.id} value={child.id}>
                    {child.full_name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <span className="mb-1 block text-xs font-medium text-slate-600">
              {t('Usul va summa')}
            </span>
            <div className="space-y-2">
              {lines.map((line, index) => (
                <div key={line.key}>
                  <div className="flex gap-2">
                    <select
                      aria-label={t("To'lov usuli")}
                      value={line.method}
                      onChange={(e) => update(line.key, { method: e.target.value })}
                      className="w-[9.5rem] shrink-0 rounded-lg border border-slate-200 px-2 py-2 text-sm outline-none focus:border-brand-500"
                    >
                      {PAYMENT_METHODS.map((method) => (
                        <option key={method} value={method}>
                          {paymentMethodLabel(method)}
                        </option>
                      ))}
                    </select>
                    <input
                      aria-label={t('Summa')}
                      type="number"
                      min="0"
                      step="0.01"
                      required={index === 0}
                      value={line.amount}
                      onChange={(e) => update(line.key, { amount: e.target.value })}
                      placeholder="0"
                      className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2 text-right text-sm tabular-nums outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                    />
                    {lines.length > 1 && (
                      <button
                        type="button"
                        onClick={() => setLines((prev) => prev.filter((l) => l.key !== line.key))}
                        title={t("Qatorni o'chirish")}
                        className="shrink-0 rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                  {line.method !== 'cash' && (
                    <input
                      aria-label={t("Ma'lumotnoma (ixtiyoriy)")}
                      value={line.reference}
                      onChange={(e) => update(line.key, { reference: e.target.value })}
                      placeholder={t('Tranzaksiya raqami')}
                      className="mt-1.5 w-full rounded-lg border border-slate-200 px-3 py-1.5 text-xs outline-none focus:border-brand-500"
                    />
                  )}
                </div>
              ))}
            </div>

            {lines.length < PAYMENT_METHODS.length && (
              <button
                type="button"
                onClick={addLine}
                className="mt-2 flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-medium text-brand-700 transition hover:bg-brand-50"
              >
                <Plus className="h-4 w-4" /> {t('Yana usul qo‘shish')}
              </button>
            )}
          </div>

          {/* Taqsimot — kassir tugmani bosishdan OLDIN ko'radi.
              Ortiqcha summa xato emas: u avansga tushadi va keyingi
              hisob-fakturani yopadi (docs/03 §13.5a). */}
          {lines.length > 1 || advance > 0 ? (
            <dl className="space-y-1 rounded-lg bg-slate-50 px-3 py-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-500">{t('Jami')}</dt>
                <dd className="font-semibold tabular-nums text-slate-900">
                  {t("{money} so'm", { money: money(total) })}
                </dd>
              </div>
              {invoice && settled > 0 && (
                <div className="flex justify-between">
                  <dt className="text-slate-500">{t('Hisob-fakturaga')}</dt>
                  <dd className="tabular-nums text-slate-700">
                    {t("{money} so'm", { money: money(settled) })}
                  </dd>
                </div>
              )}
              {advance > 0 && (
                <div className="flex justify-between">
                  <dt className="text-amber-700">{t('Avansga (balansga)')}</dt>
                  <dd className="font-medium tabular-nums text-amber-700">
                    {t("{money} so'm", { money: money(advance) })}
                  </dd>
                </div>
              )}
            </dl>
          ) : null}

          <button
            type="submit"
            disabled={record.isPending || !ready}
            className={cn(
              'flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-white transition',
              record.isPending || !ready ? 'bg-slate-300' : 'bg-emerald-600 hover:bg-emerald-700',
            )}
          >
            <Banknote className="h-4 w-4" />
            {record.isPending
              ? t('Saqlanmoqda…')
              : t("{money} so'm qabul qilish", { money: money(total) })}
          </button>
        </form>
      </div>
    </Modal>
  )
}
