/**
 * Yuqoridagi qidiruv (mijoz soʻrovi, 2026-10-28).
 *
 * Maydon har bir ekranda turardi va "Ism yoki ID boʻyicha qidiruv..."
 * deb vaʼda berardi — lekin unga yozilgan narsa hech qayerga
 * ketmasdi: holat ham, soʻrov ham, natija ham yoʻq edi. Ishlamaydigan
 * qidiruv — yoʻq qidiruvdan yomonroq: odam uni sinab koʻradi,
 * natijasiz qoladi va keyin tizimga ishonmaydi.
 *
 * Mijoz "asosiyda ham, bolalarda ham, toʻlovlar va qarzdorliklarda
 * ham" degan edi — "asosiy" aynan shu maydon.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { GlobalSearch } from '../layout/GlobalSearch'

const can = vi.fn(() => true)
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can, canAny: can, isReadOnly: false }),
}))
vi.mock('@/app/providers/AuthProvider', () => ({
  useOrganizationId: () => 'org-1',
}))

const list = vi.fn()
vi.mock('@/features/children/api', () => ({
  childrenApi: { list: (params: Record<string, unknown>) => list(params) },
}))

const navigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => navigate }
})

function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <GlobalSearch />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const child = {
  id: 'c-1',
  full_name: 'Safarova Aziza',
  contract_number: 'SH-2026-0041',
  current_group: { id: 'g-1', name: 'Quyoshcha' },
}

beforeEach(() => {
  vi.clearAllMocks()
  can.mockReturnValue(true)
  list.mockResolvedValue({ items: [child] })
})

describe('Global qidiruv', () => {
  it('yozilgan matn bilan soʻrov yuboradi', async () => {
    show()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'SH-2026-0041' } })
    await waitFor(() => expect(list).toHaveBeenCalled())
    expect(list.mock.calls[0][0]).toMatchObject({ q: 'SH-2026-0041' })
  })

  it('topilgan bolani roʻyxatda koʻrsatadi', async () => {
    show()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'safarova' } })
    expect(await screen.findByText('Safarova Aziza')).toBeTruthy()
    expect(screen.getByText(/SH-2026-0041/)).toBeTruthy()
  })

  it('qator bosilsa bolaning kartasiga oʻtadi', async () => {
    show()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'safarova' } })
    fireEvent.click(await screen.findByText('Safarova Aziza'))
    expect(navigate).toHaveBeenCalledWith('/children/c-1')
  })

  it('bitta harf uchun soʻrov yubormaydi', async () => {
    show()
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'a' } })
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(list).not.toHaveBeenCalled()
  })

  it('bolalarni oʻqiy olmaydigan rolga maydon umuman koʻrinmaydi', () => {
    can.mockReturnValue(false)
    show()
    expect(screen.queryByRole('searchbox')).toBeNull()
  })
})
