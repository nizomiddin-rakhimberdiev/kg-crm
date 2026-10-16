/**
 * Reja va prognoz (Bosqich 13.7).
 *
 * Asosiy savol: ega "qancha pul olsa boʻladi?" savoliga formulasi bilan
 * javob koʻradimi va pul yetmasa — ogohlantirishni.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { reportsApi, type ForecastView } from '@/features/dashboard/api'
import { PlanTab } from '../components/PlanTab'

vi.mock('@/features/dashboard/api', () => ({
  reportsApi: {
    forecast: vi.fn(),
    budget: vi.fn(() => new Promise(() => {})),
    kpi: vi.fn(() => new Promise(() => {})),
    trends: vi.fn(() => new Promise(() => {})),
  },
}))
vi.mock('@/features/expenses/api', () => ({ expensesApi: { recentCategories: vi.fn() } }))
vi.mock('@/app/providers/AuthProvider', () => ({ useOrganizationId: () => 'org-1' }))
vi.mock('@/app/providers/BranchProvider', () => ({
  useBranchScope: () => ({ selectedBranchId: null }),
}))
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can: () => true, canAny: () => true, isReadOnly: false }),
}))
vi.mock('recharts', () => ({
  ResponsiveContainer: () => null,
  LineChart: () => null,
  Line: () => null,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  Legend: () => null,
}))

const view = (amount: string, shortfall: string): ForecastView => ({
  as_of: '2026-09-15',
  opening: '180000000.00',
  basis: { collection_rate: '75.0', recurring_monthly: '0.00', payroll_net: '0.00', excluded: '' },
  lines: [],
  buckets: [30, 60, 90].map((days) => ({
    days,
    until: '2026-10-15',
    inflows: { tuition: '0.00', total: '0.00' },
    outflows: { suppliers: '110000000.00', total: '110000000.00' },
    closing: '70000000.00',
  })),
  safe_withdrawal: {
    money: '180000000.00',
    obligations_30: '110000000.00',
    reserve: '30000000.00',
    reserve_basis: 'Sozlamadagi summa',
    amount,
    shortfall,
  },
})

const show = () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <PlanTab />
    </QueryClientProvider>,
  )
}

describe('PlanTab', () => {
  it('xavfsiz olish summasini formulasi bilan koʻrsatadi', async () => {
    vi.mocked(reportsApi.forecast).mockResolvedValue(view('40000000.00', '0.00'))
    show()
    await waitFor(() => expect(screen.getByText('Qancha pul olsa boʻladi?')).toBeInTheDocument())
    expect(screen.getByText('− kelgusi 30 kun majburiyatlari')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('pul yetmasa ogohlantiradi', async () => {
    vi.mocked(reportsApi.forecast).mockResolvedValue(view('0.00', '40000000.00'))
    show()
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
