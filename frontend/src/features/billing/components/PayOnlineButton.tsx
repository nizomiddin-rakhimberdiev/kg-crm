/**
 * "Pay online" for one open subscription invoice (PLAN 6.4).
 *
 * The money goes to Radix's own Payme / Click merchant; the provider's
 * callback records it and lifts a suspension by itself (invariant 11). The
 * links are asked for only on click: an organization without them set up
 * on the server sees the bank details below instead, nothing broken.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { CreditCard } from 'lucide-react'
import { billingApi } from '@/features/billing/api'
import { ApiError } from '@/lib/api/types'
import { t } from '@/lib/i18n'

const LABEL: Record<string, string> = { payme: 'Payme', click: 'Click' }

export function PayOnlineButton({ invoiceId }: { invoiceId: string }) {
  const [links, setLinks] = useState<Array<[string, string]> | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useMutation({
    mutationFn: () => billingApi.payLinks(invoiceId),
    onSuccess: (result) =>
      setLinks(Object.entries(result.providers ?? {}) as Array<[string, string]>),
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  if (links === null) {
    return (
      <div>
        <button
          type="button"
          onClick={() => load.mutate()}
          disabled={load.isPending}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 transition hover:border-brand-300 hover:bg-brand-50/50 disabled:opacity-60"
        >
          <CreditCard className="h-3.5 w-3.5" />
          {load.isPending ? t('Yuklanmoqda…') : t('Onlayn toʻlash')}
        </button>
        {error && <p className="mt-1 text-xs text-red-700">{error}</p>}
      </div>
    )
  }

  if (links.length === 0) {
    return (
      <p className="text-xs text-slate-500">{t('Onlayn toʻlov yoʻq — bank orqali toʻlang.')}</p>
    )
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {links.map(([provider, url]) => (
        <a
          key={provider}
          href={url}
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-brand-700"
        >
          <CreditCard className="h-3.5 w-3.5" />
          {LABEL[provider] ?? provider}
        </a>
      ))}
    </div>
  )
}
