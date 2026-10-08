/**
 * Oylik varaqasi — RASMIY va NAQD qism alohida (ADR-18).
 *
 * Nega jadvalda emas: ustunlar soni oltitadan o'n ikkitaga chiqardi va
 * telefonda o'qib bo'lmasdi. Buxgalter himoya qiladigan hujjat esa
 * aynan shu — ikkita blok va ularning yig'indisi.
 */

import { Modal } from '@/components/ui/Modal'
import type { PayrollItem } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { money } from '@/lib/format'
import { t } from '@/lib/i18n'

function Row({
  label,
  value,
  negative = false,
  strong = false,
}: {
  label: string
  value: string
  negative?: boolean
  strong?: boolean
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1.5">
      <span className="text-sm text-slate-600">{label}</span>
      <span
        className={cn(
          'text-sm tabular-nums',
          strong && 'font-semibold text-slate-900',
          negative ? 'text-red-600' : !strong && 'text-slate-700',
        )}
      >
        {negative ? '− ' : ''}
        {money(value)}
      </span>
    </div>
  )
}

export function PayslipModal({ item, onClose }: { item: PayrollItem | null; onClose: () => void }) {
  if (!item) return null

  const hasOfficial = Number(item.official_base) > 0
  const cashBase = Number(item.base_amount) - Number(item.official_base)

  return (
    <Modal open onClose={onClose} className="max-w-md">
      <div className="p-6">
        <div className="pr-10">
          <h2 className="text-lg font-bold text-slate-900">{t('Oylik varaqasi')}</h2>
          <p className="mt-1 text-sm text-slate-500">{item.employee_name}</p>
        </div>

        {hasOfficial && (
          <section className="mt-5 rounded-xl border border-slate-200 p-4">
            <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {t('Rasmiy qism — kartaga')}
            </h3>
            <div className="mt-1 divide-y divide-slate-100">
              <Row label={t('Lavozim maoshi')} value={item.official_base} />
              <Row label={t('Daromad soligʻi')} value={item.tax_income} negative />
              <Row label={t('Pensiya badali')} value={item.tax_pension} negative />
              <Row label={t('Oʻtkaziladi')} value={item.official_net} strong />
            </div>
          </section>
        )}

        <section className="mt-3 rounded-xl border border-slate-200 p-4">
          <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {hasOfficial ? t('Naqd qism') : t('Naqd')}
          </h3>
          <div className="mt-1 divide-y divide-slate-100">
            <Row label={t('Maosh')} value={String(cashBase)} />
            {Number(item.bonus) > 0 && <Row label={t('Bonus')} value={item.bonus} />}
            {Number(item.deduction) > 0 && (
              <Row label={t('Ushlab qolish')} value={item.deduction} negative />
            )}
            {Number(item.advance) > 0 && (
              <Row label={t('Avans (allaqachon berilgan)')} value={item.advance} negative />
            )}
            <Row label={t('Beriladi')} value={item.cash_net} strong />
          </div>
        </section>

        <div className="mt-4 flex items-baseline justify-between gap-3 border-t border-slate-200 pt-3">
          <span className="text-sm font-medium text-slate-600">{t('Jami qoʻlga')}</span>
          <span className="text-xl font-bold tabular-nums text-slate-900">{money(item.net)}</span>
        </div>

        {hasOfficial && (
          <p className="mt-3 text-xs text-slate-500">
            {t(
              'Ushlab qolingan soliq xodimga berilmaydi va kassadan ham chiqmaydi — u davlatga toʻlanganda oddiy chiqim boʻlib yoziladi.',
            )}
          </p>
        )}

        {item.note && <p className="mt-3 text-xs text-slate-500">{item.note}</p>}
      </div>
    </Modal>
  )
}
