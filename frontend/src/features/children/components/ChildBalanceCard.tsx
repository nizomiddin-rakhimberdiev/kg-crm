/**
 * Bolaning puli — bitta kartochkada (PLAN 2.1).
 *
 * Auditda bola kartasida balans umuman yo'q edi: mudira "bu oila
 * qancha qarz?" degan savolga javob olish uchun Qarzdorlar ro'yxatiga
 * o'tib, u yerdan bolani qidirishi kerak edi.
 *
 * Uch raqam ataylab alohida: ular boshqa savollarga javob beradi
 * (`finance/balance.py`). Qarz — oila bizga qancha qarzdor; avans —
 * qo'limizda uning qancha puli bor; muddati o'tgan — shundan qanchasi
 * kechikkan.
 */

import { useQuery } from '@tanstack/react-query'
import { Banknote, Wallet } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { paymentsApi } from '@/features/payments/api'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate } from '@/lib/utils'
import { money } from '@/lib/format'
import { t } from '@/lib/i18n'

export function ChildBalanceCard({
  childId,
  onTakePayment,
}: {
  childId: string
  onTakePayment?: () => void
}) {
  const organizationId = useOrganizationId()
  const { can } = useCan()

  const balance = useQuery({
    queryKey: ['org', organizationId, 'payments', 'child-balance', childId],
    queryFn: () => paymentsApi.childBalance(childId),
  })
  const data = balance.data

  const debt = Number(data?.outstanding ?? 0)
  const advance = Number(data?.advance ?? 0)
  const overdue = Number(data?.overdue_amount ?? 0)
  const next = data?.open_invoices[0]

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center gap-2">
        <Wallet className="h-4 w-4 text-slate-500" />
        <h2 className="text-sm font-semibold text-slate-900">{t('Hisob')}</h2>
      </div>

      {balance.isPending ? (
        <p className="mt-3 text-sm text-slate-500">{t('Yuklanmoqda…')}</p>
      ) : (
        <>
          <p
            className={cn(
              'num mt-3 text-2xl font-bold tracking-tight',
              debt > 0 ? 'text-orik-700' : 'text-slate-900',
            )}
          >
            {t('{money} soʻm', { money: money(debt) })}
          </p>
          <p className="text-xs text-slate-500">{debt > 0 ? t('Jami qarz') : t('Qarz yoʻq')}</p>

          <dl className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-sm">
            {advance > 0 && (
              <div className="flex justify-between gap-3">
                <dt className="text-nihol-700">{t('Avansda')}</dt>
                <dd className="num font-semibold text-nihol-700">{money(advance)}</dd>
              </div>
            )}
            {overdue > 0 && (
              <div className="flex justify-between gap-3">
                <dt className="text-orik-700">
                  {t('Muddati oʻtgan ({days} kun)', { days: data?.overdue_days ?? 0 })}
                </dt>
                <dd className="num font-semibold text-orik-700">{money(overdue)}</dd>
              </div>
            )}
            {next && (
              <div className="flex justify-between gap-3">
                <dt className="text-slate-500">{t('Keyingi toʻlov')}</dt>
                <dd className="num text-slate-800">{formatDate(next.due_date)}</dd>
              </div>
            )}
          </dl>

          {can('payments.create') && onTakePayment && (
            <button
              type="button"
              onClick={onTakePayment}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-nihol-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-nihol-700"
            >
              <Banknote className="h-4 w-4" />
              {t('Toʻlov qabul qilish')}
            </button>
          )}
        </>
      )}
    </div>
  )
}
