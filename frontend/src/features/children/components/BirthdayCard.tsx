/**
 * Yaqin tug'ilgan kunlar — dashboard kartasi (7 kun).
 *
 * Ma'lumot `children.read` ruxsati bilan keladi; kartani dashboard o'zi
 * shu ruxsatga qarab chizadi. Bu yerda faqat ko'rsatish.
 */

import { useQuery } from '@tanstack/react-query'
import { Cake } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { childrenApi } from '@/features/children/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { formatDateLong } from '@/lib/utils'
import { t } from '@/lib/i18n'

function whenLabel(daysUntil: number): string {
  if (daysUntil === 0) return t('Bugun')
  if (daysUntil === 1) return t('Ertaga')
  return t('{d} kundan keyin', { d: daysUntil })
}

export function BirthdayCard() {
  const organizationId = useOrganizationId()
  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.birthdays(organizationId),
    queryFn: () => childrenApi.birthdays(7),
    staleTime: 300_000,
  })

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="flex items-center gap-2">
        <Cake className="h-4 w-4 text-ildiz-700" aria-hidden />
        <h2 className="text-sm font-semibold text-slate-900">{t('Yaqin tug‘ilgan kunlar')}</h2>
      </div>
      <p className="mt-0.5 text-xs text-slate-500">{t('Keyingi 7 kun ichida')}</p>

      {isError && (
        <p role="alert" className="mt-4 text-sm text-red-700">
          {t("Ma'lumotni yuklab bo'lmadi.")}
        </p>
      )}
      {isLoading && <p className="mt-4 text-sm text-slate-400">{t('Yuklanmoqda…')}</p>}

      {!isLoading && !isError && (data?.items.length ?? 0) === 0 && (
        <p className="mt-4 text-sm text-slate-500">{t('Yaqin 7 kunda tug‘ilgan kun yo‘q.')}</p>
      )}

      {!isLoading && !isError && (data?.items.length ?? 0) > 0 && (
        <ul className="mt-4 divide-y divide-slate-100">
          {data?.items.map((child) => (
            <li key={child.id} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">{child.full_name}</p>
                <p className="text-xs text-slate-500">
                  {formatDateLong(child.birthday)} · {t('{n} yoshga to‘ladi', { n: child.turning })}
                </p>
              </div>
              <span className="shrink-0 rounded-full bg-ildiz-50 px-2.5 py-1 text-xs font-medium text-ildiz-700">
                {whenLabel(child.days_until)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
