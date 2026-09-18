/**
 * Jonli tekshiruvlar (docs/07 §11) — saqlanmaydi, har so'rovda hisoblanadi.
 *
 * Davomat to'liqligi BOLA darajasida: `recorded / expected`. Guruhda
 * "bitta yozuv bor" — to'liq emas. Ish kuni bo'lmasa yoki faol bola
 * bo'lmasa backend `null` beradi va tekshiruv umuman ko'rsatilmaydi.
 */

import { CalendarCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ProgressBar } from '@/components/ui/primitives'
import { fill, getCopy } from '@/features/intelligence/content'
import type { AttendanceCheck, Briefing } from '@/lib/api/types'

interface BriefingChecksProps {
  checks: Briefing['checks']
  /** Egasi uchun filial nomlari — `attendance_by_branch` kalitlari id. */
  branchNames?: Record<string, string>
}

function AttendanceRow({ check, label }: { check: AttendanceCheck; label?: string }) {
  const copy = getCopy()
  const tone = check.complete ? 'success' : check.percent >= 50 ? 'warning' : 'danger'
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
      <div className="flex items-center gap-2">
        <CalendarCheck className="h-4 w-4 shrink-0 text-teal-600" />
        <p className="text-sm font-semibold text-slate-900">
          {copy.checks.attendanceTitle}
          {label ? <span className="font-normal text-slate-500"> · {label}</span> : null}
        </p>
        <span className="ml-auto text-sm font-bold tabular-nums text-slate-900">
          {check.percent}%
        </span>
      </div>
      <ProgressBar value={check.percent} tone={tone} className="mt-3" />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs">
        <span className="text-slate-600">{fill(copy.checks.attendanceBody, { ...check })}</span>
        <span className={check.complete ? 'text-emerald-700' : 'text-amber-700'}>
          {check.complete
            ? copy.checks.attendanceComplete
            : fill(copy.checks.attendanceIncomplete, {
                missing: check.expected - check.recorded,
              })}
        </span>
      </div>
      {!check.complete && (
        <Link
          to="/attendance"
          className="mt-3 inline-flex min-h-11 items-center text-sm font-medium text-brand-600 hover:text-brand-700"
        >
          {copy.checks.open} →
        </Link>
      )}
    </div>
  )
}

export function BriefingChecks({ checks, branchNames }: BriefingChecksProps) {
  const rows: { key: string; check: AttendanceCheck; label?: string }[] = []
  if (checks.attendance) rows.push({ key: 'branch', check: checks.attendance })
  for (const [branchId, check] of Object.entries(checks.attendance_by_branch ?? {})) {
    if (check) rows.push({ key: branchId, check, label: branchNames?.[branchId] })
  }
  if (rows.length === 0) return null
  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <AttendanceRow key={row.key} check={row.check} label={row.label} />
      ))}
    </div>
  )
}
