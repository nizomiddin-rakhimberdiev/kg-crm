/**
 * Oylik yigʻma qaysi oyni koʻrsatadi (audit, 2026-10-21).
 *
 * Sahifaning davr tanlagichi "shu oy" turganda karta jimgina OLDINGI
 * oyni soʻrardi. Ekranda ikkita davr bor edi, ulardan biri yozilmagan —
 * va mudira kartadagi raqamni shu oyning raqami deb oʻqiydi.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { reportsApi } from '@/features/dashboard/api'
import { MonthlySummary } from '../components/MonthlySummary'

vi.mock('@/features/dashboard/api', () => ({
  reportsApi: {
    monthlySummary: vi.fn(() => new Promise(() => {})),
    completeness: vi.fn(() => new Promise(() => {})),
  },
}))
vi.mock('@/app/providers/AuthProvider', () => ({ useOrganizationId: () => 'org-1' }))
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can: () => true, canAny: () => true, isReadOnly: false }),
}))
vi.mock('@/features/reports/useExcelExport', () => ({
  useExcelExport: () => ({ start: vi.fn(), busy: false, error: null }),
}))

function show(month: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MonthlySummary month={month} />
    </QueryClientProvider>,
  )
}

describe('MonthlySummary', () => {
  it('sahifada tanlangan oyni soʻraydi', async () => {
    show('2026-10')
    await waitFor(() => expect(reportsApi.monthlySummary).toHaveBeenCalledWith(2026, 10))
    expect(screen.getByRole('combobox', { name: 'Oy' })).toHaveTextContent('Oktabr')
    expect(screen.getByRole('combobox', { name: 'Yil' })).toHaveTextContent('2026')
  })

  it('sahifa davri oʻzgarsa karta ham oʻzgaradi', async () => {
    const { rerender } = show('2026-10')
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    rerender(
      <QueryClientProvider client={client}>
        <MonthlySummary month="2026-08" />
      </QueryClientProvider>,
    )
    await waitFor(() => expect(reportsApi.monthlySummary).toHaveBeenCalledWith(2026, 8))
  })
})
