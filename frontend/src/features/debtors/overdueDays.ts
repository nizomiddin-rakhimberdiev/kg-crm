/**
 * `?overdue_days=N` — Radix AI deep link'i uchun sof yordamchilar (docs/07 §8).
 *
 * Filtr mijoz tomonida: backend `/debtors?overdue=true` faqat "muddati
 * o'tgan" ni biladi. Ro'yxat jonli — snapshot'dan farq qilishi mumkin va
 * bu sahifada shunday deb aytiladi.
 */

import type { DebtorRow } from '@/lib/api/types'

const MAX_DAYS = 3650

export function overdueDaysFromSearch(params: URLSearchParams): number | null {
  const raw = params.get('overdue_days')
  if (raw === null || raw === '') return null
  const value = Number(raw)
  if (!Number.isInteger(value) || value < 0 || value > MAX_DAYS) return null
  return value
}

/** `oldest_overdue_date` ≤ bugun − N kun bo'lgan qatorlar. `null` — filtr yo'q. */
export function filterByOverdueDays(
  rows: DebtorRow[],
  overdueDays: number | null,
  today: Date,
): DebtorRow[] {
  if (overdueDays === null) return rows
  const cutoff = new Date(today)
  cutoff.setHours(0, 0, 0, 0)
  cutoff.setDate(cutoff.getDate() - overdueDays)
  // `toISOString()` UTC'ga o'giradi va Toshkentda kunni bir kun orqaga
  // surardi — sana mahalliy qismlardan yig'iladi.
  const cutoffIso = [
    cutoff.getFullYear(),
    String(cutoff.getMonth() + 1).padStart(2, '0'),
    String(cutoff.getDate()).padStart(2, '0'),
  ].join('-')
  return rows.filter(
    (row) => row.oldest_overdue_date !== null && row.oldest_overdue_date < cutoffIso,
  )
}
