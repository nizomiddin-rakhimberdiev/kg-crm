/**
 * "Payment link" inside the cashier's payment window (PLAN 6.1).
 *
 * The parent pays from their phone with Payme or Click; the money lands
 * in the kindergarten's own merchant account and is recorded by the
 * provider's callback — the cashier does nothing more. Asking twice
 * returns the same link while it is valid, so the button is safe to
 * press again.
 */

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Check, Copy, Link2, Send } from 'lucide-react'
import { onlinePaymentsApi, type PaymentLink } from '@/features/online-payments/api'
import { ApiError } from '@/lib/api/types'
import { formatDate } from '@/lib/format'
import { t } from '@/lib/i18n'

export function PaymentLinkButton({ invoiceId }: { invoiceId: string }) {
  const [link, setLink] = useState<PaymentLink | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const create = useMutation({
    mutationFn: () => onlinePaymentsApi.createLink(invoiceId),
    onSuccess: (result) => {
      setLink(result)
      setError(null)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const copy = async () => {
    if (!link) return
    try {
      await navigator.clipboard.writeText(link.url)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard can be blocked (http, old browser) — the URL is on screen to select.
    }
  }

  if (!link) {
    return (
      <div className="mt-3">
        <button
          type="button"
          onClick={() => create.mutate()}
          disabled={create.isPending}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-brand-300 hover:bg-brand-50/50 disabled:opacity-60"
        >
          <Link2 className="h-4 w-4" />
          {create.isPending ? t('Yuklanmoqda…') : t('Onlayn toʻlov havolasi (Payme / Click)')}
        </button>
        {error && (
          <p role="alert" className="mt-1.5 text-xs text-red-700">
            {error}
          </p>
        )}
      </div>
    )
  }

  const share = `https://t.me/share/url?url=${encodeURIComponent(link.url)}`
  return (
    <div className="mt-3 rounded-xl border border-brand-200 bg-brand-50/40 p-3">
      <label htmlFor="payment-link-url" className="block text-xs font-medium text-slate-600">
        {t('Ota-onaga yuboring — toʻlov oʻzi yoziladi')}
      </label>
      <div className="mt-1.5 flex gap-1.5">
        <input
          id="payment-link-url"
          readOnly
          value={link.url}
          onFocus={(event) => event.target.select()}
          className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 font-mono text-xs text-slate-700 outline-none"
        />
        <button
          type="button"
          onClick={() => void copy()}
          aria-label={t('Nusxalash')}
          title={t('Nusxalash')}
          className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:text-slate-900"
        >
          {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
        </button>
        <a
          href={share}
          target="_blank"
          rel="noreferrer"
          aria-label={t('Telegramda yuborish')}
          title={t('Telegramda yuborish')}
          className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-slate-200 bg-white text-slate-500 transition hover:text-slate-900"
        >
          <Send className="h-4 w-4" />
        </a>
      </div>
      <p className="mt-1.5 text-xs text-slate-500">
        {t('Havola {date} gacha ishlaydi.', { date: formatDate(link.expires_at) })}
      </p>
    </div>
  )
}
