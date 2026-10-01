/**
 * Test rejimi banneri (PLAN 3.2).
 *
 * Auditdagi eng jimgina xato: jurnal "Yuborildi" deydi, ota-ona esa
 * hech narsa olmagan. Banner shu holatni ekranda AYTADI — shuning
 * uchun uning ko'rinishi testdan o'tadi.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { notificationsApi } from '../api'
import { TestModeBanner } from '../components/TestModeBanner'
import type { SmsStatus } from '@/lib/api/types'

vi.mock('../api', () => ({
  notificationsApi: { status: vi.fn() },
}))
vi.mock('@/app/providers/AuthProvider', () => ({
  useOrganizationId: () => 'org-1',
}))

const status = (patch: Partial<SmsStatus> = {}): SmsStatus => ({
  test_mode: true,
  provider: 'console',
  sms_enabled: true,
  send_from_hour: 8,
  send_to_hour: 21,
  reminders_per_day: 1,
  max_retries: 3,
  usage: {
    year: 2026,
    month: 10,
    total: 0,
    sent: 0,
    failed: 0,
    queued: 0,
    test_mode: 0,
    parts: 0,
    price_per_part: '0',
    estimated_cost: null,
  },
  ...patch,
})

const show = () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <TestModeBanner />
    </QueryClientProvider>,
  )
}

describe('TestModeBanner', () => {
  it('provayder ulanmagan bo‘lsa ogohlantiradi', async () => {
    vi.mocked(notificationsApi.status).mockResolvedValue(status())
    show()
    await waitFor(() => expect(screen.getByText('SMS test rejimida')).toBeInTheDocument())
    expect(screen.getByText(/YUBORILMAYDI/)).toBeInTheDocument()
  })

  it('haqiqiy provayder ulangach banner yo‘qoladi', async () => {
    vi.mocked(notificationsApi.status).mockResolvedValue(status({ test_mode: false }))
    const { container } = show()
    await waitFor(() => expect(notificationsApi.status).toHaveBeenCalled())
    expect(container.textContent).toBe('')
  })

  it('SMS butunlay o‘chirilgan bo‘lsa buni ham aytadi', async () => {
    vi.mocked(notificationsApi.status).mockResolvedValue(
      status({ sms_enabled: false, test_mode: false }),
    )
    show()
    await waitFor(() => expect(screen.getByText(/o‘chirilgan/)).toBeInTheDocument())
  })
})
