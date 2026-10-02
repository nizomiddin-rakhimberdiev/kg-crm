/**
 * Ulash havolasi (PLAN 3.7).
 *
 * Asosiy savol: mudira havolani bir bosishda olib, ota-onaga
 * yuborishi mumkinmi — va bot sozlanmagan bo'lsa nima ko'radi?
 * Ishlamaydigan havolani berib qo'yish eng yomon variant.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { guardiansApi } from '../api'
import { TelegramLinkButton } from '../components/TelegramLinkButton'

vi.mock('../api', () => ({
  guardiansApi: { telegramLink: vi.fn(), telegramUnlink: vi.fn() },
}))
const can = vi.fn(() => true)
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can, canAny: can, isReadOnly: false }),
}))

const show = (linked = false) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <TelegramLinkButton guardianId="g1" linked={linked} onChange={vi.fn()} />
    </QueryClientProvider>,
  )
}

describe('TelegramLinkButton', () => {
  it('ulanmagan ota-ona uchun havola beradi', async () => {
    vi.mocked(guardiansApi.telegramLink).mockResolvedValue({
      url: 'https://t.me/radix_bot?start=abc',
      bot_username: 'radix_bot',
      linked: false,
    })
    show()
    expect(screen.getByText('Telegram ulanmagan')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Ulash havolasi'))
    await waitFor(() =>
      expect(screen.getByText('https://t.me/radix_bot?start=abc')).toBeInTheDocument(),
    )
  })

  it('bot sozlanmagan bo‘lsa, ishlamaydigan havola ko‘rsatilmaydi', async () => {
    vi.mocked(guardiansApi.telegramLink).mockResolvedValue({
      url: '',
      bot_username: '',
      linked: false,
    })
    show()
    fireEvent.click(screen.getByText('Ulash havolasi'))
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert').textContent).toContain('sozlanmagan')
  })

  it('ulangan ota-onada "uzish" ko‘rinadi, havola emas', () => {
    show(true)
    expect(screen.getByText('Telegram ulangan')).toBeInTheDocument()
    expect(screen.getByText('Uzish')).toBeInTheDocument()
    expect(screen.queryByText('Ulash havolasi')).not.toBeInTheDocument()
  })

  it('ruxsati yo‘q xodim faqat holatni ko‘radi', () => {
    can.mockReturnValueOnce(false)
    show(true)
    expect(screen.getByText('Telegram ulangan')).toBeInTheDocument()
    expect(screen.queryByText('Uzish')).not.toBeInTheDocument()
  })
})
