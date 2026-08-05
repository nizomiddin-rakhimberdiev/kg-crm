/**
 * Berilgan kirish ruxsatlari.
 *
 * Bu ro'yxat vendorning O'ZI uchun ham nazorat: kim, qachon, qaysi
 * mijozga va nima sababdan kirgan. Xuddi shu yozuvlar mijozning audit
 * jurnalida ham ko'rinadi (ADR-10) — ya'ni bu ro'yxatni "tozalab
 * qo'yish" mumkin emas.
 */

import { useQuery } from '@tanstack/react-query'
import { KeyRound } from 'lucide-react'
import { cn } from '@/lib/utils'
import { platform } from '../api'

const when = (iso: string) =>
  new Date(iso).toLocaleString('uz-UZ', { dateStyle: 'short', timeStyle: 'short' })

export default function PlatformGrantsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['platform', 'grants'],
    queryFn: platform.supportGrants,
  })

  const rows = data ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Kirish ruxsatlari</h1>
        <p className="mt-1 text-sm text-slate-400">
          Har bir ruxsat mijozning audit jurnalida ham ko'rinadi.
        </p>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Bog'cha</th>
              <th className="px-4 py-3">Kim</th>
              <th className="px-4 py-3">Sabab</th>
              <th className="px-4 py-3">Berilgan</th>
              <th className="px-4 py-3">Tugaydi</th>
              <th className="px-4 py-3">Holat</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900/40">
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="px-4 py-3 font-medium">{row.organization_name}</td>
                <td className="px-4 py-3 text-slate-400">{row.platform_email}</td>
                <td className="max-w-sm px-4 py-3 text-slate-300">{row.reason}</td>
                <td className="px-4 py-3 text-slate-400">{when(row.created_at)}</td>
                <td className="px-4 py-3 text-slate-400">{when(row.expires_at)}</td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      'rounded-full px-2 py-0.5 text-xs font-medium',
                      row.is_active
                        ? 'bg-amber-500/10 text-amber-400'
                        : 'bg-slate-700/40 text-slate-400',
                    )}
                  >
                    {row.is_active ? 'Faol' : row.revoked_at ? 'Bekor qilingan' : 'Tugagan'}
                  </span>
                </td>
              </tr>
            ))}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-slate-500">
                  <KeyRound className="mx-auto mb-2 h-6 w-6" />
                  Hech qanday ruxsat berilmagan.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
