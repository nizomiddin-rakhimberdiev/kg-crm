import { lazy, Suspense } from 'react'
import { Navigate, useSearchParams } from 'react-router-dom'
import { useCan } from '@/lib/rbac/useCan'
import { t } from '@/lib/i18n'

const DebtorsPage = lazy(() => import('@/features/debtors/pages/DebtorsPage'))

/**
 * `/debtors` → `/payments?tab=debtors`, soʻrov satri bilan.
 *
 * Sahifa Toʻlovlar ichiga koʻchdi (audit, 2026-10-21), lekin eski
 * manzil tirik: u bazadagi insight yozuvlarida (`deep_link`,
 * `intelligence/rules.py`) va xodimlarning xatchoʻplarida qolgan.
 *
 * **Toʻlovlarga ruxsati yoʻq odam uchun roʻyxat SHU YERDA chiziladi.**
 * `debtors.read` bor, `payments.read` yoʻq rol boʻlishi mumkin —
 * bogʻcha egasi qoʻlda yasagan "qarz yigʻuvchi" roli aynan shunday.
 * Uni `/payments` ga yuborish ekranni butunlay olib qoʻyardi, ya'ni
 * koʻchirish uning ishini buzardi.
 */
export function DebtorsRedirect() {
  const [params] = useSearchParams()
  const { can } = useCan()

  if (!can('payments.read')) {
    return (
      <Suspense
        fallback={<p className="py-10 text-center text-sm text-slate-500">{t('Yuklanmoqda…')}</p>}
      >
        <DebtorsPage />
      </Suspense>
    )
  }

  const query = params.toString()
  return <Navigate replace to={`/payments?tab=debtors${query ? `&${query}` : ''}`} />
}
