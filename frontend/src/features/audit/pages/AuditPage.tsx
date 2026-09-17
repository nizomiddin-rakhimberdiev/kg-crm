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

const ACTION: Record<string, [string, string]> = {
  login: ['Kirish', 'bg-slate-100 text-slate-600'],
  login_failed: ['Kirish urinishi', 'bg-amber-50 text-amber-700'],
  logout: ['Chiqish', 'bg-slate-100 text-slate-600'],
  signup: ["Ro'yxatdan o'tish", 'bg-sky-50 text-sky-700'],
  password_change: ["Parol o'zgardi", 'bg-amber-50 text-amber-700'],
  create: ['Yaratildi', 'bg-emerald-50 text-emerald-700'],
  update: ['Yangilandi', 'bg-sky-50 text-sky-700'],
  delete: ["O'chirildi", 'bg-red-50 text-red-700'],
}

const ENTITY: Record<string, string> = {
  child: 'Bola',
  child_import: 'Bolalar importi',
  payment: "To'lov",
  invoice: 'Hisob-faktura',
  invoice_run: 'Hisob-faktura generatsiyasi',
  discount: 'Chegirma',
  expense: 'Chiqim',
  stock_movement: 'Stok harakati',
  system_setting: 'Sozlama',
  user: 'Foydalanuvchi',
  role: 'Rol',
  branch: 'Filial',
  organization: 'Tashkilot',
  payroll_run: 'Oylik hisoblash',
}

const FILTERS: Array<[string, string]> = [
  ['', 'Hammasi'],
  ['create', 'Yaratish'],
  ['update', 'Yangilash'],
  ['delete', "O'chirish"],
  ['login_failed', 'Kirish urinishlari'],
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
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Audit jurnali</h1>
        <p className="mt-1 text-sm text-slate-500">
          Kim, nima va qachon — o'zgartirib bo'lmaydigan yozuv.
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
          <h2 className="text-sm font-semibold text-slate-900">Tizim provayderi kirishi</h2>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          Radix CRM xodimlari sukut bo'yicha sizning ma'lumotingizni ko'rmaydi. Har qanday kirish
          vaqt bilan cheklanadi, sababi yoziladi va shu yerda ko'rinadi.
        </p>

        {platformRows.length === 0 ? (
          <p className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            Hech qanday kirish qayd etilmagan.
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
                  <p className="mt-0.5 text-slate-600">Sabab: {row.changes.reason}</p>
                )}
                {typeof row.changes?.expires_at === 'string' && (
                  <p className="text-xs text-slate-400">
                    Amal qiladi: {when(row.changes.expires_at)} gacha
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
              action === key ? 'bg-slate-900 text-white' : 'bg-white text-slate-600 hover:bg-slate-50',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Vaqt</th>
              <th className="px-4 py-3">Kim</th>
              <th className="px-4 py-3">Amal</th>
              <th className="px-4 py-3">Obyekt</th>
              <th className="px-4 py-3">Tafsilot</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => {
              const [label, tone] = ACTION[row.action] ?? [row.action, 'bg-slate-100 text-slate-600']
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
                    {ENTITY[row.entity_type] ?? row.entity_type ?? '—'}
                  </td>
                  <td className="max-w-sm px-4 py-3 text-xs text-slate-500">
                    {changes.length === 0
                      ? '—'
                      : changes
                          .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
                          .join(', ')}
                  </td>
                </tr>
              )
            })}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-slate-400">
                  <ScrollText className="mx-auto mb-2 h-6 w-6" />
                  Yozuv topilmadi.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
