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
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Ban, Banknote, X } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { invoicesApi, paymentsApi, type BoardRow, type OpenInvoice } from '@/features/payments/api'
import {
  PAYMENT_METHODS,
  paymentMethodColor,
  paymentMethodIcon,
  paymentMethodLabel,
} from '@/features/payments/methods'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { money } from '@/lib/format'
import { t } from '@/lib/i18n'

interface Tender {
  key: string
  method: string
  amount: number
}

interface Allocation {
  invoice: OpenInvoice
  amount: number
}

/**
 * Pul qaysi hujjatlarga tushishini oldindan hisoblaydi (Q1).
 *
 * Tartib serverdagi bilan BIR XIL: ro'yxat backenddan allaqachon FIFO
 * (`due_date`) bo'yicha keladi va bu yerda faqat ustidan yuriladi.
 * Shuning uchun ekranda ko'rsatilgan taqsimot — aynan bajariladigan
 * taqsimot, taxmin emas.
 */
function planAllocation(
  invoices: OpenInvoice[],
  money: number,
  preferred: string | null,
): { rows: Allocation[]; leftover: number } {
  const queue = preferred
    ? [
        ...invoices.filter((invoice) => invoice.id === preferred),
        ...invoices.filter((invoice) => invoice.id !== preferred),
      ]
    : invoices

  const rows: Allocation[] = []
  let left = money
  for (const invoice of queue) {
    if (left <= 0) break
    const outstanding = Number(invoice.outstanding)
    if (outstanding <= 0) continue
    const share = Math.min(left, outstanding)
    rows.push({ invoice, amount: share })
    left -= share
  }
  return { rows, leftover: left }
}

export function TakePaymentModal({
  row,
  onClose,
  onPaid,
}: {
  row: BoardRow
  onClose: () => void
  /** To'lov yozilgach chaqiriladi — kvitansiyani ochish uchun. */
  onPaid?: (paymentId: string) => void
}) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()

  // Bolaning TO'LIQ manzarasi — doskadagi qator faqat shu oyni biladi,
  // pul esa eng eski ochiq hujjatdan boshlab yopiladi (FIFO, Q1).
  const balanceQuery = useQuery({
    queryKey: ['org', organizationId, 'payments', 'child-balance', row.child_id],
    queryFn: () => paymentsApi.childBalance(row.child_id),
  })
  const detail = balanceQuery.data
  // `useMemo` shart: `?? []` har renderda yangi massiv yaratadi va
  // quyidagi `planAllocation` har safar qayta hisoblanardi.
  const openInvoices = useMemo(() => detail?.open_invoices ?? [], [detail])

  // Qancha to'lashi kerak — BARCHA ochiq hujjatlar bo'yicha, faqat shu
  // oy emas: kassirning savoli "bu bola hozir qancha qarz?" degani.
  const due = openInvoices.reduce((sum, invoice) => sum + Number(invoice.outstanding), 0)
  const credit = Number(detail?.advance ?? 0)

  const [tenders, setTenders] = useState<Tender[]>([])
  const [preferred, setPreferred] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const taken = tenders.reduce((sum, tender) => sum + tender.amount, 0)
  const left = Math.max(0, due - taken)
  const advance = Math.max(0, taken - due)

  // Avans ham taqsimlanadi: u allaqachon kassada turgan pul.
  const plan = useMemo(
    () => planAllocation(openInvoices, taken + credit, preferred),
    [openInvoices, taken, credit, preferred],
  )

  // Kiritish maydoni qoldiq bilan to'ldirilib turadi: odatiy holatda
  // kassir hech narsa yozmasdan usul tugmasini bosadi.
  //
  // Qiymat FAQAT raqamlardan iborat matn sifatida saqlanadi, ekranda
  // esa ajratgich bilan ko'rsatiladi: "720 000" va "7 200 000" ni bir
  // qarashda farqlash mumkin, "720000" va "7200000" ni esa yo'q — va
  // bu xato pul bilan bog'liq.
  //
  // Tiyinlar ataylab yo'q: bog'cha to'lovlari butun summada bo'ladi.
  const [amount, setAmount] = useState('')
  const entered = Number(amount) || 0

  // Qoldiq so'rov kelgach BIR marta kiritib qo'yiladi: odatiy holatda
  // kassir hech narsa yozmasdan usul tugmasini bosadi.
  const [prefilled, setPrefilled] = useState(false)
  if (!prefilled && detail) {
    setPrefilled(true)
    if (due > 0) setAmount(String(Math.round(due)))
  }

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
      invalidateMoney(queryClient, organizationId)
      onClose()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const save = useMutation({
    mutationFn: () =>
      paymentsApi.recordBatch(
        {
          child_id: row.child_id,
          // Kassir aniq hujjatni tanlagan bo'lsa, taqsimot o'shandan
          // boshlanadi; aks holda server FIFO qiladi.
          ...(preferred ? { invoice_id: preferred } : {}),
          lines: tenders.map((tender) => ({
            method: tender.method,
            amount: String(tender.amount),
          })),
        },
        idempotencyKey,
      ),
    onSuccess: (payments) => {
      invalidateMoney(queryClient, organizationId)
      onClose()
      // Kvitansiya DARHOL taklif qilinadi: kassir uni ota-ona hali
      // kassada turganda beradi, keyin emas.
      if (payments[0]) onPaid?.(payments[0].id)
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
            {due > 0 ? t('Toʻlanishi kerak') : t('Qarz yoʻq')}
          </p>
          <p className="mt-0.5 text-2xl font-bold tabular-nums text-slate-900">
            {t('{money} soʻm', { money: money(due) })}
          </p>
          {credit > 0 && (
            <p className="mt-1 text-xs font-medium text-emerald-700">
              {t('Avansda {money} soʻm bor', { money: money(credit) })}
            </p>
          )}
          {openInvoices.length > 1 && (
            <p className="mt-1 text-xs text-slate-500">
              {t('{n} ta ochiq hisob-faktura', { n: openInvoices.length })}
            </p>
          )}
          {detail && openInvoices.length === 0 && (
            <p className="mt-1 text-xs text-orik-700">
              {t('Ochiq hisob-faktura yoʻq — pul avansga tushadi.')}
            </p>
          )}
        </div>

        {/* Ochiq hujjatlar — FIFO tartibida. Kassir odatda hech narsa
            tanlamaydi (pul o'zi eng eskisidan boshlab yopadi), lekin
            ota-ona "aynan sentabr uchun" desa, tanlay oladi (Q1). */}
        {openInvoices.length > 1 && (
          <div className="mt-3 space-y-1">
            {openInvoices.map((invoice) => {
              const chosen = preferred === invoice.id
              return (
                <button
                  key={invoice.id}
                  type="button"
                  onClick={() => setPreferred(chosen ? null : invoice.id)}
                  className={cn(
                    'flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left transition',
                    chosen
                      ? 'border-brand-400 bg-brand-50'
                      : 'border-slate-200 hover:border-slate-300',
                  )}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-medium text-slate-700">
                      {invoice.period}
                      <span className="ml-1.5 font-mono text-[11px] text-slate-400">
                        {invoice.number}
                      </span>
                    </span>
                    {invoice.is_overdue && (
                      <span className="text-[11px] font-medium text-orik-700">
                        {t('Muddati oʻtgan')}
                      </span>
                    )}
                  </span>
                  <span className="num shrink-0 text-sm font-semibold text-slate-900">
                    {money(Number(invoice.outstanding))}
                  </span>
                </button>
              )
            })}
            {preferred && (
              <p className="pt-0.5 text-[11px] text-slate-500">
                {t('Avval tanlangan hujjat yopiladi, ortigʻi keyingisiga oʻtadi.')}
              </p>
            )}
          </div>
        )}

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
                  title={t('Oʻchirish')}
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

        {/* Bu pul qaysi hujjatlarni yopadi.
            Auditda kassir buni umuman ko'rmasdi: to'lov "avans" bo'lib
            yozilar, hisob-faktura esa "To'lanmagan" bo'lib turaverardi.
            Endi taqsimot tasdiqlashdan OLDIN ko'rinadi. */}
        {plan.rows.length > 0 && (
          <div className="mt-3 rounded-xl border border-slate-200 bg-white p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              {t('Qaysi hisob-fakturaga tushadi')}
            </p>
            <ul className="mt-1.5 space-y-1">
              {plan.rows.map((allocation) => (
                <li
                  key={allocation.invoice.id}
                  className="flex items-center justify-between gap-2 text-sm"
                >
                  <span className="min-w-0 truncate text-slate-600">
                    {allocation.invoice.period}
                    {allocation.amount >= Number(allocation.invoice.outstanding) && (
                      <span className="ml-1.5 text-[11px] font-medium text-emerald-700">
                        {t('yopiladi')}
                      </span>
                    )}
                  </span>
                  <span className="num shrink-0 font-semibold text-slate-900">
                    {money(allocation.amount)}
                  </span>
                </li>
              ))}
              {plan.leftover > 0 && (
                <li className="flex items-center justify-between gap-2 border-t border-slate-100 pt-1 text-sm">
                  <span className="text-emerald-700">{t('Avansda qoladi')}</span>
                  <span className="num shrink-0 font-semibold text-emerald-700">
                    {money(plan.leftover)}
                  </span>
                </li>
              )}
            </ul>
          </div>
        )}

        {/* Hisob-fakturani bekor qilish — shu oynada, chunki faktura
            aynan bu yerda ko'rinadi. Ataylab asosiy oqimdan tashqarida
            va so'nik: u pul qabul qilish tugmasi bilan adashtirilmasin.
            Hujjat tahrirlanmaydi — bekor qilinadi (D3). */}
        {row.invoice_id && can('payments.update') && tenders.length === 0 && (
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
              ? t('{money} soʻm qabul qilish', { money: money(taken) })
              : t('Usulni tanlang')}
        </button>
      </div>
    </Modal>
  )
}
