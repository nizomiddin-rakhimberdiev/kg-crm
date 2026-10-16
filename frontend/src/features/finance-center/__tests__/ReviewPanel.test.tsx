/**
 * Hisobot jarayoni (Bosqich 13.6).
 *
 * Asosiy savollar: izohsiz qizil band qolganda topshirish tugmasi
 * bosilmaydimi; topshirilgan hisobotda rahbar "Qabul qildim"ni koʻradimi;
 * boshqaruvchi esa koʻrmaydimi.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { reportsApi, type ReviewState } from '@/features/dashboard/api'
import { ReviewPanel } from '../components/ReviewPanel'

vi.mock('@/features/dashboard/api', () => ({
  reportsApi: { review: vi.fn(), reviewAct: vi.fn(), share: vi.fn(), revokeShare: vi.fn() },
}))
vi.mock('@/app/providers/AuthProvider', () => ({ useOrganizationId: () => 'org-1' }))
const can = vi.fn(() => true)
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can, canAny: can, isReadOnly: false }),
}))

const base: ReviewState = {
  model: 'B',
  consolidation: false,
  status: 'draft',
  ready: false,
  blockers: [{ path: 'checks:month_closed', kind: 'check', title: 'Oy yopilgan', detail: '' }],
  deadline: '2026-10-05',
  late: false,
  snapshot: null,
  changed: false,
  submitted_by: '',
  submitted_at: null,
  acceptors: ['Egasi'],
  accepted_by: [],
  can_accept: true,
  events: [],
  opens: [],
  share_links: [],
}

const show = (state: Partial<ReviewState>) => {
  vi.mocked(reportsApi.review).mockResolvedValue({ ...base, ...state })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ReviewPanel at={{ year: 2026, month: 9 }} />
    </QueryClientProvider>,
  )
}

describe('ReviewPanel', () => {
  it('izohsiz qizil band bor ekan, topshirib boʻlmaydi', async () => {
    show({})
    await waitFor(() => expect(screen.getByText('Oy yopilgan')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Topshirish' })).toBeDisabled()
  })

  it('topshirilgan hisobotda rahbar qabul qila oladi', async () => {
    show({
      status: 'submitted',
      ready: true,
      blockers: [],
      snapshot: { version: 1, checksum: 'abc', created_at: '2026-10-03T10:00:00Z' },
    })
    await waitFor(() => expect(screen.getByRole('button', { name: 'Qabul qildim' })).toBeEnabled())
    expect(screen.getByRole('button', { name: 'Qaytarish' })).toBeInTheDocument()
  })

  it('rahbar boʻlmagan foydalanuvchi qabul tugmasini koʻrmaydi', async () => {
    can.mockReturnValue(false)
    show({ status: 'submitted', ready: true, blockers: [] })
    await waitFor(() => expect(screen.getByText('Topshirildi')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Qabul qildim' })).not.toBeInTheDocument()
    can.mockReturnValue(true)
  })

  it('A modelda topshirish emas, tasdiqlash', async () => {
    show({ model: 'A', ready: true, blockers: [] })
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Tasdiqladim' })).toBeInTheDocument(),
    )
    expect(screen.queryByRole('button', { name: 'Topshirish' })).not.toBeInTheDocument()
  })
})
