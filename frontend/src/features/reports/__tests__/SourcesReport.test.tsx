/**
 * "Bizni qayerdan eshitishgan?" varonkasi (Bosqich 14).
 *
 * Asosiy savol: eng koʻp bola keltirgan manba tepada turadimi, har qatorda
 * soni yozilganmi, javobsizlar varonkadan tashqarida alohida koʻrsatiladimi.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { reportsApi } from '@/features/dashboard/api'
import { SourcesReport } from '../components/SourcesReport'

vi.mock('@/features/dashboard/api', () => ({ reportsApi: { sources: vi.fn() } }))
vi.mock('@/app/providers/AuthProvider', () => ({ useOrganizationId: () => 'org-1' }))

const show = () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <SourcesReport from="2026-09-01" to="2026-09-30" />
    </QueryClientProvider>,
  )
}

describe('SourcesReport', () => {
  it('eng koʻp bola keltirgan manba tepada', async () => {
    vi.mocked(reportsApi.sources).mockResolvedValue({
      from: '2026-09-01',
      to: '2026-09-30',
      rows: [
        {
          source: 'referral',
          label: 'Tanish-bilish tavsiyasi',
          count: 2,
          active: 1,
          share: '25.0',
        },
        { source: 'instagram', label: 'Instagram', count: 5, active: 5, share: '62.5' },
      ],
      total: 8,
      unanswered: 1,
    })
    show()
    await waitFor(() => expect(screen.getByRole('list')).toBeInTheDocument())
    const items = within(screen.getByRole('list')).getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Instagram')
    expect(items[0]).toHaveTextContent('5')
    expect(items[1]).toHaveTextContent('Tanish-bilish tavsiyasi')
    expect(screen.getByText(/Koʻrsatilmagan: 1 bola/)).toBeInTheDocument()
  })
})
