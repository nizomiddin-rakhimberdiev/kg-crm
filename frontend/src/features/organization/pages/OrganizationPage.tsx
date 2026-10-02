/**
 * Bog'cha profili (docs/04 §16).
 *
 * Ruxsat `settings` moduli bo'yicha: tashkilot egasi tahrirlaydi, direktor
 * ko'radi. Bu qasddan — bog'cha nomi va rekvizitlari kundalik operatsiya
 * emas, sozlama; ular hisob-fakturaga ham tushadi.
 */

import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Save, Trash2 } from 'lucide-react'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { OrgMark } from '@/components/brand/OrgMark'
import { organizationApi, type OrganizationInput } from '@/features/organization/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { ApiError } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatDate } from '@/lib/utils'
import { t } from '@/lib/i18n'

const FIELDS: Array<[keyof OrganizationInput, string, string]> = [
  ['name', t('Bogʻcha nomi'), 'text'],
  ['legal_name', t('Yuridik nomi'), 'text'],
  ['tax_id', t('STIR / INN'), 'text'],
  ['contact_email', t('Aloqa emaili'), 'email'],
  ['contact_phone', t('Aloqa telefoni'), 'tel'],
]

const EMPTY: OrganizationInput = {
  name: '',
  legal_name: '',
  tax_id: '',
  contact_email: '',
  contact_phone: '',
}

export default function OrganizationPage() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { refreshUser } = useAuth()
  const { can } = useCan()
  const editable = can('settings.update')

  const [form, setForm] = useState<OrganizationInput>(EMPTY)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const query = useQuery({
    queryKey: queryKeys.organization(organizationId),
    queryFn: organizationApi.get,
  })

  // Serverdan kelgan holat qoralamaning boshlang'ich qiymati bo'ladi.
  useEffect(() => {
    if (!query.data) return
    setForm({
      name: query.data.name,
      legal_name: query.data.legal_name,
      tax_id: query.data.tax_id,
      contact_email: query.data.contact_email,
      contact_phone: query.data.contact_phone,
    })
  }, [query.data])

  /**
   * Logotip (PLAN 4.6).
   *
   * Muvaffaqiyatdan keyin `auth/me` ham yangilanadi: sarlavhadagi
   * belgi shu soʻrovdan keladi va u yangilanmasa, logotip faqat
   * sahifani qayta yuklagandan keyin koʻrinardi.
   */
  const refreshBrand = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.organization(organizationId) })
    void refreshUser()
  }

  const uploadLogo = useMutation({
    mutationFn: (file: File) => organizationApi.uploadLogo(file),
    onSuccess: () => {
      setError(null)
      setSaved(true)
      refreshBrand()
    },
    onError: (err: unknown) =>
      setError(err instanceof ApiError ? err.message : t('Logotipni yuklab boʻlmadi.')),
  })

  const removeLogo = useMutation({
    mutationFn: () => organizationApi.removeLogo(),
    onSuccess: () => {
      setError(null)
      setSaved(true)
      refreshBrand()
    },
    onError: (err: unknown) =>
      setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const save = useMutation({
    mutationFn: () => organizationApi.update(form),
    onSuccess: () => {
      setError(null)
      setFieldErrors({})
      setSaved(true)
      void queryClient.invalidateQueries({ queryKey: queryKeys.organization(organizationId) })
      // Nom yon panelda ham turadi — u `/auth/me` dan keladi.
      void refreshUser()
    },
    onError: (err) => {
      setSaved(false)
      if (err instanceof ApiError) {
        setError(err.message)
        setFieldErrors(err.fieldErrors())
      } else {
        setError(t('Saqlab boʻlmadi.'))
      }
    },
  })

  if (query.isPending) {
    return <p className="py-8 text-center text-sm text-slate-400">{t('Yuklanmoqda…')}</p>
  }
  if (query.isError) {
    return (
      <p className="py-8 text-center text-sm text-red-600">
        {query.error instanceof ApiError ? query.error.message : t('Maʼlumotni yuklab boʻlmadi.')}
      </p>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Bogʻcha profili')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('Tashkilot maʼlumotlari — hisob-faktura va hujjatlarda shular ishlatiladi.')}
        </p>
      </div>

      <div className="max-w-2xl space-y-4 rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
          {/* Bogʻchaning OʻZ belgisi — umumiy ikonka emas (PLAN 4.6). */}
          <OrgMark name={query.data?.name} logoUrl={query.data?.logo_url} size={44} />
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-slate-900">{query.data?.name}</p>
            <p className="text-xs text-slate-400">
              {t('Identifikator: {slug} · Roʻyxatdan oʻtgan:', { slug: query.data?.slug })}{' '}
              {query.data ? formatDate(query.data.created_at) : '—'}
            </p>
          </div>
          {editable && (
            <div className="flex shrink-0 items-center gap-1.5">
              <label className="cursor-pointer rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50">
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  className="sr-only"
                  onChange={(event) => {
                    const file = event.target.files?.[0]
                    // Maydon tozalanadi: bir xil faylni qayta
                    // tanlaganda `change` hodisasi otilmasligi mumkin.
                    event.target.value = ''
                    if (file) uploadLogo.mutate(file)
                  }}
                />
                {uploadLogo.isPending ? t('Yuklanmoqda…') : t('Logotip')}
              </label>
              {query.data?.logo_url && (
                <button
                  type="button"
                  onClick={() => removeLogo.mutate()}
                  disabled={removeLogo.isPending}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-orik-50 hover:text-orik-700"
                  aria-label={t('Logotipni olib tashlash')}
                  title={t('Logotipni olib tashlash')}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}
        </div>

        <form
          className="mt-4 grid gap-3 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault()
            save.mutate()
          }}
        >
          {FIELDS.map(([key, label, type]) => (
            <div key={key}>
              <label htmlFor={key} className="mb-1 block text-xs font-medium text-slate-600">
                {label}
              </label>
              <input
                id={key}
                type={type}
                disabled={!editable}
                value={form[key] ?? ''}
                onChange={(e) => {
                  setForm((prev) => ({ ...prev, [key]: e.target.value }))
                  setSaved(false)
                }}
                className={cn(
                  'w-full rounded-lg border px-3 py-2 text-sm outline-none focus:ring-2 disabled:bg-slate-50 disabled:text-slate-500',
                  fieldErrors[key]
                    ? 'border-red-300 focus:ring-red-100'
                    : 'border-slate-200 focus:border-brand-500 focus:ring-brand-100',
                )}
              />
              {fieldErrors[key] && <p className="mt-1 text-xs text-red-600">{fieldErrors[key]}</p>}
            </div>
          ))}

          {error && (
            <div
              role="alert"
              className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 sm:col-span-2"
            >
              {error}
            </div>
          )}
          {saved && (
            <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700 sm:col-span-2">
              {t('Saqlandi.')}
            </div>
          )}

          {editable && (
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={save.isPending}
                className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
              >
                <Save className="h-4 w-4" />
                {save.isPending ? t('Saqlanmoqda…') : t('Saqlash')}
              </button>
            </div>
          )}
          {!editable && (
            <p className="text-xs text-slate-400 sm:col-span-2">
              {t('Tahrirlash uchun tashkilot egasi huquqi kerak.')}
            </p>
          )}
        </form>
      </div>
    </div>
  )
}
