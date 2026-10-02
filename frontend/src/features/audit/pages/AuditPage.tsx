/**
 * Audit jurnali (docs/04 §17).
 *
 * Faqat o'qish — jurnal tahrirlanmaydi va o'chirilmaydi (D3). Bu
 * sahifaning butun ma'nosi shundaki, unga tegib bo'lmaydi: "kim
 * o'chirdi?" degan savolga javob ham o'chirilib ketmasin.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ScrollText, ShieldCheck } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { auditApi } from '@/features/dashboard/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { cn } from '@/lib/utils'
import { env } from '@/config/env'
import { t } from '@/lib/i18n'

const ACTION: Record<string, [string, string]> = {
  login: [t('Kirish'), 'bg-slate-100 text-slate-600'],
  login_failed: [t('Kirish urinishi'), 'bg-amber-50 text-amber-700'],
  // Xavfsizlik hodisalari (PLAN 5.2, 5.3, 5.5). Ular jadvalda XOM
  // nom bilan chiqib turardi: `ACTION` da yo'q qiymat shunchaki
  // o'zini ko'rsatadi, va o'qiyotgan odam uchun `login_blocked`
  // hech narsa demaydi.
  login_blocked: [t('Kirish bloklandi'), 'bg-red-50 text-red-700'],
  password_reset_requested: [t('Parol tiklash soʻraldi'), 'bg-amber-50 text-amber-700'],
  password_reset: [t('Parol tiklandi'), 'bg-amber-50 text-amber-700'],
  invite_accepted: [t('Taklif qabul qilindi'), 'bg-emerald-50 text-emerald-700'],
  logout: [t('Chiqish'), 'bg-slate-100 text-slate-600'],
  signup: [t('Roʻyxatdan oʻtish'), 'border border-ildiz-300 bg-ildiz-50 text-ildiz-800'],
  password_change: [t('Parol oʻzgardi'), 'bg-amber-50 text-amber-700'],
  create: [t('Yaratildi'), 'bg-emerald-50 text-emerald-700'],
  update: [t('Yangilandi'), 'border border-ildiz-300 bg-ildiz-50 text-ildiz-800'],
  delete: [t('Oʻchirildi'), 'bg-red-50 text-red-700'],
}

const ENTITY: Record<string, string> = {
  child: t('Bola'),
  enrollment: t('Guruhga biriktirish'),
  group: t('Guruh'),
  guardian: t('Vasiy'),
  employee: t('Xodim'),
  product: t('Mahsulot'),
  tariff: t('Tarif'),
  cash_account: t('Kassa'),
  absence_claim: t('Kelmagan kun daʼvosi'),
  notification: t('Bildirishnoma'),
  notification_template: t('Xabar shabloni'),
  subscription: t('Obuna'),
  support_grant: t('Qoʻllab-quvvatlash ruxsati'),
  child_import: t('Bolalar importi'),
  payment: t('Toʻlov'),
  invoice: t('Hisob-faktura'),
  invoice_run: t('Hisob-faktura generatsiyasi'),
  discount: t('Chegirma'),
  expense: t('Chiqim'),
  stock_movement: t('Stok harakati'),
  system_setting: t('Sozlama'),
  user: t('Foydalanuvchi'),
  role: t('Rol'),
  branch: t('Filial'),
  organization: t('Tashkilot'),
  payroll_run: t('Oylik hisoblash'),
}

/**
 * Oʻzgargan maydonning nomi — odam tilida (PLAN 4.4).
 *
 * Auditda bu ustun `status: "archived", reason: "…"` koʻrinishida
 * edi: inglizcha kalit va JSON. Jurnalni mudira oʻqiydi, va u
 * maydon nomlarini bilishi kerak emas.
 */
const FIELD: Record<string, string> = {
  status: t('Holat'),
  reason: t('Sabab'),
  amount: t('Summa'),
  name: t('Nomi'),
  from: t('Nimadan'),
  to: t('Nimaga'),
  before: t('Oldin'),
  after: t('Keyin'),
  child: t('Bola'),
  group: t('Guruh'),
  guardian: t('Vasiy'),
  employee: t('Xodim'),
  product: t('Mahsulot'),
  tariff: t('Tarif'),
  invoice: t('Hisob-faktura'),
  payment: t('Toʻlov'),
  cash_account: t('Kassa'),
  role: t('Rol'),
  method: t('Usul'),
  direction: t('Yoʻnalish'),
  movement_type: t('Harakat turi'),
  fields: t('Maydonlar'),
  permissions: t('Ruxsatlar'),
  archived: t('Arxivlangan'),
  reactivated: t('Qayta faollashtirilgan'),
  reversed: t('Qaytarilgan'),
  revoked: t('Bekor qilingan'),
  suspended: t('Toʻxtatilgan'),
  forced: t('Majburan'),
  days: t('Kunlar'),
  until: t('Qachongacha'),
  expires_at: t('Amal qilish muddati'),
  total_net: t('Sof summa'),
  payouts: t('Toʻlovlar soni'),
  created: t('Yaratildi'),
  skipped: t('Oʻtkazib yuborildi'),
  recalculated: t('Qayta hisoblandi'),
  email: t('Email'),
  slug: t('Manzil nomi'),
  severity: t('Jiddiylik'),
  kind: t('Turi'),
  type: t('Turi'),
  telegram: t('Telegram'),
  self_profile: t('Oʻz profili'),
  sessions_closed: t('Yopilgan sessiyalar'),
  password_reset: t('Parol tiklandi'),
  trial_extended_days: t('Sinov uzaytirildi (kun)'),
  n: t('Soni'),
  batch: t('Partiya'),
  credit: t('Kredit'),
  movement: t('Harakat'),
  id: t('Identifikator'),
  key: t('Kalit'),
  reopened_from: t('Qaytib ochildi'),
}

/** JSON emas, odam oʻqiydigan qiymat. */
function fieldValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? t('ha') : t('yoʻq')
  if (Array.isArray(value)) return value.map((item) => fieldValue(item)).join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const FILTERS: Array<[string, string]> = [
  ['', t('Hammasi')],
  ['create', t('Yaratish')],
  ['update', t('Yangilash')],
  ['delete', t('Oʻchirish')],
  ['login_failed', t('Kirish urinishlari')],
  ['login_blocked', t('Bloklanishlar')],
]

const when = (iso: string) =>
  new Date(iso).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'medium' })

export default function AuditPage() {
  const organizationId = useOrganizationId()
  const [action, setAction] = useState('')

  const params = action ? { action } : undefined
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.auditLogs(organizationId, params),
    queryFn: () => auditApi.list(params),
  })

  // Vendor kirishi ALOHIDA ko'rsatiladi, umumiy jurnalga qorishtirilmaydi:
  // "bizning ma'lumotimizga kim qaraydi?" — bu boshqacha savol va u
  // ko'zga tashlanib turishi kerak (ADR-10).
  const platformQuery = useQuery({
    queryKey: queryKeys.platformAccess(organizationId),
    queryFn: auditApi.platformAccess,
  })
  const platformRows = platformQuery.data?.items ?? []

  const rows = data?.items ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Audit jurnali')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t('Kim, nima va qachon — oʻzgartirib boʻlmaydigan yozuv.')}
        </p>
      </div>

      {/* Standalone o'rnatmada vendor tekisligi UMUMAN yo'q (ADR-13):
          tizim mijozning o'z serverida ishlaydi va unga kiradigan
          "provayder" degan tomon mavjud emas. Bo'limni qoldirish
          mijozda "demak kimdir kira oladi" degan noto'g'ri taassurot
          qoldirardi — aynan u sotib olmagan narsa haqida. */}
      {!env.isStandalone && (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-brand-600" />
            <h2 className="text-sm font-semibold text-slate-900">
              {t('Tizim provayderi kirishi')}
            </h2>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {t(
              'Radix CRM xodimlari sukut boʻyicha sizning maʼlumotingizni koʻrmaydi. Har qanday kirish vaqt bilan cheklanadi, sababi yoziladi va shu yerda koʻrinadi.',
            )}
          </p>

          {platformRows.length === 0 ? (
            <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {t('Hech qanday kirish qayd etilmagan.')}
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-slate-100 border-t border-slate-100">
              {platformRows.map((row) => (
                <li key={row.id} className="py-2.5 text-sm">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-medium text-slate-900">{row.actor_email}</span>
                    <span className="text-xs text-slate-400">{when(row.created_at)}</span>
                  </div>
                  {typeof row.changes?.reason === 'string' && (
                    <p className="mt-0.5 text-slate-600">
                      {t('Sabab: {reason}', { reason: row.changes.reason })}
                    </p>
                  )}
                  {typeof row.changes?.expires_at === 'string' && (
                    <p className="text-xs text-slate-400">
                      {t('Amal qiladi: {when} gacha', { when: when(row.changes.expires_at) })}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map(([key, label]) => (
          <button
            key={key || 'all'}
            type="button"
            onClick={() => setAction(key)}
            className={cn(
              'rounded-lg px-3 py-1.5 text-sm font-medium',
              action === key
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-600 hover:bg-slate-50',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">{t('Vaqt')}</th>
                <th className="px-4 py-3">{t('Kim')}</th>
                <th className="px-4 py-3">{t('Amal')}</th>
                <th className="px-4 py-3">{t('Obyekt')}</th>
                <th className="px-4 py-3">{t('Tafsilot')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((row) => {
                const [label, tone] = ACTION[row.action] ?? [
                  row.action,
                  'bg-slate-100 text-slate-600',
                ]
                const changes = Object.entries(row.changes ?? {})
                return (
                  <tr key={row.id} className="align-top">
                    <td className="whitespace-nowrap px-4 py-3 text-slate-500">
                      {when(row.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-900">{row.actor_name ?? '—'}</p>
                      <p className="text-xs text-slate-400">{row.actor_email || '—'}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', tone)}>
                        {label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      <p>{ENTITY[row.entity_type] ?? row.entity_type ?? '—'}</p>
                      {/* UUID emas, NOM (PLAN 4.4): "kim nima qildi?"
                          degan savolga javob shu ustunda boʻlishi
                          kerak, qidirishga yuboradigan havola emas. */}
                      {row.entity_label && (
                        <p className="text-xs text-slate-400">{row.entity_label}</p>
                      )}
                    </td>
                    <td className="max-w-sm px-4 py-3 text-xs text-slate-500">
                      {changes.length === 0
                        ? '—'
                        : changes
                            .map(([key, value]) => {
                              const label = FIELD[key] ?? key
                              const named = row.changes_labels?.[key]
                              return `${label}: ${named ?? fieldValue(value)}`
                            })
                            .join(' · ')}
                    </td>
                  </tr>
                )
              })}
              {!isLoading && rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-slate-400">
                    <ScrollText className="mx-auto mb-2 h-6 w-6" />
                    {t('Yozuv topilmadi.')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
