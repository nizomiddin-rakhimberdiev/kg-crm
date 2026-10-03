/**
 * Settings → Online payment (PLAN 6.1, ADR-26).
 *
 * The kindergarten connects ITS OWN Payme / Click merchant: money goes
 * straight to its account, Radix never holds it. Two things go between
 * this screen and the provider's merchant cabinet — the keys come here,
 * and the callback address goes there. Both are on the same card so the
 * setup is one sitting.
 *
 * The secret is write-only: after saving, only its last four characters
 * are shown, enough to tell which key is in place.
 */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, CreditCard } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { useToast } from '@/app/providers/ToastProvider'
import { Switch } from '@/components/ui/primitives'
import {
  onlinePaymentsApi,
  PROVIDER_LABEL,
  type MerchantCredentialState,
  type OnlineProvider,
} from '@/features/online-payments/api'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { t } from '@/lib/i18n'

const inputClass =
  'w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-brand-500 disabled:bg-slate-50'

export function OnlinePaymentSettings() {
  const organizationId = useOrganizationId()
  const query = useQuery({
    queryKey: ['org', organizationId, 'online-payments', 'credentials'],
    queryFn: onlinePaymentsApi.credentials,
  })

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <h2 className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-900">
        <CreditCard className="h-4 w-4 text-slate-500" />
        {t('Onlayn toʻlov')}
      </h2>
      <p className="px-4 pt-3 text-xs text-slate-500">
        {t(
          'Ota-onalar Payme yoki Click orqali toʻlaydi, pul toʻgʻridan-toʻgʻri bogʻchangiz hisobiga tushadi va toʻlov tizimga oʻzi yoziladi. Kalitlarni toʻlov tizimining kabinetidan oling.',
        )}
      </p>
      <div className="divide-y divide-slate-100">
        {query.isPending && <p className="px-4 py-6 text-sm text-slate-400">{t('Yuklanmoqda…')}</p>}
        {query.data?.map((state) => (
          <ProviderRow key={state.provider} state={state} />
        ))}
      </div>
    </section>
  )
}

function ProviderRow({ state }: { state: MerchantCredentialState }) {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { can } = useCan()
  const editable = can('settings.update')
  const provider: OnlineProvider = state.provider
  const id = `merchant-${provider}`

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    merchant_id: state.merchant_id,
    service_id: state.service_id,
    secret: '',
    sandbox: state.sandbox,
  })
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const refresh = () =>
    queryClient.invalidateQueries({
      queryKey: ['org', organizationId, 'online-payments', 'credentials'],
    })

  const save = useMutation({
    mutationFn: () =>
      onlinePaymentsApi.saveCredential(provider, {
        merchant_id: form.merchant_id.trim(),
        ...(provider === 'click' ? { service_id: form.service_id.trim() } : {}),
        secret: form.secret.trim(),
        sandbox: form.sandbox,
      }),
    onSuccess: () => {
      setEditing(false)
      setError(null)
      setForm((prev) => ({ ...prev, secret: '' }))
      toast(t('Saqlandi'))
      void refresh()
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Saqlab boʻlmadi.')),
  })

  const remove = useMutation({
    mutationFn: () => onlinePaymentsApi.removeCredential(provider),
    onSuccess: () => void refresh(),
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(state.webhook_url)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard blocked — the address is on screen to select.
    }
  }

  return (
    <div className="space-y-3 px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-900">{PROVIDER_LABEL[provider]}</p>
          <p className="text-xs text-slate-500">
            {state.configured
              ? t('Ulangan · kalit …{hint}', { hint: state.secret_hint }) +
                (state.sandbox ? ` · ${t('sinov rejimi')}` : '')
              : t('Ulanmagan')}
          </p>
        </div>
        {editable && !editing && (
          <div className="flex items-center gap-2">
            {state.configured && (
              <button
                type="button"
                disabled={remove.isPending}
                onClick={() => {
                  if (
                    window.confirm(
                      t('{provider} orqali toʻlovni oʻchirasizmi?', {
                        provider: PROVIDER_LABEL[provider],
                      }),
                    )
                  )
                    remove.mutate()
                }}
                className="rounded-lg px-3 py-1.5 text-sm text-slate-500 transition hover:bg-red-50 hover:text-red-600"
              >
                {t('Oʻchirish')}
              </button>
            )}
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              {state.configured ? t('Kalitni almashtirish') : t('Ulash')}
            </button>
          </div>
        )}
      </div>

      <div>
        <label htmlFor={`${id}-webhook`} className="mb-1 block text-xs font-medium text-slate-600">
          {t('Toʻlov tizimi kabinetiga kiritiladigan manzil')}
        </label>
        <div className="flex gap-1.5">
          <input
            id={`${id}-webhook`}
            readOnly
            value={state.webhook_url}
            onFocus={(event) => event.target.select()}
            className={`${inputClass} font-mono text-xs`}
          />
          <button
            type="button"
            onClick={() => void copy()}
            aria-label={t('Nusxalash')}
            title={t('Nusxalash')}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-slate-200 text-slate-500 transition hover:text-slate-900"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {editing && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            save.mutate()
          }}
          className="grid gap-3 rounded-lg bg-slate-50 p-3 sm:grid-cols-2"
        >
          <div>
            <label
              htmlFor={`${id}-merchant`}
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {provider === 'payme' ? t('Kassa ID (merchant)') : t('Merchant ID')}
            </label>
            <input
              id={`${id}-merchant`}
              required
              autoComplete="off"
              value={form.merchant_id}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, merchant_id: event.target.value }))
              }
              className={inputClass}
            />
          </div>
          {provider === 'click' && (
            <div>
              <label
                htmlFor={`${id}-service`}
                className="mb-1 block text-xs font-medium text-slate-600"
              >
                {t('Service ID')}
              </label>
              <input
                id={`${id}-service`}
                required
                autoComplete="off"
                inputMode="numeric"
                value={form.service_id}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, service_id: event.target.value }))
                }
                className={inputClass}
              />
            </div>
          )}
          <div className="sm:col-span-2">
            <label
              htmlFor={`${id}-secret`}
              className="mb-1 block text-xs font-medium text-slate-600"
            >
              {t('Maxfiy kalit')}
            </label>
            <input
              id={`${id}-secret`}
              required
              type="password"
              autoComplete="new-password"
              value={form.secret}
              onChange={(event) => setForm((prev) => ({ ...prev, secret: event.target.value }))}
              className={inputClass}
            />
          </div>
          <div className="flex items-center gap-3 sm:col-span-2">
            <Switch
              checked={form.sandbox}
              onChange={(next) => setForm((prev) => ({ ...prev, sandbox: next }))}
              label={t('Sinov rejimi (sandbox)')}
            />
            <span className="text-sm text-slate-700">{t('Sinov rejimi (sandbox)')}</span>
          </div>
          {error && (
            <p role="alert" className="text-sm text-red-700 sm:col-span-2">
              {error}
            </p>
          )}
          <div className="flex justify-end gap-2 sm:col-span-2">
            <button
              type="button"
              onClick={() => {
                setEditing(false)
                setError(null)
              }}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
            >
              {t('Bekor qilish')}
            </button>
            <button
              type="submit"
              disabled={save.isPending}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
            </button>
          </div>
        </form>
      )}
      {!editing && error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}
