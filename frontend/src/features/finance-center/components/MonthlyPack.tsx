/**
 * Oylik moliyaviy hisobot paketi (Bosqich 13.5, brif §5.3, §8).
 *
 * Tuzilma har oy bir xil — 16 boʻlim. Raqamlar serverdagi bitta JSON'dan;
 * manbasi bor raqam bosilsa, uning yozuvlari ochiladi. Nusxa saqlangach,
 * keyingi oʻzgarish "oʻzgarish bor" boʻlib koʻrinadi va versiyalar farqi
 * raqamlar darajasida koʻrsatiladi.
 */

import { Fragment, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Download, FileText, Lock } from 'lucide-react'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { Modal } from '@/components/ui/Modal'
import { QueryError } from '@/components/ui/QueryError'
import { reportsApi, type PackSection, type PackUnit } from '@/features/dashboard/api'
import { branchesApi } from '@/features/branches/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { NetworkTable } from './NetworkTable'
import { ReviewPanel } from './ReviewPanel'
import { httpClient } from '@/lib/api/client'
import { ApiError } from '@/lib/api/types'
import { formatDate, som, today } from '@/lib/format'
import { t } from '@/lib/i18n'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { MonthInput } from '@/components/ui/MonthInput'

const HIDDEN = new Set(['key', 'title', 'id', 'source', 'link', 'subject', 'at', 'user_id'])
const NUMERIC = /^-?\d+(\.\d+)?$/

function cell(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string' && NUMERIC.test(value)) return som(value)
  if (typeof value === 'boolean') return value ? t('Ha') : t('Yoʻq')
  return String(value)
}

/** Har qanday boʻlimni koʻrsatadigan oddiy chizgich: jadval yoki kalit-qiymat. */
function Generic({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    if (value.length === 0) return <p className="text-sm text-slate-500">—</p>
    if (typeof value[0] !== 'object') {
      return (
        <ul className="list-disc space-y-0.5 pl-5 text-sm text-slate-700">
          {value.map((item, index) => (
            <li key={index}>{String(item)}</li>
          ))}
        </ul>
      )
    }
    const columns = Object.keys(value[0] as object).filter(
      (key) => !HIDDEN.has(key) && typeof (value[0] as Record<string, unknown>)[key] !== 'object',
    )
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              {columns.map((column) => (
                <th key={column} className="px-2 py-1 font-medium">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {value.map((row, index) => (
              <tr key={index}>
                {columns.map((column) => (
                  <td key={column} className="px-2 py-1 tabular-nums">
                    {cell((row as Record<string, unknown>)[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).filter(
      ([key]) => !HIDDEN.has(key),
    )
    return (
      <div className="space-y-2">
        <dl className="grid grid-cols-1 gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
          {entries
            .filter(([, item]) => typeof item !== 'object' || item === null)
            .map(([key, item]) => (
              <Fragment key={key}>
                <dt className="text-slate-500">{key}</dt>
                <dd className="tabular-nums text-slate-900 sm:text-right">{cell(item)}</dd>
              </Fragment>
            ))}
        </dl>
        {entries
          .filter(([, item]) => typeof item === 'object' && item !== null)
          .map(([key, item]) => (
            <div key={key}>
              <h4 className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {key}
              </h4>
              <Generic value={item} />
            </div>
          ))}
      </div>
    )
  }
  return <p className="text-sm">{cell(value)}</p>
}

interface ChainRow {
  id: string
  label: string
  value: string
  source?: string
}

function SourceModal({
  at,
  source,
  title,
  onClose,
}: {
  at: PackUnit
  source: string
  title: string
  onClose: () => void
}) {
  const organizationId = useOrganizationId()
  const rows = useQuery({
    queryKey: ['org', organizationId, 'reports', 'pack-source', at, source],
    queryFn: () => reportsApi.packSource(at, source),
  })
  return (
    <Modal open onClose={onClose} className="max-w-2xl">
      <div className="p-5">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        <div className="mt-3 max-h-[60vh] overflow-y-auto">
          <Generic value={rows.data?.rows ?? []} />
        </div>
      </div>
    </Modal>
  )
}

function Summary({ section }: { section: PackSection }) {
  const figures = (section.figures as Array<Record<string, string>>) ?? []
  const facts = (section.facts as string[]) ?? []
  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-3">
        {figures.map((figure) => (
          <div key={figure.id} className="rounded-xl bg-slate-50 px-3 py-2">
            <p className="text-xs text-slate-500">{figure.label}</p>
            <p className="text-lg font-bold tabular-nums text-slate-900">{cell(figure.value)}</p>
            {figure.delta !== undefined && figure.prev !== '0.00' && (
              <p
                className={cn(
                  'text-xs tabular-nums',
                  Number(figure.delta) < 0 ? 'text-red-700' : 'text-emerald-700',
                )}
              >
                {Number(figure.delta) > 0 ? '+' : ''}
                {cell(figure.delta)}
                {figure.delta_pct && ` (${figure.delta_pct}%)`}
              </p>
            )}
          </div>
        ))}
      </div>
      <ul className="list-disc space-y-0.5 pl-5 text-sm text-slate-700">
        {facts.map((fact) => (
          <li key={fact}>{fact}</li>
        ))}
      </ul>
    </div>
  )
}

function Revenue({
  section,
  onSource,
}: {
  section: PackSection
  onSource: (row: ChainRow) => void
}) {
  const chain = (section.chain as ChainRow[]) ?? []
  const factors = section.factors as { total_change: string; items: ChainRow[] }
  const kpi = section.kpi as Record<string, string | null>
  return (
    <div className="space-y-4">
      <ol className="space-y-1 text-sm">
        {chain.map((row) => (
          <li key={row.id} className="flex items-center justify-between gap-3">
            <span className="text-slate-600">{row.label}</span>
            {row.source ? (
              <button
                type="button"
                onClick={() => onSource(row)}
                className="font-semibold tabular-nums text-brand-700 underline-offset-2 hover:underline"
              >
                {cell(row.value)}
              </button>
            ) : (
              <span className="font-semibold tabular-nums">{cell(row.value)}</span>
            )}
          </li>
        ))}
      </ol>
      <dl className="grid grid-cols-3 gap-2 text-center text-sm">
        <div className="rounded-lg bg-slate-50 py-2">
          <dt className="text-xs text-slate-500">{t('Yigʻish darajasi')}</dt>
          <dd className="font-semibold">{kpi.collection_rate ?? '—'}%</dd>
        </div>
        <div className="rounded-lg bg-slate-50 py-2">
          <dt className="text-xs text-slate-500">{t('Imtiyoz ulushi')}</dt>
          <dd className="font-semibold">{kpi.benefit_share ?? '—'}%</dd>
        </div>
        <div className="rounded-lg bg-slate-50 py-2">
          <dt className="text-xs text-slate-500">{t('Bir boladan')}</dt>
          <dd className="font-semibold tabular-nums">{cell(kpi.average_per_child)}</dd>
        </div>
      </dl>
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('Oʻtgan oyga nisbatan farq: {money}', { money: cell(factors.total_change) })}
        </h4>
        <ul className="mt-1 space-y-0.5 text-sm">
          {factors.items.map((item) => (
            <li key={item.id} className="flex justify-between">
              <span className="text-slate-600">{item.label}</span>
              <span className="tabular-nums">{cell(item.value)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function Waterfall({ section }: { section: PackSection }) {
  const steps = (section.steps as ChainRow[]) ?? []
  const check = section.check as { ok: boolean }
  return (
    <div className="space-y-1 text-sm">
      {/* Oylik hisoblanmagan oyda foyda TAXMINIY (audit, 2026-10-30):
          raqam notoʻgʻri emas, lekin u boshqa savolga javob beradi —
          va buni ekran aytishi kerak. */}
      {section.payroll_estimated ? (
        <p className="mb-2 rounded-lg bg-orik-50 px-3 py-2 text-xs text-orik-800">
          {t('Bu oyning oyligi hali hisoblanmagan — foyda taxminiy.')}
        </p>
      ) : null}
      <p className="flex justify-between font-semibold">
        <span>{t('Operatsion foyda')}</span>
        <span className="tabular-nums">{cell(section.operating_profit)}</span>
      </p>
      {steps.map((step) => (
        <p key={step.id} className="flex justify-between">
          <span className="text-slate-600">{step.label}</span>
          <span className={cn('tabular-nums', Number(step.value) < 0 && 'text-red-700')}>
            {Number(step.value) > 0 ? '+' : ''}
            {cell(step.value)}
          </span>
        </p>
      ))}
      <p className="flex justify-between border-t border-slate-200 pt-1 font-semibold">
        <span>{t('Pul oʻzgarishi')}</span>
        <span className="tabular-nums">{cell(section.money_change)}</span>
      </p>
      {!check.ok && (
        <p className="text-xs text-red-700">{t('Koʻprik tutashmadi — maʼlumotni tekshiring.')}</p>
      )}
    </div>
  )
}

async function download(url: string, params: Record<string, unknown>, name: string) {
  const response = await httpClient.get(url, { params, responseType: 'blob' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(response.data as Blob)
  link.download = name
  link.click()
  URL.revokeObjectURL(link.href)
}

export function MonthlyPack() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const { can } = useCan()
  const [period, setPeriod] = useState(() => {
    const now = new Date(today())
    const previous = new Date(now.getFullYear(), now.getMonth() - 1, 1)
    return `${previous.getFullYear()}-${String(previous.getMonth() + 1).padStart(2, '0')}`
  })
  const [year, month] = period.split('-').map(Number)
  // Egasi yuqoridagi filial tanlovi bilan filial hisobotiga oʻtadi (C model);
  // boshqa rollarni backend oʻz filialiga bogʻlaydi.
  const { user } = useAuth()
  const { selectedBranchId } = useBranchScope()
  const at: PackUnit = { year, month, branch: selectedBranchId }
  const key = ['org', organizationId, 'reports', 'pack', period, selectedBranchId]
  const pack = useQuery({ queryKey: key, queryFn: () => reportsApi.pack(at) })
  const versions = useQuery({
    queryKey: [...key, 'versions'],
    queryFn: () => reportsApi.packVersions(at),
  })
  const [source, setSource] = useState<ChainRow | null>(null)
  const [diffFrom, setDiffFrom] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const diff = useQuery({
    queryKey: [...key, 'diff', diffFrom],
    queryFn: () => reportsApi.packDiff(at, diffFrom as number),
    enabled: diffFrom !== null,
  })
  const snapshot = useMutation({
    mutationFn: () => reportsApi.packSnapshot(at),
    onSuccess: () => {
      setError(null)
      void queryClient.invalidateQueries({ queryKey: key })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const data = pack.data
  // `#pack-pnl` kabi havola — paket yuklangach o'sha bo'limga (F2).
  const { hash } = useLocation()
  useEffect(() => {
    if (!data || !hash.startsWith('#pack-')) return
    document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' })
  }, [data, hash])
  const params = { year, month, ...(selectedBranchId ? { branch: selectedBranchId } : {}) }
  const isOwner = user?.role?.code === 'org_owner'
  const branches = useQuery({
    queryKey: queryKeys.branches(organizationId),
    queryFn: branchesApi.list,
    enabled: isOwner,
  })
  const network = isOwner && !selectedBranchId && (branches.data?.items.length ?? 0) > 1

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <MonthInput id="pack-month" label={t('Oy')} value={period} onChange={setPeriod} />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void download('/reports/pack/pdf', params, `hisobot-${period}.pdf`)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <FileText className="h-4 w-4" />
            PDF
          </button>
          <button
            type="button"
            onClick={() => void download('/reports/pack/xlsx', params, `hisobot-${period}.xlsx`)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-4 w-4" />
            Excel
          </button>
          {can('reports.approve') && (
            <button
              type="button"
              disabled={snapshot.isPending}
              onClick={() => snapshot.mutate()}
              className="flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              <Lock className="h-4 w-4" />
              {t('Oʻzgarmas nusxani saqlash')}
            </button>
          )}
        </div>
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {data?.changed_since_snapshot && (
        <p className="flex items-center gap-2 rounded-lg bg-orik-50 px-3 py-2 text-sm text-orik-800">
          <AlertTriangle className="h-4 w-4" />
          {t('Oʻzgarish bor: {v}-versiyadan keyin maʼlumot oʻzgardi.', {
            v: data.latest_version ?? 0,
          })}
          <button
            type="button"
            onClick={() => setDiffFrom(data.latest_version)}
            className="ml-auto font-medium underline"
          >
            {t('Farqni koʻrish')}
          </button>
        </p>
      )}

      {(versions.data ?? []).length > 0 && (
        <details className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm">
          <summary className="cursor-pointer font-medium text-slate-700">
            {t('Versiyalar — {n}', { n: versions.data?.length ?? 0 })}
          </summary>
          <ul className="mt-2 space-y-1">
            {(versions.data ?? []).map((row) => (
              <li key={row.version} className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  v{row.version} · {formatDate(row.created_at)} · {row.created_by}
                  <span className="ml-1 font-mono text-xs text-slate-400">
                    {row.checksum.slice(0, 10)}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => setDiffFrom(row.version)}
                  className="text-xs font-medium text-brand-700"
                >
                  {t('Hozirgisi bilan farq')}
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}

      {diffFrom !== null && diff.data && (
        <Modal open onClose={() => setDiffFrom(null)} className="max-w-2xl">
          <div className="p-5">
            <h2 className="text-base font-semibold text-slate-900">
              {t('v{v} bilan farq — {n} ta raqam', { v: diffFrom, n: diff.data.changes.length })}
            </h2>
            <div className="mt-3 max-h-[60vh] overflow-y-auto">
              <Generic value={diff.data.changes} />
            </div>
          </div>
        </Modal>
      )}

      <ReviewPanel at={at} />
      {network && <NetworkTable year={year} month={month} />}

      {pack.isError && <QueryError error={pack.error} onRetry={() => void pack.refetch()} />}

      {data?.sections.map((section, index) => (
        <section
          key={section.key}
          id={`pack-${section.key}`}
          className="scroll-mt-4 rounded-2xl border border-slate-200 bg-white p-4"
        >
          <h3 className="mb-3 text-sm font-semibold text-slate-900">
            {index + 1}. {section.title}
          </h3>
          {section.key === 'summary' ? (
            <Summary section={section} />
          ) : section.key === 'revenue' ? (
            <Revenue section={section} onSource={setSource} />
          ) : section.key === 'profit_vs_cash' ? (
            <Waterfall section={section} />
          ) : (
            <Generic value={section} />
          )}
        </section>
      ))}

      {source && source.source && (
        <SourceModal
          at={at}
          source={source.source}
          title={source.label}
          onClose={() => setSource(null)}
        />
      )}
    </div>
  )
}
