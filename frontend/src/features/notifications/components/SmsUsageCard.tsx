/**
 * Bu oy nechta SMS ketdi va qanchaga tushdi (PLAN 3.3).
 *
 * SMS — bog'chaning haqiqiy xarajati, va u sezilmasdan o'sadi: 200
 * bolali bog'chada kunlik eslatma oyiga 4000 ta xabar degani. Shuning
 * uchun son ham, taxminiy pul ham ko'rinib turishi kerak.
 *
 * Narx **bo'laklar** bo'yicha: kirill xabari 70 belgidan keyin
 * ikkinchi bo'lakka o'tadi. Narx kiritilmagan bo'lsa pul ko'rsatilmaydi
 * — "0 so'm" deb yozish SMS bepul degan ma'noni berardi.
 */

import { Clock, MessageSquare } from 'lucide-react'
import type { SmsStatus } from '@/lib/api/types'
import { money, som } from '@/lib/format'
import { t } from '@/lib/i18n'

export function SmsUsageCard({ status }: { status: SmsStatus }) {
  const { usage } = status
  return (
    <section className="rounded-xl border border-tosh-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-tosh-900">
          <MessageSquare className="h-4 w-4 text-nihol-600" />
          {t('Bu oy')}
        </h2>
        <p className="text-xs text-tosh-500">
          {t('Telegram: {telegram} · SMS: {sms}', {
            telegram: money(usage.telegram),
            sms: money(usage.sms),
          })}
        </p>
        <p className="flex items-center gap-1.5 text-xs text-tosh-500">
          <Clock className="h-3.5 w-3.5" />
          {t('Yuborish vaqti: {from}:00 – {to}:00', {
            from: String(status.send_from_hour).padStart(2, '0'),
            to: String(status.send_to_hour).padStart(2, '0'),
          })}
        </p>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <dt className="text-xs text-tosh-500">{t('Yuborilgan')}</dt>
          <dd className="num text-lg font-semibold text-tosh-900">{money(usage.sent)}</dd>
        </div>
        <div>
          <dt className="text-xs text-tosh-500">{t('SMS bo‘laklari')}</dt>
          <dd className="num text-lg font-semibold text-tosh-900">{money(usage.parts)}</dd>
        </div>
        <div>
          <dt className="text-xs text-tosh-500">{t('Xato')}</dt>
          <dd className="num text-lg font-semibold text-orik-700">{money(usage.failed)}</dd>
        </div>
        <div>
          <dt className="text-xs text-tosh-500">{t('Taxminiy xarajat')}</dt>
          <dd className="num text-lg font-semibold text-tosh-900">
            {/* Faqat SMS pul turadi — Telegram bepul (ADR-23). */}
            {usage.sms === 0 ? (
              <span className="text-sm font-normal text-nihol-700">{t('bepul')}</span>
            ) : usage.estimated_cost ? (
              som(usage.estimated_cost)
            ) : (
              <span className="text-sm font-normal text-tosh-400">{t('narx kiritilmagan')}</span>
            )}
          </dd>
        </div>
      </dl>

      {usage.test_mode > 0 && (
        <p className="mt-3 text-xs text-orik-800">
          {t(
            '{count} ta xabar test rejimida qoldi — ular ota-onalarga yuborilmagan va pul turmaydi.',
            { count: money(usage.test_mode) },
          )}
        </p>
      )}
    </section>
  )
}
