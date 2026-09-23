/**
 * Hisob-fakturalar va tariflar (docs/04 §9).
 *
 * Hisob-faktura bu yerda TAHRIRLANMAYDI — u ledger yozuvini yaratgan
 * hujjat (D3). Xato bo'lsa bekor qilinadi (qarshi yozuv bilan) va
 * yangisi chiqariladi.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Ban, Banknote, FileText, Plus, Trash2, Wallet } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { invoicesApi, paymentsApi, tariffsApi } from '@/features/payments/api'
import { RecordPaymentModal } from '@/features/payments/components/RecordPaymentModal'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError, type BillingRunResult, type Invoice, type Payment } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate } from '@/lib/utils'
import { EmptyRow } from '@/components/ui/EmptyState'
import { Modal } from '@/components/ui/Modal'
import { t } from '@/lib/i18n'

const STATUS_STYLES: Record<string, string> = {
  issued: 'bg-sky-50 text-sky-700',
  partially_paid: 'bg-amber-50 text-amber-700',
  paid: 'bg-emerald-50 text-emerald-700',
  overdue: 'bg-red-50 text-red-700',
  cancelled: 'bg-slate-100 text-slate-400 line-through',
  draft: 'bg-slate-100 text-slate-500',
}

const STATUS_LABELS: Record<string, string> = {
  issued: t('Chiqarilgan'),
  partially_paid: t("Qisman to'langan"),
  paid: t("To'langan"),
  overdue: t("Muddati o'tgan"),
  cancelled: t('Bekor qilingan'),
  draft: t('Qoralama'),
}

const money = (value: string) => new Intl.NumberFormat('uz-UZ').format(Number(value)) + t(" so'm")

const METHOD_LABELS: Record<string, string> = {
  cash: t('Naqd'),
  card: t('Karta'),
  bank_transfer: t("Bank o'tkazmasi"),
  online: t('Onlayn'),
}

export default function PaymentsPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const now = new Date()
  const [tab, setTab] = useState<'invoices' | 'payments' | 'tariffs'>('invoices')
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [tariffForm, setTariffForm] = useState({ name: '', amount: '' })
  const [runResult, setRunResult] = useState<BillingRunResult | null>(null)
  const [payingInvoice, setPayingInvoice] = useState<Invoice | null>(null)
  // Fakturasiz to'lov oynasi (avans): `invoice` berilmaydi.
  const [advanceOpen, setAdvanceOpen] = useState(false)
  // Qaytarish sababi so'raladigan to'lov.
  const [reversing, setReversing] = useState<Payment | null>(null)
  const [reverseReason, setReverseReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const invoicesQuery = useQuery({
    queryKey: queryKeys.invoices(organizationId, { year, month }),
    queryFn: () => invoicesApi.list({ period_year: year, period_month: month }),
  })

  const tariffsQuery = useQuery({
    queryKey: queryKeys.tariffs(organizationId),
    queryFn: tariffsApi.list,
  })

  // To'lovlar ro'yxati — kassirning kunlik jurnali. Ilgari UI'da umuman
  // yo'q edi: qabul qilingan to'lovni faqat hisob-faktura qatoridan
  // ko'rish mumkin edi, fakturasiz kelgan pul esa hech qayerda
  // ko'rinmasdi.
  const paymentsQuery = useQuery({
    queryKey: queryKeys.payments(organizationId, { page_size: 100 }),
    queryFn: () => paymentsApi.list({ page_size: 100 }),
    enabled: tab === 'payments',
  })

  const reverseMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => paymentsApi.reverse(id, reason),
    onSuccess: () => {
      setReversing(null)
      setReverseReason('')
      setError(null)
      for (const key of ['invoices', 'payments', 'debtors', 'children']) {
        void queryClient.invalidateQueries({ queryKey: ['org', organizationId, key] })
      }
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'invoices'] })
    void queryClient.invalidateQueries({ queryKey: queryKeys.tariffs(organizationId) })
  }

  const generate = useMutation({
    mutationFn: () => invoicesApi.generate(year, month),
    onSuccess: (result) => {
      setRunResult(result)
      setError(null)
      invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const cancelInvoice = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => invoicesApi.cancel(id, reason),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const createTariff = useMutation({
    mutationFn: () => tariffsApi.create(tariffForm),
    onSuccess: () => {
      setTariffForm({ name: '', amount: '' })
      setError(null)
      invalidate()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const removeTariff = useMutation({
    mutationFn: tariffsApi.remove,
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const invoices = invoicesQuery.data?.items ?? []
  const totalDue = invoices
    .filter((i) => i.status !== 'cancelled')
    .reduce((sum, i) => sum + Number(i.amount_due), 0)

  return (
    <div className="space-y-6">
      {payingInvoice && (
        <RecordPaymentModal invoice={payingInvoice} onClose={() => setPayingInvoice(null)} />
      )}

      {advanceOpen && <RecordPaymentModal onClose={() => setAdvanceOpen(false)} />}

      {/* Qaytarish — sabab MAJBURIY: kassa jurnalida "nega qaytarildi?"
          degan savol javobsiz qolmasin (to'lovning o'zi o'chirilmaydi,
          ustiga qarshi yozuv qo'shiladi). */}
      <Modal open={Boolean(reversing)} onClose={() => setReversing(null)} className="max-w-md">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (reversing) reverseMutation.mutate({ id: reversing.id, reason: reverseReason })
          }}
          className="p-5"
        >
          <h2 className="text-base font-semibold text-slate-900">{t("To'lovni qaytarish")}</h2>
          <p className="mt-1 text-sm text-slate-500">
            {reversing?.child_name} · {reversing ? money(reversing.amount) : ''}
          </p>
          <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
            {t(
              "To'lov o'chirilmaydi — ustiga qarshi yozuv qo'shiladi va jurnalda ikkalasi ham ko'rinadi.",
            )}
          </p>
          <label htmlFor="rev-reason" className="mt-4 block text-xs font-medium text-slate-600">
            {t('Sabab')}
          </label>
          <input
            id="rev-reason"
            required
            autoFocus
            maxLength={255}
            value={reverseReason}
            onChange={(e) => setReverseReason(e.target.value)}
            placeholder={t('Masalan: xato summa kiritilgan')}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          <div className="mt-5 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setReversing(null)}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={reverseMutation.isPending}
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-700 disabled:opacity-60"
            >
              {t('Qaytarish')}
            </button>
          </div>
        </form>
      </Modal>

      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t("To'lovlar")}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t("Hisob-fakturalar ledger'ga yoziladi va tahrirlanmaydi — xato bo'lsa bekor qilinadi.")}
        </p>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(
          [
            ['invoices', t('Hisob-fakturalar')],
            ['payments', t("To'lovlar")],
            ['tariffs', t('Tariflar')],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={cn(
              '-mb-px border-b-2 px-4 py-2 text-sm font-medium transition',
              tab === key
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-800',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {tab === 'invoices' && (
        <>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="year" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Yil')}
              </label>
              <input
                id="year"
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="w-24 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label htmlFor="month" className="mb-1 block text-xs font-medium text-slate-600">
                {t('Oy')}
              </label>
              <select
                id="month"
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>
                    {String(m).padStart(2, '0')}
                  </option>
                ))}
              </select>
            </div>

            {can('payments.create') && (
              <button
                type="button"
                disabled={generate.isPending}
                onClick={() => generate.mutate()}
                className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
              >
                <FileText className="h-4 w-4" />
                {generate.isPending ? t('Chiqarilmoqda…') : t('Hisob-faktura chiqarish')}
              </button>
            )}

            {invoices.length > 0 && (
              <div className="ml-auto text-right">
                <p className="text-xs text-slate-500">{t("Davr bo'yicha jami")}</p>
                <p className="text-lg font-bold text-slate-900">{money(String(totalDue))}</p>
              </div>
            )}
          </div>

          {runResult && (
            <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
              <p className="font-semibold text-slate-900">
                {t('{period}: {created} ta yangi hisob-faktura', {
                  period: runResult.period,
                  created: runResult.created,
                })}
              </p>
              {runResult.skipped_existing > 0 && (
                <p className="mt-1 text-slate-500">
                  {t('{skipped_existing} ta allaqachon mavjud edi — qayta hisoblanmadi.', {
                    skipped_existing: runResult.skipped_existing,
                  })}
                </p>
              )}
              {runResult.skipped_no_tariff.length > 0 && (
                <p className="mt-1 text-amber-700">
                  {t("Tarifsiz bolalar o'tkazib yuborildi:")}{' '}
                  {runResult.skipped_no_tariff.join(', ')}
                </p>
              )}
            </div>
          )}

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            {invoicesQuery.isPending && (
              <p className="px-4 py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
            )}
            {invoices.length === 0 && !invoicesQuery.isPending && (
              <div className="px-4 py-12 text-center">
                <Wallet className="mx-auto mb-3 h-10 w-10 text-slate-200" />
                <p className="text-sm text-slate-500">{t("Bu davr uchun hisob-faktura yo'q.")}</p>
              </div>
            )}

            {invoices.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="px-4 py-3 font-medium">{t('Raqam')}</th>
                      <th className="px-4 py-3 font-medium">{t('Bola')}</th>
                      <th className="px-4 py-3 text-right font-medium">{t('Summa')}</th>
                      <th className="px-4 py-3 text-right font-medium">{t('Qoldiq')}</th>
                      <th className="px-4 py-3 font-medium">{t('Holat')}</th>
                      <th className="px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {invoices.map((invoice) => (
                      <tr key={invoice.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-mono text-xs text-slate-500">
                          {invoice.number}
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-800">
                          {invoice.child_name}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-700">
                          {money(invoice.amount_due)}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-500">
                          {money(invoice.amount_outstanding)}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={cn(
                              'rounded-full px-2 py-0.5 text-xs font-medium',
                              STATUS_STYLES[invoice.status],
                            )}
                          >
                            {STATUS_LABELS[invoice.status] ?? invoice.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {can('payments.create') &&
                            Number(invoice.amount_outstanding) > 0 &&
                            invoice.status !== 'cancelled' && (
                              <button
                                type="button"
                                title={t("To'lov qabul qilish")}
                                onClick={() => setPayingInvoice(invoice)}
                                className="mr-1 rounded-lg p-2 text-emerald-600 transition hover:bg-emerald-50"
                              >
                                <Banknote className="h-4 w-4" />
                              </button>
                            )}
                          {can('payments.update') && invoice.status !== 'cancelled' && (
                            <button
                              type="button"
                              title={t('Bekor qilish')}
                              onClick={() => {
                                const reason = window.prompt(t('Bekor qilish sababi:'))
                                if (reason !== null) {
                                  cancelInvoice.mutate({ id: invoice.id, reason })
                                }
                              }}
                              className="rounded-lg p-2 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                            >
                              <Ban className="h-4 w-4" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                    {invoices.length === 0 && (
                      <EmptyRow
                        colSpan={7}
                        icon={FileText}
                        title={t("Hisob-faktura yo'q")}
                        hint={t(
                          "Bolalarga tarif belgilangach, oylik hisob-fakturalar shu yerda paydo bo'ladi.",
                        )}
                      />
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {tab === 'payments' && (
        <>
          {can('payments.create') && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setAdvanceOpen(true)}
                className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
              >
                <Banknote className="h-4 w-4" />
                {t("To'lov qabul qilish")}
              </button>
            </div>
          )}

          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="border-b border-slate-200 bg-slate-50/70 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">{t('Sana')}</th>
                    <th className="px-4 py-3">{t('Bola')}</th>
                    <th className="px-4 py-3">{t('Hisob-faktura')}</th>
                    <th className="px-4 py-3">{t("To'lov usuli")}</th>
                    <th className="px-4 py-3 text-right">{t('Summa')}</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {paymentsQuery.data?.items.map((payment) => (
                    <tr
                      key={payment.id}
                      className={cn('tabular-nums', payment.is_reversed && 'text-slate-400')}
                    >
                      <td className="px-4 py-3">{formatDate(payment.paid_at)}</td>
                      <td className="px-4 py-3 font-medium text-slate-800">{payment.child_name}</td>
                      <td className="px-4 py-3 font-mono text-xs text-slate-500">
                        {payment.invoice_number ?? t('— avans —')}
                      </td>
                      <td className="px-4 py-3">
                        {METHOD_LABELS[payment.method] ?? payment.method}
                      </td>
                      <td
                        className={cn(
                          'px-4 py-3 text-right font-semibold',
                          payment.is_reversed ? 'text-slate-400 line-through' : 'text-emerald-700',
                        )}
                      >
                        {money(payment.amount)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {payment.is_reversed ? (
                          <span
                            title={payment.reversal_reason || undefined}
                            className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500"
                          >
                            {t('Qaytarilgan')}
                          </span>
                        ) : (
                          can('payments.update') && (
                            <button
                              type="button"
                              onClick={() => {
                                setReversing(payment)
                                setReverseReason('')
                              }}
                              title={t('Qaytarish')}
                              className="rounded-lg p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                            >
                              <Ban className="h-4 w-4" />
                            </button>
                          )
                        )}
                      </td>
                    </tr>
                  ))}
                  {paymentsQuery.data?.items.length === 0 && (
                    <EmptyRow
                      colSpan={6}
                      icon={Wallet}
                      title={t("Hozircha to'lov qabul qilinmagan.")}
                    />
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {tab === 'tariffs' && (
        <>
          {can('payments.create') && (
            <form
              onSubmit={(event) => {
                event.preventDefault()
                createTariff.mutate()
              }}
              className="flex flex-wrap items-end gap-3 rounded-2xl border border-slate-200 bg-white p-4"
            >
              <div className="min-w-[200px] flex-1">
                <label htmlFor="t-name" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Tarif nomi')}
                </label>
                <input
                  id="t-name"
                  required
                  value={tariffForm.name}
                  onChange={(e) => setTariffForm((p) => ({ ...p, name: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <div className="w-44">
                <label htmlFor="t-amount" className="mb-1 block text-xs font-medium text-slate-600">
                  {t('Oylik summa')}
                </label>
                <input
                  id="t-amount"
                  required
                  type="number"
                  min={0}
                  step="0.01"
                  value={tariffForm.amount}
                  onChange={(e) => setTariffForm((p) => ({ ...p, amount: e.target.value }))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
              </div>
              <button
                type="submit"
                disabled={createTariff.isPending}
                className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
              >
                <Plus className="h-4 w-4" />
                {t("Qo'shish")}
              </button>
            </form>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {tariffsQuery.data?.items.map((tariff) => (
              <div key={tariff.id} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-slate-900">{tariff.name}</p>
                    <p className="mt-0.5 text-sm text-slate-600">{money(tariff.amount)}</p>
                  </div>
                  {can('payments.delete') && (
                    <button
                      type="button"
                      onClick={() => removeTariff.mutate(tariff.id)}
                      className="shrink-0 rounded-lg p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                      title={t("O'chirish")}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {tariffsQuery.data?.items.length === 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white px-4 py-12 text-center">
              <p className="text-sm text-slate-500">
                {t(
                  "Hozircha tarif yo'q. Hisob-faktura chiqarish uchun avval tarif yarating va bolalarga biriktiring.",
                )}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
