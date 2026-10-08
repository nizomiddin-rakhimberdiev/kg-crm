/**
 * Soʻrov xatosi — bitta koʻrinish (PLAN 10.14).
 *
 * Auditda oʻnta asosiy sahifadan SAKKIZTASIDA xato tarmogʻi umuman
 * yoʻq edi: roʻyxat soʻrovi yiqilsa (internet uzilgan, server 500
 * qaytargan) `data` boʻsh qoladi, "boʻsh roʻyxat" sharti esa
 * `data && …` boʻlgani uchun ishlamaydi — natijada sahifada sarlavha
 * turadi va ostida HECH NARSA yoʻq. Foydalanuvchi buni "maʼlumotim
 * yoʻqoldi" deb oʻqiydi.
 *
 * Shuning uchun uchta narsa aytiladi: nima boʻldi, maʼlumot
 * yoʻqolmagani, va qayta urinish tugmasi — chunki sabab koʻpincha
 * bir soniyalik uzilish boʻladi va sahifani qayta yuklash kerak emas.
 */

import { AlertTriangle } from 'lucide-react'
import { ApiError } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

export function QueryError({
  error,
  onRetry,
  className,
}: {
  error: unknown
  onRetry?: () => void
  className?: string
}) {
  const message = error instanceof ApiError ? error.message : t('Maʼlumotni yuklab boʻlmadi.')
  return (
    <div role="alert" className={cn('px-4 py-10 text-center', className)}>
      <AlertTriangle className="mx-auto h-8 w-8 text-orik-500" />
      <p className="mt-3 text-sm font-medium text-orik-900">{message}</p>
      <p className="mt-1 text-sm text-tosh-500">
        {t('Maʼlumot yoʻqolmadi — aloqa tiklangach qayta koʻrinadi.')}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 inline-flex min-h-11 items-center rounded-lg border border-tosh-200 px-4 text-sm font-semibold text-tosh-700 transition hover:bg-tosh-50"
        >
          {t('Qayta urinish')}
        </button>
      )}
    </div>
  )
}
