/**
 * Ota-onaga yillik toʻlovlar maʼlumotnomasi (Bosqich 13.8, brif §9).
 *
 * JShDS imtiyozi uchun: har oy toʻlangani, qaytarilgani va limit ichidagi
 * qismi, toʻlovchi ish beruvchi boʻlsa — nomi va STIR. PDF serverda chiqadi.
 */

import { useState } from 'react'
import { FileDown } from 'lucide-react'
import { httpClient } from '@/lib/api/client'
import { today } from '@/lib/format'
import { t } from '@/lib/i18n'

export function AnnualStatementButton({ childId }: { childId: string }) {
  const current = new Date(today()).getFullYear()
  // Joriy yil — sukut (audit, 2026-10-21). Ilgari o'tgan yil turardi va
  // 2026 yilda so'rangan ma'lumotnoma jimgina 2025 uchun chiqardi.
  const [year, setYear] = useState(current)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const download = async () => {
    setBusy(true)
    setError(null)
    try {
      const response = await httpClient.get(`/children/${childId}/annual-statement`, {
        params: { year },
        responseType: 'blob',
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(response.data as Blob)
      link.download = `malumotnoma-${year}.pdf`
      link.click()
      URL.revokeObjectURL(link.href)
    } catch {
      setError(t('Maʼlumotnomani yuklab boʻlmadi.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div>
        <label htmlFor="statement-year" className="mb-1 block text-xs font-medium text-slate-600">
          {t('Yillik maʼlumotnoma')}
        </label>
        <select
          id="statement-year"
          value={year}
          onChange={(event) => setYear(Number(event.target.value))}
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500"
        >
          {[current, current - 1, current - 2].map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </div>
      <button
        type="button"
        disabled={busy}
        onClick={() => void download()}
        className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
      >
        <FileDown className="h-4 w-4" aria-hidden />
        PDF
      </button>
      {error && (
        <p role="alert" className="w-full text-xs text-red-700">
          {error}
        </p>
      )}
    </div>
  )
}
