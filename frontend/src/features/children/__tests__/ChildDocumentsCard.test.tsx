/**
 * Imzolangan shartnoma fayli (mijoz, 2026-10-21).
 *
 * Asosiy savollar: biriktirilgan fayl roʻyxatda koʻrinadimi; PDF/DOC/DOCX
 * dan boshqasi serverga umuman yuborilmaydimi; tahrirlash huquqi
 * boʻlmaganda biriktirish tugmasi yoʻqmi.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { childrenApi } from '@/features/children/api'
import { ChildDocumentsCard } from '../components/ChildDocumentsCard'

vi.mock('@/features/children/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/features/children/api')>()
  return {
    ...actual,
    childrenApi: {
      documents: vi.fn(),
      uploadDocument: vi.fn(),
      removeDocument: vi.fn(),
      downloadDocument: vi.fn(),
    },
  }
})
vi.mock('@/app/providers/AuthProvider', () => ({ useOrganizationId: () => 'org-1' }))
const can = vi.fn(() => true)
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can, canAny: can, isReadOnly: false }),
}))

const show = () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ChildDocumentsCard childId="c1" />
    </QueryClientProvider>,
  )
}

describe('ChildDocumentsCard', () => {
  beforeEach(() => {
    vi.mocked(childrenApi.documents).mockResolvedValue([
      {
        id: 'd1',
        kind: 'contract',
        name: 'shartnoma.pdf',
        size: 2048,
        uploaded_by: 'Abdulaziz',
        created_at: '2026-10-21T09:00:00Z',
      },
    ])
    vi.mocked(childrenApi.uploadDocument).mockReset()
    can.mockReturnValue(true)
  })

  it('biriktirilgan fayl roʻyxatda', async () => {
    show()
    await waitFor(() => expect(screen.getByText('shartnoma.pdf')).toBeInTheDocument())
  })

  it('rasm faylini serverga yubormaydi', async () => {
    show()
    const input = screen.getByLabelText('Shartnoma faylini tanlash')
    fireEvent.change(input, { target: { files: [new File(['x'], 'rasm.jpg')] } })
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(childrenApi.uploadDocument).not.toHaveBeenCalled()
  })

  it('PDF ni yuklaydi', async () => {
    vi.mocked(childrenApi.uploadDocument).mockResolvedValue({
      id: 'd2',
      kind: 'contract',
      name: 'yangi.pdf',
      size: 10,
      uploaded_by: '',
      created_at: '2026-10-21T10:00:00Z',
    })
    show()
    const file = new File(['%PDF'], 'yangi.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Shartnoma faylini tanlash'), {
      target: { files: [file] },
    })
    await waitFor(() => expect(childrenApi.uploadDocument).toHaveBeenCalledWith('c1', file))
  })

  it('tahrirlash huquqi yoʻq — biriktirish tugmasi yoʻq', async () => {
    can.mockReturnValue(false)
    show()
    await waitFor(() => expect(screen.getByText('shartnoma.pdf')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /Fayl biriktirish/ })).not.toBeInTheDocument()
  })
})
