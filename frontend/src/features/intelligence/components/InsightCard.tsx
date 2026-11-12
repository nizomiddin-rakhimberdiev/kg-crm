/**
 * Insight kartasi (docs/07 §7, §8, §9).
 *
 * Har bir kartada MAJBURIY to'rt narsa: signal (sarlavha), darajasi,
 * dalil ("Nega?") va tavsiya + deep link. Til — fakt: raqamdan tuzilgan
 * jumla, bashorat yo'q.
 *
 * `new` karta birinchi ko'rsatilganda `seen` bo'ladi — backend'da
 * idempotent, StrictMode'ning ikki marta ishga tushishi zararsiz.
 */

import { useEffect, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, CheckCircle2, Clock, HelpCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { Badge, Button } from '@/components/ui/primitives'
import { insightsApi } from '@/features/intelligence/api'
import { fill, getCopy } from '@/features/intelligence/content'
import { WhyPanel } from '@/features/intelligence/components/WhyPanel'
import { isPaymentDelayEvidence } from '@/features/intelligence/severity'
import { ApiError } from '@/lib/api/types'
import type { Insight } from '@/lib/api/types'
import { useCan } from '@/lib/rbac/useCan'
import { cn, formatUZS } from '@/lib/utils'
import { t } from '@/lib/i18n'
import { formatDate } from '@/lib/format'

interface InsightCardProps {
  insight: Insight
}

const stripe: Record<Insight['severity'], string> = {
  critical: 'border-l-red-500',
  warning: 'border-l-amber-400',
}

export function InsightCard({ insight }: InsightCardProps) {
  const copy = getCopy()
  const { can } = useCan()
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const [why, setWhy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const evidence = isPaymentDelayEvidence(insight.evidence) ? insight.evidence : null

  const invalidate = () =>
    queryClient.invalidateQueries({
      queryKey: ['org', organizationId, 'insights'],
    })

  const seen = useMutation({
    mutationFn: (id: string) => insightsApi.seen(id),
    onSuccess: invalidate,
  })
  const resolve = useMutation({
    mutationFn: (id: string) => insightsApi.resolve(id),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })
  const dismiss = useMutation({
    mutationFn: (id: string) => insightsApi.dismiss(id),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const canAct = can('dashboard.update')
  const busy = resolve.isPending || dismiss.isPending

  useEffect(() => {
    if (insight.status === 'new' && canAct && !seen.isPending && !seen.isSuccess) {
      seen.mutate(insight.id)
    }
    // Faqat id/holat o'zgarsa — mutatsiya obyekti har renderda yangi.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [insight.id, insight.status, canAct])

  if (!evidence) return null // noma'lum evidence versiyasi — jim, yolg'on emas

  const title = fill(copy.titles[insight.type], evidence)
  const recommendation = copy.recommendations[insight.recommendation_key]

  return (
    <article
      data-testid="insight-card"
      className={cn(
        'rounded-2xl border border-slate-200 border-l-4 bg-white p-4 shadow-card sm:p-5',
        stripe[insight.severity],
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={insight.severity === 'critical' ? 'danger' : 'warning'} dot>
          {copy.severity[insight.severity]}
        </Badge>
        {insight.status === 'new' && <Badge tone="info">{copy.statusNew}</Badge>}
        <span className="ml-auto text-xs text-slate-500">{formatDate(evidence.as_of)}</span>
      </div>

      <h3 className="mt-3 text-base font-semibold leading-snug text-slate-900 [text-wrap:balance]">
        {title}
      </h3>

      {/* 375px da uch ustun bir-birining ustiga chiqardi (audit 2026-11-12, H9). */}
      <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-slate-500">{copy.facts.totalOverdue}</dt>
          <dd className="font-semibold tabular-nums text-slate-900">
            {formatUZS(Number(evidence.total_overdue))}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">{copy.facts.maxDays}</dt>
          <dd className="font-semibold tabular-nums text-slate-900">
            {evidence.max_days_overdue} {copy.facts.dayUnit}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">{copy.facts.children}</dt>
          <dd className="font-semibold tabular-nums text-slate-900">
            {evidence.children_count}{' '}
            <span className="text-xs font-normal text-slate-500">
              {fill(copy.facts.ofActive, evidence)}
            </span>
          </dd>
        </div>
      </dl>

      {recommendation && <p className="mt-3 text-sm text-slate-600">{recommendation}</p>}

      {error && (
        <p role="alert" className="mt-3 text-sm text-red-600">
          {error}
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          icon={HelpCircle}
          onClick={() => setWhy(true)}
          className="min-h-11"
        >
          {copy.actions.why}
        </Button>
        <Link
          to={insight.deep_link}
          className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
        >
          {copy.actions.open}
          <ArrowRight className="h-4 w-4" />
        </Link>
        {canAct && (
          <div className="ml-auto flex gap-1">
            <Button
              variant="ghost"
              icon={CheckCircle2}
              disabled={busy}
              onClick={() => resolve.mutate(insight.id)}
              className="min-h-11"
            >
              {copy.actions.resolve}
            </Button>
            <Button
              variant="ghost"
              icon={Clock}
              disabled={busy}
              onClick={() => dismiss.mutate(insight.id)}
              className="min-h-11"
            >
              {copy.actions.dismiss}
            </Button>
          </div>
        )}
      </div>

      {why && <WhyPanel insight={insight} evidence={evidence} onClose={() => setWhy(false)} />}
    </article>
  )
}
