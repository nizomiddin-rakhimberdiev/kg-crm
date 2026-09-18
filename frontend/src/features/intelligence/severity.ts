/**
 * `evidence` dan "nega jiddiy" ni o'qish — bashorat emas, qoida qaysi
 * chegaradan oshganini aytish (docs/07 §4, §7).
 */

import type { InsightSeverity, PaymentDelayEvidence } from '@/lib/api/types'

export type SeverityReason = 'days' | 'count' | 'both' | 'none'

export function paymentDelayReason(
  evidence: PaymentDelayEvidence,
  severity: InsightSeverity,
): SeverityReason {
  if (severity !== 'critical') return 'none'
  const byDays = evidence.max_days_overdue >= evidence.critical_days_threshold
  const byCount = evidence.children_count >= evidence.critical_children_threshold
  if (byDays && byCount) return 'both'
  if (byDays) return 'days'
  if (byCount) return 'count'
  // Backend bilan mos kelmagan holat — yolg'on sabab yozmaymiz.
  return 'none'
}

export function isPaymentDelayEvidence(value: unknown): value is PaymentDelayEvidence {
  if (!value || typeof value !== 'object') return false
  const e = value as Record<string, unknown>
  return (
    typeof e.children_count === 'number' &&
    typeof e.max_days_overdue === 'number' &&
    typeof e.overdue_days_threshold === 'number' &&
    Array.isArray(e.children)
  )
}
