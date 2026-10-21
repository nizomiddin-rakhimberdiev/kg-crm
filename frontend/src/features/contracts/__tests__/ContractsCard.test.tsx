/**
 * Shablondan tuzilgan shartnomalar kartasi (mijoz, 2026-10-21).
 *
 * Mijoz imzolangan faylni biriktiradi (ChildDocumentsCard). Shablon yoʻli
 * faqat haqiqatan ishlatilganda koʻrinadi: shablon ham, shablondan
 * tuzilgan shartnoma ham boʻlmasa — karta yoʻq, "Avval shablon yarating"
 * degan talab ham yoʻq.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { contractTemplatesApi, contractsApi } from '@/features/contracts/api'
import { ContractsCard } from '../components/ContractsCard'

vi.mock('@/features/contracts/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/contracts/api')>()
  return {
    ...actual,
    contractsApi: { ...actual.contractsApi, forChild: vi.fn() },
    contractTemplatesApi: { ...actual.contractTemplatesApi, list: vi.fn() },
  }
})
vi.mock('@/app/providers/AuthProvider', () => ({ useOrganizationId: () => 'org-1' }))
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can: () => true, canAny: () => true, isReadOnly: false }),
}))

const show = () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ContractsCard childId="c1" />
    </QueryClientProvider>,
  )
}

describe('ContractsCard', () => {
  it('shablon ham, shartnoma ham boʻlmasa — karta yoʻq', async () => {
    vi.mocked(contractsApi.forChild).mockResolvedValue([])
    vi.mocked(contractTemplatesApi.list).mockResolvedValue([])
    const { container } = show()
    await waitFor(() => expect(contractTemplatesApi.list).toHaveBeenCalled())
    await waitFor(() => expect(container).toBeEmptyDOMElement())
    expect(screen.queryByText(/shablonini yarating/)).not.toBeInTheDocument()
  })

  it('shablon bor boʻlsa — shablondan tuzish koʻrinadi', async () => {
    vi.mocked(contractsApi.forChild).mockResolvedValue([])
    vi.mocked(contractTemplatesApi.list).mockResolvedValue([
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      { id: 't1', name: 'Asosiy' } as any,
    ])
    show()
    await waitFor(() =>
      expect(screen.getByText('Shablondan tuzilgan shartnomalar')).toBeInTheDocument(),
    )
  })
})
