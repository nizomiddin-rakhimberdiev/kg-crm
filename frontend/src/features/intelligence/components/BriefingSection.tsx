/**
 * Dashboard'dagi "Radix AI · Kunlik brifing" bloki (docs/07 §11).
 *
 * Brifing saqlanmaydi: ochiq insight'lar + jonli tekshiruvlar bitta
 * so'rovda keladi. Ochiq signal yo'q va tekshiruv yo'q bo'lsa — bitta
 * qator, katta bo'sh karta emas.
 */

import { useQuery } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { branchesApi } from '@/features/branches/api'
import { insightsApi } from '@/features/intelligence/api'
import { getCopy } from '@/features/intelligence/content'
import { BriefingChecks } from '@/features/intelligence/components/BriefingChecks'
import { InsightCard } from '@/features/intelligence/components/InsightCard'
import { queryKeys } from '@/lib/api/queryKeys'
import { t } from '@/lib/i18n'

export function BriefingSection() {
  const copy = getCopy()
  const organizationId = useOrganizationId()
  const { user } = useAuth()

  const briefing = useQuery({
    queryKey: queryKeys.briefing(organizationId),
    queryFn: () => insightsApi.briefing(),
    staleTime: 60_000,
  })

  const data = briefing.data
  const byBranch = data?.checks.attendance_by_branch ?? {}
  // Egasi, filial tanlanmagan: kalitlar id — nomlar ro'yxatdan, faqat
  // birdan ko'p filial bo'lsa (bitta bo'lsa yorliq ortiqcha).
  const needsNames = !user?.branch && Object.keys(byBranch).length > 1
  const branches = useQuery({
    queryKey: queryKeys.branches(organizationId),
    queryFn: branchesApi.list,
    enabled: needsNames,
    staleTime: 300_000,
  })
  const branchNames = needsNames
    ? Object.fromEntries((branches.data?.items ?? []).map((b) => [b.id, b.name]))
    : undefined
  const hasChecks =
    !!data?.checks.attendance ||
    Object.values(data?.checks.attendance_by_branch ?? {}).some(Boolean)

  return (
    <section aria-labelledby="briefing-title" className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-50 text-brand-600">
          <Sparkles className="h-4 w-4" />
        </span>
        <h2 id="briefing-title" className="text-sm font-semibold text-slate-900">
          {copy.brand}
          <span className="font-normal text-slate-500"> · {copy.briefingTitle}</span>
        </h2>
        {data && data.open_count > 0 && (
          <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs font-semibold text-white">
            {data.open_count}
          </span>
        )}
        {/* Signallar kechasi hisoblanadi, dashboard esa jonli raqam
            ko'rsatadi. Auditda bitta ekranda ikkita raqam turgan va
            qaysi biri qachongi holat ekani ko'rinmasdi. */}
        {data?.generated_at && (
          <span className="num ml-auto text-xs text-slate-400">
            {t('holat {time}', {
              time: new Date(data.generated_at).toLocaleTimeString('uz-UZ', {
                hour: '2-digit',
                minute: '2-digit',
              }),
            })}
          </span>
        )}
      </div>

      {briefing.isError && (
        <p role="alert" className="text-sm text-red-600">
          {copy.loadError}
        </p>
      )}

      {data && data.insights.length === 0 && !hasChecks && (
        <p className="text-sm text-slate-500">{copy.noOpenInsights}</p>
      )}

      {data && (data.insights.length > 0 || hasChecks) && (
        // Signallar chapda, jonli tekshiruvlar o'ngda — ikkalasi bo'lsa
        // ikki ustun; biri bo'lmasa qolgani butun kenglikni oladi.
        <div
          className={
            data.insights.length > 0 && hasChecks
              ? 'grid gap-3 lg:grid-cols-2 lg:items-start'
              : 'grid gap-3'
          }
        >
          {data.insights.length > 0 && (
            <div className="space-y-3">
              {data.insights.map((insight) => (
                <InsightCard key={insight.id} insight={insight} />
              ))}
            </div>
          )}
          {hasChecks && <BriefingChecks checks={data.checks} branchNames={branchNames} />}
        </div>
      )}
    </section>
  )
}
