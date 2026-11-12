/**
 * Tasdiq oynasi — qaytarib bo'lmaydigan yoki pul tegadigan amallar uchun.
 *
 * Auditda ro'yxatdagi guruh va kartadagi tarif select'lari tasdiqsiz
 * DARHOL saqlanardi: sichqoncha g'ildiragining bitta aylanishi bolani
 * boshqa guruhga ko'chirib yuborardi, tarif o'zgarishi esa keyingi
 * hisob-fakturaning summasini o'zgartirardi (Q4).
 *
 * `window.confirm` emas: u brauzerga qarab boshqacha ko'rinadi, tilni
 * bilmaydi va nima o'zgarishini tushuntira olmaydi — bu yerda esa
 * "nimadan nimaga" ko'rsatiladi.
 */

import { useEffect, useId, useState, type ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

interface Props {
  open: boolean
  title: string
  /** Nima o'zgarishi — "Quyosh → Yulduzcha" kabi aniq matn. */
  body?: ReactNode
  confirmLabel?: string
  tone?: 'default' | 'danger'
  busy?: boolean
  /**
   * Sabab so'raladi va `onConfirm` ga beriladi. Pul yoki hujjatni
   * bekor qilish izsiz qolmasin — backend ham kamida
   * `REASON_MIN` belgini talab qiladi.
   */
  requireReason?: boolean
  onConfirm: (reason: string) => void
  onCancel: () => void
}

/** Backend `apps/core/params.py` dagi `REASON_MIN` bilan bir xil. */
export const REASON_MIN = 5

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel,
  tone = 'default',
  busy = false,
  requireReason = false,
  onConfirm,
  onCancel,
}: Props) {
  const [reason, setReason] = useState('')
  const reasonId = useId()
  useEffect(() => {
    if (open) setReason('')
  }, [open])
  const reasonMissing = requireReason && reason.trim().length < REASON_MIN

  return (
    <Modal open={open} onClose={onCancel} className="max-w-sm">
      <div className="p-6">
        <div className="flex items-start gap-3 pr-8">
          <span
            className={cn(
              'grid h-9 w-9 shrink-0 place-items-center rounded-xl',
              tone === 'danger' ? 'bg-red-50 text-red-600' : 'bg-orik-50 text-orik-700',
            )}
          >
            <AlertTriangle className="h-4.5 w-4.5" />
          </span>
          <div className="min-w-0">
            <h2 className="text-base font-bold text-slate-900">{title}</h2>
            {body && <div className="mt-1 text-sm leading-6 text-slate-600">{body}</div>}
          </div>
        </div>

        {requireReason && (
          <div className="mt-4">
            <label htmlFor={reasonId} className="text-xs font-semibold text-slate-600">
              {t('Sabab')}
            </label>
            <textarea
              id={reasonId}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              rows={2}
              maxLength={255}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            />
            <p className="mt-1 text-xs text-slate-500">
              {t('Kamida {n} ta belgi — audit jurnaliga yoziladi.', { n: REASON_MIN })}
            </p>
          </div>
        )}

        <div className="mt-5 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            {t('Bekor qilish')}
          </button>
          <button
            type="button"
            onClick={() => onConfirm(reason.trim())}
            disabled={busy || reasonMissing}
            className={cn(
              'rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:opacity-50',
              tone === 'danger' ? 'bg-red-600 hover:bg-red-700' : 'bg-brand-600 hover:bg-brand-700',
            )}
          >
            {busy ? t('Saqlanmoqda…') : (confirmLabel ?? t('Tasdiqlash'))}
          </button>
        </div>
      </div>
    </Modal>
  )
}
