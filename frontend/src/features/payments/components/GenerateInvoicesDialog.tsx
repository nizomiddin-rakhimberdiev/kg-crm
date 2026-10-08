/**
 * Hisob-faktura chiqarish — TASDIQ BILAN (PLAN 1.4).
 *
 * Auditda bu tugma hech narsa so'ramasdan ishlab ketardi. 200 bolali
 * bog'chada bitta bosish — 200 ta moliyaviy hujjat, va ularni
 * qaytarish uchun har birini alohida bekor qilish kerak.
 *
 * Endi avval SERVER hisoblab beradi (hech narsa yozmasdan), ro'yxat
 * ko'rsatiladi, keyin tasdiqlanadi. Ro'yxatda nafaqat "nechta", balki
 * "kimga qancha va nega" ham bor: proporsional oy "22 ish kunidan
 * 1 kun" deb izohlanadi, avansi bor bola alohida belgilanadi.
 */

import { useMutation, useQuery } from '@tanstack/react-query'
import { AlertTriangle, FileText, Loader2 } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Modal } from '@/components/ui/Modal'
import { invoicesApi } from '@/features/payments/api'
import type { BillingRunResult } from '@/lib/api/types'
import { ApiError } from '@/lib/api/types'
import { money, monthLabel } from '@/lib/format'
import { t } from '@/lib/i18n'

interface Props {
  year: number
  month: number
  onClose: () => void
  onDone: (result: BillingRunResult) => void
}

export function GenerateInvoicesDialog({ year, month, onClose, onDone }: Props) {
  const organizationId = useOrganizationId()

  const preview = useQuery({
    queryKey: ['org', organizationId, 'invoices', 'preview-run', year, month],
    queryFn: () => invoicesApi.previewRun(year, month),
    // Tasdiqlash oynasi har safar YANGI hisobni ko'rsatishi kerak:
    // keshdan kelgan ro'yxat bo'yicha tasdiqlash — eski ma'lumot
    // asosida 200 ta hujjat yaratish demak.
    staleTime: 0,
    gcTime: 0,
  })

  const run = useMutation({
    mutationFn: () => invoicesApi.generate(year, month),
    onSuccess: onDone,
  })

  const data = preview.data
  const nothingToDo = data !== undefined && data.will_create === 0
  const error = run.error ?? preview.error

  return (
    <Modal open onClose={onClose} className="max-w-lg">
      <div className="p-6">
        <div className="pr-10">
          <h2 className="text-lg font-bold text-slate-900">{t('Hisob-faktura chiqarish')}</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            {t('{period} davri uchun', { period: monthLabel(year, month) })}
          </p>
        </div>

        {preview.isPending && (
          <div className="mt-6 flex items-center justify-center gap-2 py-8 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('Hisoblanmoqda…')}
          </div>
        )}

        {error && (
          <div role="alert" className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error instanceof ApiError ? error.message : t('Xatolik yuz berdi.')}
          </div>
        )}

        {data && (
          <>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-slate-50 px-4 py-3">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t('Chiqariladi')}
                </p>
                <p className="num mt-0.5 text-2xl font-bold text-slate-900">{data.will_create}</p>
              </div>
              <div className="rounded-xl bg-slate-50 px-4 py-3">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  {t('Jami summa')}
                </p>
                <p className="num mt-0.5 text-2xl font-bold text-slate-900">
                  {money(data.total_amount)}
                </p>
              </div>
            </div>

            {/* O'tkazib yuborilganlar — SABABI bilan. "12 ta o'tkazib
                yuborildi" degan raqamning o'zi hech narsa demaydi. */}
            {(data.skipped_existing > 0 ||
              data.skipped_no_tariff.length > 0 ||
              data.skipped_next_month.length > 0) && (
              <div className="mt-3 space-y-1.5 rounded-xl border border-orik-200 bg-orik-50 px-4 py-3 text-sm">
                <p className="flex items-center gap-1.5 font-semibold text-orik-800">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  {t('Oʻtkazib yuboriladi')}
                </p>
                {data.skipped_existing > 0 && (
                  <p className="text-orik-800">
                    {t('{n} ta — allaqachon chiqarilgan', { n: data.skipped_existing })}
                  </p>
                )}
                {data.skipped_no_tariff.length > 0 && (
                  <p className="text-orik-800">
                    {t('{n} ta — tarif biriktirilmagan: {names}', {
                      n: data.skipped_no_tariff.length,
                      names: data.skipped_no_tariff.slice(0, 5).join(', '),
                    })}
                  </p>
                )}
                {data.skipped_next_month.length > 0 && (
                  <p className="text-orik-800">
                    {t('{n} ta — sozlamaga koʻra keyingi oydan', {
                      n: data.skipped_next_month.length,
                    })}
                  </p>
                )}
              </div>
            )}

            {data.rows.length > 0 && (
              <div className="mt-3 max-h-64 overflow-y-auto rounded-xl border border-slate-200 scrollbar-thin">
                <ul className="divide-y divide-slate-100">
                  {data.rows.map((row) => (
                    <li key={row.child_id} className="flex items-center gap-3 px-3 py-2">
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-slate-800">
                          {row.full_name}
                        </span>
                        <span className="block truncate text-xs text-slate-500">
                          {row.note || row.group_name || t('Guruhsiz')}
                        </span>
                      </span>
                      {Number(row.advance) > 0 && (
                        <span className="num shrink-0 rounded-full bg-nihol-50 px-2 py-0.5 text-xs font-medium text-nihol-700">
                          {t('avans {money}', { money: money(row.advance) })}
                        </span>
                      )}
                      <span className="num shrink-0 text-sm font-semibold text-slate-900">
                        {money(row.amount)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {nothingToDo && (
              <p className="mt-4 rounded-xl bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
                {t('Chiqariladigan hisob-faktura yoʻq.')}
              </p>
            )}
          </>
        )}

        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="button"
            onClick={() => run.mutate()}
            disabled={run.isPending || preview.isPending || nothingToDo}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-50"
          >
            <FileText className="h-4 w-4" />
            {run.isPending
              ? t('Chiqarilmoqda…')
              : t('{n} ta chiqarish', { n: data?.will_create ?? 0 })}
          </button>
        </div>
      </div>
    </Modal>
  )
}
