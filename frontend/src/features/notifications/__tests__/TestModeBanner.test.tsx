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
  default_channel: 'telegram',
  test_mode: true,
  provider: 'console',
  channels: {
    telegram: { configured: false, bot_username: '', reach: { linked: 0, total: 0 } },
    sms: { configured: false, provider: 'console' },
  },
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
    telegram: 0,
    sms: 0,
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
  it('Telegram bot ulanmagan bo‘lsa ogohlantiradi', async () => {
    vi.mocked(notificationsApi.status).mockResolvedValue(status())
    show()
    await waitFor(() => expect(screen.getByText('Telegram bot ulanmagan')).toBeInTheDocument())
    expect(screen.getByText(/YUBORILMAYDI/)).toBeInTheDocument()
  })

  it('asosiy kanal SMS bo‘lsa, ogohlantirish SMS haqida bo‘ladi', async () => {
    vi.mocked(notificationsApi.status).mockResolvedValue(status({ default_channel: 'sms' }))
    show()
    await waitFor(() => expect(screen.getByText('SMS test rejimida')).toBeInTheDocument())
  })

  it('bot ulangan va hamma ota-ona ulangan bo‘lsa banner yo‘qoladi', async () => {
    vi.mocked(notificationsApi.status).mockResolvedValue(
      status({
        test_mode: false,
        channels: {
          telegram: { configured: true, bot_username: 'radix_bot', reach: { linked: 4, total: 4 } },
          sms: { configured: false, provider: 'console' },
        },
      }),
    )
    const { container } = show()
    await waitFor(() => expect(notificationsApi.status).toHaveBeenCalled())
    expect(container.textContent).toBe('')
  })

  it('bot ishlaydi, lekin ota-onalar ulanmagan — bu ham aytiladi', async () => {
    // Natija bir xil: xabar hech kimga bormaydi.
    vi.mocked(notificationsApi.status).mockResolvedValue(
      status({
        test_mode: false,
        channels: {
          telegram: { configured: true, bot_username: 'radix_bot', reach: { linked: 1, total: 4 } },
          sms: { configured: false, provider: 'console' },
        },
      }),
    )
    show()
    await waitFor(() => expect(screen.getByText(/Qolgan 3 tasi/)).toBeInTheDocument())
    // Raqamlar TARTIBI: "4 ota-onadan 1 tasi", teskarisi emas — oldin
    // jumla "1 ota-onadan 4 tasi ulangan" deb bema'ni gap aytardi.
    expect(screen.getByText(/4 ota-onadan 1 tasi Telegramga ulangan/)).toBeInTheDocument()
  })

  it('xabar yuborish butunlay oʻchirilgan bo‘lsa buni ham aytadi', async () => {
    vi.mocked(notificationsApi.status).mockResolvedValue(
      status({ sms_enabled: false, test_mode: false }),
    )
    show()
    await waitFor(() => expect(screen.getByText(/oʻchirilgan/)).toBeInTheDocument())
  })
})
