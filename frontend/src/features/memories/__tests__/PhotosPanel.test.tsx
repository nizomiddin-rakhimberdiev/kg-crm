/**
 * Rasmlar bo'limi: taklif ("suggested") tegli rasm "Tekshiring" belgisi bilan
 * ko'rinadi, filtr ishlaydi va rasm blob sifatida (ochiq URL'siz) olinadi.
 */

import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { MemoryPhoto } from '@/lib/api/types'

vi.mock('@/app/providers/AuthProvider', () => ({
  useOrganizationId: () => 'org-1',
  useAuth: () => ({
    user: { permissions: ['memories.read', 'memories.create', 'memories.update'] },
    isReadOnly: false,
  }),
}))

const photos: MemoryPhoto[] = [
  {
    id: 'p1',
    branch: 'b1',
    image_url: '/api/v1/memory-photos/p1/image',
    taken_at: '2026-10-06T09:00:00Z',
    source: 'telegram',
    status: 'processed',
    faces_detected: 2,
    caption: '',
    created_at: '2026-10-06T09:00:00Z',
    tags: [
      {
        id: 't1',
        photo: 'p1',
        child: 'c1',
        child_name: 'Ali',
        confidence: 0.5,
        box: [0.1, 0.1, 0.2, 0.2],
        status: 'suggested',
        sent_at: null,
      },
    ],
  },
  {
    id: 'p2',
    branch: 'b1',
    image_url: '/api/v1/memory-photos/p2/image',
    taken_at: '2026-10-06T10:00:00Z',
    source: 'upload',
    status: 'processed',
    faces_detected: 1,
    caption: '',
    created_at: '2026-10-06T10:00:00Z',
    tags: [
      {
        id: 't2',
        photo: 'p2',
        child: 'c2',
        child_name: 'Vali',
        confidence: 0.9,
        box: [],
        status: 'confirmed',
        sent_at: '2026-10-06T10:01:00Z',
      },
    ],
  },
]

vi.mock('../api', async (importOriginal) => {
  const original = await importOriginal<typeof import('../api')>()
  return {
    ...original,
    fetchBlob: vi.fn(async () => new Blob(['x'], { type: 'image/jpeg' })),
    memoryPhotosApi: {
      ...original.memoryPhotosApi,
      list: vi.fn(async () => ({ items: photos, pagination: null })),
    },
  }
})

import { PhotosPanel } from '../components/PhotosPanel'

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <PhotosPanel />
    </QueryClientProvider>,
  )
}

describe('PhotosPanel', () => {
  afterEach(cleanup)

  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => 'blob:test')
    URL.revokeObjectURL = vi.fn()
  })

  it("taklif tegli rasmni 'Tekshiring' belgisi bilan ko'rsatadi", async () => {
    renderPanel()
    expect(await screen.findByText('Tekshiring')).toBeInTheDocument()
    expect(screen.getByText('Vali')).toBeInTheDocument()
  })

  it("'Tekshirish kerak' filtri faqat tasdiqlanmagan rasmlarni qoldiradi", async () => {
    renderPanel()
    await screen.findByText('Tekshiring')
    await userEvent.click(screen.getByRole('button', { name: /Tekshirish kerak/ }))
    await waitFor(() => expect(screen.queryByText('Vali')).not.toBeInTheDocument())
    expect(screen.getByText('Tekshiring')).toBeInTheDocument()
  })

  it('rasm autentifikatsiyali blob orqali olinadi', async () => {
    renderPanel()
    await screen.findByText('Tekshiring')
    const { fetchBlob } = await import('../api')
    await waitFor(() => expect(fetchBlob).toHaveBeenCalledWith('/memory-photos/p1/image'))
  })
})
