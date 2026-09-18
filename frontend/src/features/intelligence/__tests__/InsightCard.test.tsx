import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { insightsApi } from '../api'
import { InsightCard } from '../components/InsightCard'
import type { Insight } from '@/lib/api/types'

vi.mock('../api', () => ({
  insightsApi: { seen: vi.fn(), resolve: vi.fn(), dismiss: vi.fn() },
}))
vi.mock('@/features/children/api', () => ({
  childrenApi: {
    list: vi.fn(async () => ({
      items: [
        {
          id: 'c1',
          full_name: 'Ali Valiyev',
          current_group: { id: 'g', name: 'Quyosh' },
        },
      ],
      pagination: null,
    })),
  },
}))
const can = vi.fn(() => true)
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can, canAny: can, isReadOnly: false }),
}))
vi.mock('@/app/providers/AuthProvider', () => ({
  useOrganizationId: () => 'org-1',
}))

const insight: Insight = {
  id: 'i1',
  branch: 'b1',
  type: 'payment_delay',
  severity: 'critical',
  status: 'new',
  is_open: true,
  subject_type: 'branch',
  subject_id: 'b1',
  evidence: {
    as_of: '2026-09-17',
    overdue_days_threshold: 15,
    children_count: 24,
    active_children: 105,
    critical_days_threshold: 45,
    critical_children_threshold: 11,
    total_overdue: '21758500.00',
    average_days_overdue: 61,
    max_days_overdue: 160,
    children: [
      {
        child_id: 'c1',
        group_id: 'g',
        overdue_amount: '600000.00',
        days_overdue: 160,
        invoices: 1,
      },
      {
        child_id: 'gone',
        group_id: null,
        overdue_amount: '1500000.00',
        days_overdue: 38,
        invoices: 1,
      },
    ],
  },
  evidence_version: 1,
  recommendation_key: 'payment_delay.review_debtors',
  deep_link: '/debtors?overdue_days=15',
  generated_at: '2026-09-17T03:30:00Z',
  refreshed_at: null,
  seen_at: null,
  resolved_at: null,
  dismissed_at: null,
  dismissed_until: null,
  auto_resolved_at: null,
}

function renderCard(override: Partial<Insight> = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <InsightCard insight={{ ...insight, ...override }} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  can.mockReturnValue(true)
  vi.mocked(insightsApi.seen).mockResolvedValue({ ...insight, status: 'seen' })
  vi.mocked(insightsApi.resolve).mockResolvedValue({
    ...insight,
    status: 'resolved',
  })
})

describe('InsightCard', () => {
  it('sarlavha evidence raqamlaridan, deep link — nisbiy yo‘l', () => {
    renderCard()
    expect(
      screen.getByText('24 ta bola bo‘yicha to‘lov 15 kundan ortiq kechikmoqda'),
    ).toBeInTheDocument()
    expect(screen.getByText('Jiddiy')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Ro‘yxatni ochish/ })).toHaveAttribute(
      'href',
      '/debtors?overdue_days=15',
    )
  })

  it('yangi karta birinchi ko‘rsatilganda `seen` bo‘ladi — bir marta', async () => {
    renderCard()
    await waitFor(() => expect(insightsApi.seen).toHaveBeenCalledTimes(1))
    expect(insightsApi.seen).toHaveBeenCalledWith('i1')
  })

  it('`seen` bo‘lgan karta uchun qayta yuborilmaydi', async () => {
    renderCard({ status: 'seen', seen_at: '2026-09-17T08:00:00Z' })
    await new Promise((r) => setTimeout(r, 20))
    expect(insightsApi.seen).not.toHaveBeenCalled()
  })

  it('`dashboard.update` bo‘lmasa amal tugmalari yo‘q, "Nega?" bor', () => {
    can.mockReturnValue(false)
    renderCard()
    expect(screen.queryByRole('button', { name: /Hal qilindi/ })).toBeNull()
    expect(screen.getByRole('button', { name: /Nega\?/ })).toBeInTheDocument()
  })

  it('"Nega?" — snapshot raqamlari, jonli ismlar, o‘chirilgan bola yorlig‘i', async () => {
    renderCard()
    fireEvent.click(screen.getByRole('button', { name: /Nega\?/ }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('Eng uzoq kechikish 160 kun — chegara 45 kun.')
    expect(dialog).toHaveTextContent('24 ta bola — chegara 11 ta')
    await waitFor(() => expect(dialog).toHaveTextContent('Ali Valiyev'))
    expect(dialog).toHaveTextContent('Quyosh')
    expect(dialog).toHaveTextContent('o‘chirilgan bola')
    expect(dialog).toHaveTextContent('Holat 2026-09-17 sanasiga')
  })

  it('"Hal qilindi" — resolve chaqiriladi', async () => {
    renderCard({ status: 'seen' })
    fireEvent.click(screen.getByRole('button', { name: /Hal qilindi/ }))
    await waitFor(() => expect(insightsApi.resolve).toHaveBeenCalledWith('i1'))
  })

  it('noma’lum evidence sxemasi — karta jim (yolg‘on jumla yo‘q)', () => {
    const { container } = renderCard({ evidence: { drop_points: 12 } })
    expect(container.querySelector('[data-testid="insight-card"]')).toBeNull()
  })
})
