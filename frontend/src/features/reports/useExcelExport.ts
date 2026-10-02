/**
 * "Excel" tugmasi: so'rov → kutish → yuklab olish (PLAN 3.5).
 *
 * Eksport fon vazifasi (katta ro'yxat so'rov ichida tayyorlanmaydi),
 * lekin foydalanuvchi uchun bu bitta amal bo'lishi kerak: tugmani
 * bosdi — fayl keldi. Boshqa sahifaga o'tib "tayyor bo'ldimi?" deb
 * qarash — amaldagi ish oqimida yo'qoladigan qadam.
 *
 * Vazifa yiqilsa sabab qaytariladi: "hech narsa bo'lmadi" degan
 * holat qolmasligi kerak.
 */

import { useRef, useState } from 'react'
import { reportsApi } from '@/features/dashboard/api'
import { ApiError } from '@/lib/api/types'
import { t } from '@/lib/i18n'

const POLL_MS = 2000
const MAX_WAIT_MS = 120_000

export function useExcelExport(reportType: string) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const start = async (params: Record<string, unknown> = {}) => {
    setBusy(true)
    setError(null)
    try {
      const job = await reportsApi.requestExport(reportType, params)
      const deadline = Date.now() + MAX_WAIT_MS

      const poll = async (): Promise<void> => {
        const rows = await reportsApi.listExports()
        const current = rows.find((row) => row.id === job.id)
        if (current?.status === 'ready') {
          // Nom serverdan (`filename`) — u so'rov tilida va sana
          // ISO shaklda, ya'ni papkada o'zi xronologik tiziladi.
          await reportsApi.downloadExport(current.id, current.filename || `${reportType}.xlsx`)
          setBusy(false)
          return
        }
        if (current?.status === 'failed') {
          setError(current.error || t('Eksport tayyorlanmadi.'))
          setBusy(false)
          return
        }
        if (Date.now() > deadline) {
          setError(t('Eksport uzoq davom etdi — Hisobotlar sahifasidan yuklab oling.'))
          setBusy(false)
          return
        }
        timer.current = setTimeout(() => void poll(), POLL_MS)
      }

      await poll()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('Eksportni boshlab boʻlmadi.'))
      setBusy(false)
    }
  }

  const stop = () => {
    if (timer.current) clearTimeout(timer.current)
  }

  return { start, stop, busy, error }
}
