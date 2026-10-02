/**
 * Kvitansiya — ota-ona qo'lidagi qog'oz (PLAN 1.7).
 *
 * Ikki o'lchamda chop etiladi: A4 (oddiy printer) va 80 mm (kassa
 * termoprinteri). Ikkalasi ham BITTA razmetkadan chiqadi, faqat
 * `@page` va kenglik o'zgaradi — ikkita alohida shablon ertami-kechmi
 * bir-biridan ajralardi va biri eskirib qolardi.
 *
 * Kvitansiyada summadan tashqari TAQSIMOT ham bor: qaysi oy uchun
 * qancha ketgani nizoda eng kerakli qator. Va oxirida ota-onaning
 * keyingi savoliga javob: "yana qancha qoldi?".
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Loader2, Printer } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { paymentsApi } from '@/features/payments/api'
import { formatDateTime } from '@/lib/utils'
import { money } from '@/lib/format'
import { t } from '@/lib/i18n'

type Size = 'a4' | 'thermal'

export function ReceiptModal({ paymentId, onClose }: { paymentId: string; onClose: () => void }) {
  const organizationId = useOrganizationId()
  const [size, setSize] = useState<Size>('a4')

  const receipt = useQuery({
    queryKey: ['org', organizationId, 'payments', 'receipt', paymentId],
    queryFn: () => paymentsApi.receipt(paymentId),
  })
  const data = receipt.data

  return (
    <Modal open onClose={onClose} className="max-w-md">
      {/* Chop etishda faqat kvitansiyaning o'zi qoladi: modal, fon va
          tugmalar qog'ozga tushmaydi. */}
      <style>{`
        @media print {
          body * { visibility: hidden; }
          #receipt, #receipt * { visibility: visible; }
          #receipt {
            position: absolute; inset: 0;
            margin: 0; padding: 12mm;
            width: ${size === 'thermal' ? '72mm' : 'auto'};
            font-size: ${size === 'thermal' ? '11px' : '13px'};
          }
          @page { size: ${size === 'thermal' ? '80mm auto' : 'A4'}; margin: ${size === 'thermal' ? '3mm' : '15mm'}; }
        }
      `}</style>

      <div className="p-6">
        <div className="flex items-center justify-between gap-3 pr-10 print:hidden">
          <h2 className="text-lg font-bold text-slate-900">{t('Kvitansiya')}</h2>
          <div className="flex rounded-lg border border-slate-200 p-0.5 text-xs font-semibold">
            {(
              [
                ['a4', 'A4'],
                ['thermal', t('80 mm')],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setSize(value)}
                className={
                  size === value
                    ? 'rounded-md bg-slate-900 px-2.5 py-1 text-white'
                    : 'rounded-md px-2.5 py-1 text-slate-500'
                }
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {receipt.isPending && (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('Yuklanmoqda…')}
          </div>
        )}

        {data && (
          <div id="receipt" className="mt-4 rounded-xl border border-slate-200 p-4 text-sm">
            <div className="text-center">
              <p className="font-bold text-slate-900">{data.branch}</p>
              <p className="num mt-0.5 text-xs text-slate-500">{data.number}</p>
              <p className="num text-xs text-slate-500">{formatDateTime(data.paid_at)}</p>
            </div>

            {data.reversed && (
              <p className="mt-2 rounded border border-red-200 bg-red-50 py-1 text-center text-xs font-bold text-red-700">
                {t('QAYTARILGAN')}
              </p>
            )}

            <dl className="mt-3 border-t border-dashed border-slate-300 pt-3">
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">{t('Bola')}</dt>
                <dd className="font-semibold text-slate-900">{data.child}</dd>
              </div>
              {data.cashier && (
                <div className="mt-1 flex justify-between gap-3">
                  <dt className="text-slate-500">{t('Qabul qildi')}</dt>
                  <dd className="text-slate-700">{data.cashier}</dd>
                </div>
              )}
            </dl>

            <ul className="mt-3 space-y-1 border-t border-dashed border-slate-300 pt-3">
              {data.lines.map((line, index) => (
                <li key={index} className="flex justify-between gap-3">
                  <span className="text-slate-600">{line.method}</span>
                  <span className="num font-medium text-slate-900">{money(line.amount)}</span>
                </li>
              ))}
            </ul>

            <div className="mt-3 flex justify-between gap-3 border-t border-slate-900 pt-2">
              <span className="font-bold text-slate-900">{t('Jami')}</span>
              <span className="num text-base font-bold text-slate-900">{money(data.total)}</span>
            </div>

            {/* Qaysi oy uchun qancha ketgani — nizoda eng kerakli qator. */}
            {data.allocations.length > 0 && (
              <ul className="mt-3 space-y-0.5 border-t border-dashed border-slate-300 pt-3 text-xs">
                <li className="text-slate-500">{t('Hisob-fakturalarga')}</li>
                {data.allocations.map((row) => (
                  <li key={row.invoice} className="flex justify-between gap-3">
                    <span className="text-slate-600">{row.period}</span>
                    <span className="num text-slate-700">{money(row.amount)}</span>
                  </li>
                ))}
              </ul>
            )}

            <dl className="mt-3 border-t border-dashed border-slate-300 pt-3 text-xs">
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">{t('Qolgan qarz')}</dt>
                <dd className="num font-semibold text-slate-900">{money(data.balance_after)}</dd>
              </div>
              {Number(data.advance_after) > 0 && (
                <div className="mt-0.5 flex justify-between gap-3">
                  <dt className="text-slate-500">{t('Avansda')}</dt>
                  <dd className="num font-semibold text-nihol-700">{money(data.advance_after)}</dd>
                </div>
              )}
            </dl>

            <p className="mt-4 text-center text-xs text-slate-400">Radix CRM</p>
          </div>
        )}

        <div className="mt-5 flex items-center justify-end gap-2 print:hidden">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            {t('Yopish')}
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            disabled={!data}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            <Printer className="h-4 w-4" />
            {t('Chop etish')}
          </button>
        </div>
      </div>
    </Modal>
  )
}
