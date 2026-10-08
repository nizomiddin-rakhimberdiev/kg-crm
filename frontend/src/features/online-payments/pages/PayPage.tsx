/**
 * The parent's payment page — `/pay/:token` (PLAN 6.1).
 *
 * Opened from a Telegram message on a phone, without logging in. It
 * shows only what the parent needs to recognise the bill (kindergarten,
 * child's first name and initial, month, amount) — the link may be
 * forwarded into a family chat, so nothing more personal is on it.
 *
 * Payment happens on the provider's own page; the money is recorded by
 * the provider's callback, not by this page. Coming back with `?done=1`
 * the page re-reads the invoice for a short while, because the callback
 * can arrive a few seconds after the redirect.
 */

import { useQuery } from '@tanstack/react-query'
import { useParams, useSearchParams } from 'react-router-dom'
import { CheckCircle2, Clock, CreditCard } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'
import { LanguageSwitch } from '@/components/layout/LanguageSwitch'
import {
  onlinePaymentsApi,
  PROVIDER_LABEL,
  type OnlineProvider,
} from '@/features/online-payments/api'
import { ApiError } from '@/lib/api/types'
import { som } from '@/lib/format'
import { t } from '@/lib/i18n'

/** How long to keep re-reading after the parent returns from the provider. */
const RETURN_POLL_MS = 3000
const RETURN_POLL_LIMIT = 20

export default function PayPage() {
  const { token = '' } = useParams()
  const [params] = useSearchParams()
  const returned = params.get('done') === '1'

  const query = useQuery({
    queryKey: ['public', 'pay-link', token],
    queryFn: () => onlinePaymentsApi.publicLink(token),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 2,
    refetchInterval: (q) =>
      returned && !q.state.data?.is_paid && q.state.dataUpdateCount < RETURN_POLL_LIMIT
        ? RETURN_POLL_MS
        : false,
  })
  const data = query.data
  const notFound = query.error instanceof ApiError && query.error.status === 404
  const providers = Object.entries(data?.providers ?? {}) as [OnlineProvider, string][]

  return (
    <div className="flex min-h-screen flex-col items-center bg-sut px-4 py-8">
      <div className="flex w-full max-w-md items-center justify-between">
        <Logo height={28} />
        <LanguageSwitch />
      </div>

      <main className="mt-8 w-full max-w-md">
        {query.isPending && (
          <p className="py-16 text-center text-sm text-tosh-500">{t('Yuklanmoqda…')}</p>
        )}

        {(notFound || (query.isError && !notFound)) && (
          <div className="rounded-2xl border border-tosh-200 bg-white p-6 text-center shadow-card">
            <Clock className="mx-auto h-9 w-9 text-tosh-500" />
            <h1 className="mt-3 text-lg font-semibold text-tosh-900">
              {notFound ? t('Havola eskirgan yoki notoʻgʻri') : t('Xatolik yuz berdi.')}
            </h1>
            <p className="mt-1 text-sm text-tosh-600">
              {notFound
                ? t('Bogʻchadan yangi toʻlov havolasini soʻrang.')
                : t('Birozdan keyin sahifani qayta oching.')}
            </p>
          </div>
        )}

        {data && (
          <div className="rounded-2xl border border-tosh-200 bg-white p-6 shadow-card">
            <p className="text-sm font-medium text-tosh-500">{data.kindergarten}</p>
            <h1 className="mt-1 text-xl font-bold text-tosh-900">{data.child}</h1>
            <p className="mt-0.5 text-sm text-tosh-500">
              {t('{period} uchun toʻlov', { period: data.period })}
              <span className="text-tosh-300"> · </span>
              <span className="font-mono text-xs">{data.invoice}</span>
            </p>

            {data.is_paid ? (
              <div className="mt-6 rounded-xl bg-nihol-50 px-4 py-5 text-center">
                <CheckCircle2 className="mx-auto h-9 w-9 text-nihol-600" />
                <p className="mt-2 text-base font-semibold text-nihol-800">
                  {t('Toʻlov qabul qilindi')}
                </p>
                <p className="mt-1 text-sm text-tosh-600">
                  {t('Rahmat! Bogʻcha toʻlovni koʻradi.')}
                </p>
              </div>
            ) : (
              <>
                <div className="mt-6 rounded-xl bg-tosh-50 px-4 py-3">
                  <p className="text-xs font-medium uppercase tracking-wide text-tosh-500">
                    {t('Toʻlanishi kerak')}
                  </p>
                  <p className="num mt-0.5 text-2xl font-bold text-tosh-900">{som(data.payable)}</p>
                  {data.payable !== data.amount_due && (
                    <p className="mt-1 text-xs text-tosh-500">
                      {t('Hisob-faktura: {money}', { money: som(data.amount_due) })}
                    </p>
                  )}
                </div>

                {returned && (
                  <p className="mt-4 flex items-center gap-2 rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-900">
                    <Clock className="h-4 w-4 shrink-0" />
                    {t('Toʻlov tekshirilmoqda — sahifa oʻzi yangilanadi.')}
                  </p>
                )}

                {providers.length === 0 ? (
                  <p className="mt-4 text-sm text-tosh-600">
                    {t('Onlayn toʻlov hozircha mavjud emas. Bogʻcha bilan bogʻlaning.')}
                  </p>
                ) : (
                  <div className="mt-5 grid gap-2">
                    {providers.map(([provider, url]) => (
                      <a
                        key={provider}
                        href={url}
                        rel="noreferrer"
                        className="flex items-center justify-center gap-2 rounded-xl bg-nihol-600 px-4 py-3 text-base font-semibold text-white transition hover:bg-nihol-700"
                      >
                        <CreditCard className="h-5 w-5" />
                        {t('{provider} orqali toʻlash', { provider: PROVIDER_LABEL[provider] })}
                      </a>
                    ))}
                  </div>
                )}

                <p className="mt-4 text-xs text-tosh-500">
                  {t(
                    'Pul toʻgʻridan-toʻgʻri bogʻchaning hisobiga tushadi. Karta maʼlumotlari faqat toʻlov tizimi sahifasida kiritiladi.',
                  )}
                </p>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
