/**
 * To'lov qabul qilish — KASSA APPARATI tartibida.
 *
 * Ilgari bu oyna forma edi: har bir usul uchun qator qo'shilardi,
 * har qatorda select va input. Kassir uchun bu sekin va chalkash —
 * u pulni sanaydi va tugma bosishni kutadi.
 *
 * Endi tartib shunday: summa yoziladi, usul TUGMASI bosiladi, va
 * o'sha summa o'sha usul bilan ro'yxatga tushadi. Ikki-uch usul
 * bilan to'langan bo'lsa, hammasi bitta oynada, bitta harakatda —
 * ko'rinib turadi va tasdiqlanadi.
 *
 * Qoldiq har bosishdan keyin qayta hisoblanadi va keyingi summa
 * o'zi kiritilib turadi, ya'ni odatiy holatda kassir hech narsa
 * yozmaydi: "Naqd" ni bosadi va tamom.
 */

import { useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Ban, Banknote, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { invoicesApi, paymentsApi, type BoardRow } from '@/features/payments/api'
import {
  PAYMENT_METHODS,
  paymentMethodColor,
  paymentMethodIcon,
  paymentMethodLabel,
} from '@/features/payments/methods'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

const money = (value: number) => new Intl.NumberFormat('uz-UZ').format(Math.round(value))

interface Tender {
  key: string
  method: string
  amount: number
}

export function TakePaymentModal({ row, onClose }: { row: BoardRow; onClose: () => void }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  const due = Number(row.outstanding)
  const credit = Math.max(0, -Number(row.balance))

  const [tenders, setTenders] = useState<Tender[]>([])
  const [error, setError] = useState<string | null>(null)

  const taken = tenders.reduce((sum, tender) => sum + tender.amount, 0)
  const left = Math.max(0, due - taken)
  const advance = Math.max(0, taken - due)

  // Kiritish maydoni qoldiq bilan to'ldirilib turadi: odatiy holatda
  // kassir hech narsa yozmasdan usul tugmasini bosadi.
  //
  // Qiymat FAQAT raqamlardan iborat matn sifatida saqlanadi, ekranda
  // esa ajratgich bilan ko'rsatiladi: "720 000" va "7 200 000" ni bir
  // qarashda farqlash mumkin, "720000" va "7200000" ni esa yo'q — va
  // bu xato pul bilan bog'liq.
  //
  // Tiyinlar ataylab yo'q: bog'cha to'lovlari butun summada bo'ladi.
  const [amount, setAmount] = useState(() => (due > 0 ? String(Math.round(due)) : ''))
  const entered = Number(amount) || 0

  // Kalit modal ochilganda BIR marta yaratiladi — qayta urinishda
  // o'zgarmasligi uni ishlatadigan qiladi (P1-003).
  const [idempotencyKey] = useState(() => crypto.randomUUID())

  const add = (method: string) => {
    if (entered <= 0) return
    setTenders((prev) => [...prev, { key: crypto.randomUUID(), method, amount: entered }])
    // Keyingi summa — qolgani. Qoldiq tugagan bo'lsa maydon bo'shaydi,
    // ya'ni ortiqcha pul faqat ATAYLAB kiritiladi.
    const rest = Math.max(0, due - (taken + entered))
    setAmount(rest > 0 ? String(Math.round(rest)) : '')
    setError(null)
  }

  const remove = (key: string) => setTenders((prev) => prev.filter((tender) => tender.key !== key))

  const byMethod = useMemo(() => {
    const totals = new Map<string, number>()
    for (const tender of tenders) {
      totals.set(tender.method, (totals.get(tender.method) ?? 0) + tender.amount)
    }
    return totals
  }, [tenders])

  const cancel = useMutation({
    mutationFn: (reason: string) => invoicesApi.cancel(row.invoice_id!, reason),
    onSuccess: () => {
      for (const key of ['payments', 'invoices', 'children', 'debtors']) {
        void queryClient.invalidateQueries({ queryKey: ['org', organizationId, key] })
      }
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const save = useMutation({
    mutationFn: () =>
      paymentsApi.recordBatch(
        {
          child_id: row.child_id,
          ...(row.invoice_id ? { invoice_id: row.invoice_id } : {}),
          lines: tenders.map((tender) => ({
            method: tender.method,
            amount: String(tender.amount),
          })),
        },
        idempotencyKey,
      ),
    onSuccess: () => {
      for (const key of ['payments', 'invoices', 'children', 'debtors', 'cash', 'dashboard']) {
        void queryClient.invalidateQueries({ queryKey: ['org', organizationId, key] })
      }
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <div className="p-6">
        <div className="pr-10">
          <h2 className="text-lg font-bold text-slate-900">{row.child_name}</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            {row.group_name || t('Guruhsiz')}
            {row.invoice_number && (
              <>
                <span className="text-slate-300"> · </span>
                <span className="font-mono text-xs">{row.invoice_number}</span>
              </>
            )}
          </p>
        </div>

        {/* Qancha to'lashi kerak — eng katta raqam, chunki kassirning
            birinchi savoli aynan shu. */}
        <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {due > 0 ? t("To'lanishi kerak") : t('Qarz yo‘q')}
          </p>
          <p className="mt-0.5 text-2xl font-bold tabular-nums text-slate-900">
            {t("{money} so'm", { money: money(due) })}
          </p>
          {credit > 0 && (
            <p className="mt-1 text-xs font-medium text-emerald-700">
              {t("Avansda {money} so'm bor", { money: money(credit) })}
            </p>
          )}
          {!row.invoice_id && (
            <p className="mt-1 text-xs text-amber-700">
              {t("Bu oy uchun hisob-faktura yo'q — pul avansga tushadi.")}
            </p>
          )}
        </div>

        {error && (
          <div role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Summa + usul tugmalari: yozing va bosing. */}
        <div className="mt-4">
          <label htmlFor="take-amount" className="mb-1 block text-xs font-medium text-slate-600">
            {t('Summa')}
          </label>
          <input
            id="take-amount"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            autoFocus
            value={amount ? money(Number(amount)) : ''}
            onFocus={(event) => event.target.select()}
            placeholder="0"
            onChange={(event) => setAmount(event.target.value.replace(/\D/g, ''))}
            /* Strelkalar (spinner) olib tashlanadi: pul summasini
               bittalab oshirish hech kimga kerak emas, katta maydonda
               esa ular buzuq ko'rinish beradi. */
            className="w-full rounded-xl border border-slate-200 px-4 py-3 text-right text-2xl font-bold tabular-nums outline-none [appearance:textfield] focus:border-brand-500 focus:ring-2 focus:ring-brand-100 [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />

          <div className="mt-3 grid grid-cols-2 gap-2">
            {PAYMENT_METHODS.map((method) => {
              const Icon = paymentMethodIcon(method)
              const already = byMethod.get(method) ?? 0
              return (
                <button
                  key={method}
                  type="button"
                  onClick={() => add(method)}
                  disabled={entered <= 0}
                  className={cn(
                    'flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left transition',
                    entered > 0
                      ? 'border-slate-200 hover:border-brand-300 hover:bg-brand-50/50'
                      : 'cursor-not-allowed border-slate-100 opacity-50',
                  )}
                >
                  <span
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-lg"
                    style={{
                      backgroundColor: `${paymentMethodColor(method)}1a`,
                      color: paymentMethodColor(method),
                    }}
                  >
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-slate-700">
                      {paymentMethodLabel(method)}
                    </span>
                    {/* Shu usul bilan qancha kiritilgani tugmaning
                        o'zida turadi — mijozning so'ragan narsasi. */}
                    <span
                      className={cn(
                        'block text-xs tabular-nums',
                        already > 0 ? 'font-semibold text-emerald-700' : 'text-slate-400',
                      )}
                    >
                      {already > 0 ? money(already) : t('bosing')}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {tenders.length > 0 && (
          <ul className="mt-4 space-y-1.5">
            {tenders.map((tender) => (
              <li
                key={tender.key}
                className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2"
              >
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: paymentMethodColor(tender.method) }}
                />
                <span className="flex-1 text-sm text-slate-600">
                  {paymentMethodLabel(tender.method)}
                </span>
                <span className="text-sm font-semibold tabular-nums text-slate-900">
                  {money(tender.amount)}
                </span>
                <button
                  type="button"
                  onClick={() => remove(tender.key)}
                  title={t("O'chirish")}
                  className="rounded p-1 text-slate-300 transition hover:bg-red-50 hover:text-red-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}

        {(taken > 0 || tenders.length > 0) && (
          <dl className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">{t('Jami')}</dt>
              <dd className="font-semibold tabular-nums text-slate-900">{money(taken)}</dd>
            </div>
            {left > 0 && (
              <div className="flex justify-between">
                <dt className="text-amber-700">{t('Qoldiq')}</dt>
                <dd className="font-medium tabular-nums text-amber-700">{money(left)}</dd>
              </div>
            )}
            {advance > 0 && (
              <div className="flex justify-between">
                <dt className="text-emerald-700">{t('Avansga (balansga)')}</dt>
                <dd className="font-medium tabular-nums text-emerald-700">{money(advance)}</dd>
              </div>
            )}
          </dl>
        )}

        {/* Hisob-fakturani bekor qilish — shu oynada, chunki faktura
            aynan bu yerda ko'rinadi. Ataylab asosiy oqimdan tashqarida
            va so'nik: u pul qabul qilish tugmasi bilan adashtirilmasin.
            Hujjat tahrirlanmaydi — bekor qilinadi (D3). */}
        {row.invoice_id && can('payments.update') && (
          <button
            type="button"
            onClick={() => {
              const reason = window.prompt(t('Bekor qilish sababi:'))
              if (reason !== null) cancel.mutate(reason)
            }}
            disabled={cancel.isPending}
            className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium text-slate-400 transition hover:bg-red-50 hover:text-red-600 disabled:opacity-60"
          >
            <Ban className="h-3.5 w-3.5" />
            {t('Hisob-fakturani bekor qilish')}
          </button>
        )}

        <button
          type="button"
          onClick={() => save.mutate()}
          disabled={save.isPending || taken <= 0}
          className={cn(
            'mt-4 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white transition',
            save.isPending || taken <= 0 ? 'bg-slate-300' : 'bg-emerald-600 hover:bg-emerald-700',
          )}
        >
          <Banknote className="h-4 w-4" />
          {save.isPending
            ? t('Saqlanmoqda…')
            : taken > 0
              ? t("{money} so'm qabul qilish", { money: money(taken) })
              : t('Usulni tanlang')}
        </button>
      </div>
    </Modal>
  )
}
