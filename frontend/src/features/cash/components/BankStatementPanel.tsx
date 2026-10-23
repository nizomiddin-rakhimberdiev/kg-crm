/**
 * Bank koʻchirmasi (Bosqich 13.3d): fayl → ustunlarni moslashtirish →
 * avtomatik bogʻlash → moslashtirilmagan qatorlar navbati.
 *
 * Har bank boshqacha eksport qiladi, shuning uchun ustunlarni odam
 * tanlaydi (sarlavha nomlariga qarab taklif qilinadi). Bir faylni ikki
 * marta yuklash zararsiz — takror qatorlar oʻtkazib yuboriladi.
 */

import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileSpreadsheet } from 'lucide-react'
import { useOrganizationId } from '@/app/providers/AuthProvider'
import { cashApi, type StatementLine, type StatementMapping } from '@/features/cash/api'
import { childrenApi } from '@/features/children/api'
import { expensesApi } from '@/features/expenses/api'
import { invalidateMoney } from '@/lib/api/invalidate'
import { ApiError } from '@/lib/api/types'
import { formatDate, money, som } from '@/lib/format'
import { t } from '@/lib/i18n'
import { cn } from '@/lib/utils'
import { Select } from '@/components/ui/Select'

const field =
  'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500'
const label = 'mb-1 block text-xs font-medium text-slate-600'

const FIELDS: Array<{ key: keyof StatementMapping; label: string; guess: RegExp }> = [
  { key: 'date', label: t('Sana'), guess: /sana|дата|date/i },
  { key: 'credit', label: t('Kirim (kredit)'), guess: /kredit|кредит|credit|kirim|приход/i },
  { key: 'debit', label: t('Chiqim (debet)'), guess: /debet|дебет|debit|chiqim|расход/i },
  { key: 'amount', label: t('Summa (± bitta ustun)'), guess: /^summa$|^сумма$|^amount$/i },
  {
    key: 'purpose',
    label: t('Toʻlov maqsadi'),
    guess: /maqsad|назначени|purpose|izoh|tafsilot/i,
  },
  { key: 'counterparty', label: t('Kontragent'), guess: /kontragent|контрагент|counterpart|nomi/i },
  { key: 'reference', label: t('Hujjat raqami'), guess: /№|номер|hujjat|doc|reference/i },
]

function guess(headers: string[]): StatementMapping {
  const mapping: StatementMapping = {}
  for (const item of FIELDS) {
    const found = headers.find((header) => item.guess.test(header))
    if (found) mapping[item.key] = found
  }
  if (mapping.credit || mapping.debit) delete mapping.amount
  return mapping
}

function QueueRow({ line, onDone }: { line: StatementLine; onDone: () => void }) {
  const organizationId = useOrganizationId()
  const [mode, setMode] = useState<'' | 'ignore' | 'expense' | 'payment'>('')
  const [value, setValue] = useState('')
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)
  const categories = useQuery({
    queryKey: ['org', organizationId, 'expenses', 'categories', 'recent'],
    queryFn: expensesApi.recentCategories,
    enabled: mode === 'expense',
  })
  const children = useQuery({
    queryKey: ['org', organizationId, 'children', 'search', search],
    queryFn: () => childrenApi.list({ search, page_size: 20 }),
    enabled: mode === 'payment' && search.trim().length >= 2,
  })
  const act = useMutation({
    mutationFn: () =>
      mode === 'ignore'
        ? cashApi.ignoreLine(line.id, value)
        : mode === 'expense'
          ? cashApi.lineToExpense(line.id, value)
          : cashApi.lineToPayment(line.id, value),
    onSuccess: onDone,
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  return (
    <li className="py-2.5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <span className="min-w-0 flex-1">
          <span className="block text-sm text-slate-700">
            {line.purpose || line.counterparty || '—'}
          </span>
          <span className="text-xs text-slate-500">
            {formatDate(line.booked_on)}
            {line.counterparty && ` · ${line.counterparty}`}
          </span>
        </span>
        <span
          className={cn(
            'font-semibold tabular-nums',
            line.direction === 'in' ? 'text-emerald-700' : 'text-slate-900',
          )}
        >
          {line.direction === 'in' ? '+' : '−'}
          {som(line.amount)}
        </span>
      </div>
      {!mode ? (
        <div className="mt-1.5 flex flex-wrap gap-3 text-xs font-medium">
          {line.direction === 'out' ? (
            <button type="button" className="text-brand-700" onClick={() => setMode('expense')}>
              {t('Xarajat qilish')}
            </button>
          ) : (
            <button type="button" className="text-brand-700" onClick={() => setMode('payment')}>
              {t('Bola toʻlovi')}
            </button>
          )}
          <button type="button" className="text-slate-600" onClick={() => setMode('ignore')}>
            {t('Eʼtiborsiz qoldirish')}
          </button>
        </div>
      ) : (
        <form
          className="mt-2 flex flex-wrap items-end gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            if (value) act.mutate()
          }}
        >
          {mode === 'ignore' && (
            <input
              aria-label={t('Sabab (majburiy)')}
              placeholder={t('Sabab (majburiy)')}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              className={cn(field, 'flex-1')}
            />
          )}
          {mode === 'expense' && (
            <Select
              aria-label={t('Toifa')}
              value={value}
              onChange={(event) => setValue(event.target.value)}
              className="flex-1"
            >
              <option value="">{t('Toifani tanlang')}</option>
              {(categories.data?.items ?? []).map((category) => (
                <option key={category.id} value={category.id}>
                  {category.parent_name ? `${category.parent_name} · ` : ''}
                  {category.name}
                </option>
              ))}
            </Select>
          )}
          {mode === 'payment' && (
            <span className="flex flex-1 flex-col gap-1.5">
              <input
                aria-label={t('Bolani qidirish')}
                placeholder={t('Bolani qidirish')}
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className={field}
              />
              <Select
                aria-label={t('Bola')}
                value={value}
                onChange={(event) => setValue(event.target.value)}
                className="mt-1"
              >
                <option value="">{t('Bolani tanlang')}</option>
                {(children.data?.items ?? []).map((child) => (
                  <option key={child.id} value={child.id}>
                    {child.full_name}
                  </option>
                ))}
              </Select>
            </span>
          )}
          <button
            type="submit"
            disabled={!value || act.isPending}
            className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {t('Saqlash')}
          </button>
          <button
            type="button"
            className="px-2 py-2 text-sm text-slate-600"
            onClick={() => setMode('')}
          >
            {t('Bekor qilish')}
          </button>
        </form>
      )}
      {error && (
        <p role="alert" className="mt-1 text-xs text-red-700">
          {error}
        </p>
      )}
    </li>
  )
}

export function BankStatementPanel() {
  const organizationId = useOrganizationId()
  const queryClient = useQueryClient()
  const accounts = useQuery({
    queryKey: ['org', organizationId, 'cash', 'accounts'],
    queryFn: cashApi.accounts,
  })
  const banks = (accounts.data?.items ?? []).filter((a) => a.is_active && a.kind === 'bank')
  const queue = useQuery({
    queryKey: ['org', organizationId, 'cash', 'statement-queue'],
    queryFn: cashApi.unmatchedLines,
  })

  const [file, setFile] = useState<File | null>(null)
  const [headers, setHeaders] = useState<string[]>([])
  const [sample, setSample] = useState<string[][]>([])
  const [mapping, setMapping] = useState<StatementMapping>({})
  const [bankId, setBankId] = useState('')
  const [closing, setClosing] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)
  const bank = bankId || banks[0]?.id || ''

  const preview = useMutation({
    mutationFn: (target: File) => cashApi.statementPreview(target),
    onSuccess: (data) => {
      setHeaders(data.headers)
      setSample(data.sample)
      setMapping(guess(data.headers))
      setError(null)
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })
  const upload = useMutation({
    mutationFn: () =>
      cashApi.importStatement({
        file: file as File,
        cash_account_id: bank,
        mapping,
        ...(closing ? { closing_balance: closing } : {}),
      }),
    onSuccess: (data) => {
      setResult(
        t('{lines} qator: {matched} tasi bogʻlandi, {queue} tasi navbatda, {skipped} takror.', {
          lines: data.line_count,
          matched: data.matched_count,
          queue: data.unmatched_count,
          skipped: data.skipped_count,
        }) +
          (data.balance_difference && Number(data.balance_difference) !== 0
            ? ` ${t('Qoldiq farqi: {money}', { money: som(data.balance_difference) })}`
            : ''),
      )
      setFile(null)
      setHeaders([])
      invalidateMoney(queryClient, organizationId)
      void queryClient.invalidateQueries({ queryKey: ['org', organizationId, 'cash'] })
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : t('Xatolik yuz berdi.')),
  })

  const canImport = useMemo(
    () =>
      Boolean(file && bank && mapping.date && (mapping.amount || mapping.credit || mapping.debit)),
    [file, bank, mapping],
  )
  const lines = queue.data ?? []

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
        <FileSpreadsheet className="h-4 w-4 text-slate-500" />
        {t('Bank koʻchirmasi')}
      </h2>
      <p className="mt-0.5 text-xs text-slate-500">
        {t(
          'Bank-klientdan Excel yoki CSV. Toʻlovlar, Click/Payme tushumlari va xarajatlar oʻzi bogʻlanadi.',
        )}
      </p>

      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      {result && (
        <p className="mt-2 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{result}</p>
      )}

      <label className="mt-3 inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
        {file ? file.name : t('Faylni tanlang')}
        <input
          type="file"
          accept=".xlsx,.csv,.txt"
          className="sr-only"
          onChange={(event) => {
            const picked = event.target.files?.[0] ?? null
            setFile(picked)
            setResult(null)
            if (picked) preview.mutate(picked)
          }}
        />
      </label>

      {headers.length > 0 && (
        <form
          className="mt-3 grid gap-2 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault()
            if (canImport) upload.mutate()
          }}
        >
          {banks.length > 1 && (
            <div className="sm:col-span-2">
              <label htmlFor="st-bank" className={label}>
                {t('Bank hisobi')}
              </label>
              <Select
                id="st-bank"
                value={bank}
                onChange={(event) => setBankId(event.target.value)}
                className="mt-1"
              >
                {banks.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </Select>
            </div>
          )}
          {FIELDS.map((item) => (
            <div key={item.key}>
              <label htmlFor={`st-${item.key}`} className={label}>
                {item.label}
              </label>
              <Select
                id={`st-${item.key}`}
                value={mapping[item.key] ?? ''}
                onChange={(event) =>
                  setMapping((prev) => ({ ...prev, [item.key]: event.target.value || undefined }))
                }
                className="mt-1"
              >
                <option value="">—</option>
                {headers.map((header) => (
                  <option key={header} value={header}>
                    {header}
                  </option>
                ))}
              </Select>
            </div>
          ))}
          <div>
            <label htmlFor="st-closing" className={label}>
              {t('Koʻchirmadagi yakuniy qoldiq')}
            </label>
            <input
              id="st-closing"
              inputMode="numeric"
              value={closing ? money(Number(closing)) : ''}
              onChange={(event) => setClosing(event.target.value.replace(/\D/g, ''))}
              className={field}
            />
          </div>
          {sample.length > 0 && (
            <div className="overflow-x-auto sm:col-span-2">
              <table className="w-full text-xs text-slate-600">
                <thead>
                  <tr>
                    {headers.map((header) => (
                      <th key={header} className="px-2 py-1 text-left font-medium">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sample.map((row, index) => (
                    <tr key={index} className="border-t border-slate-100">
                      {row.map((cell, cellIndex) => (
                        <td key={cellIndex} className="px-2 py-1">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex justify-end sm:col-span-2">
            <button
              type="submit"
              disabled={!canImport || upload.isPending}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {upload.isPending ? t('Yuklanmoqda…') : t('Yuklash va bogʻlash')}
            </button>
          </div>
        </form>
      )}

      {lines.length > 0 && (
        <div className="mt-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('Moslashtirilmagan qatorlar — {n}', { n: lines.length })}
          </h3>
          <ul className="mt-1 divide-y divide-slate-100">
            {lines.map((line) => (
              <QueueRow
                key={line.id}
                line={line}
                onDone={() => {
                  invalidateMoney(queryClient, organizationId)
                  void queryClient.invalidateQueries({
                    queryKey: ['org', organizationId, 'cash', 'statement-queue'],
                  })
                }}
              />
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
