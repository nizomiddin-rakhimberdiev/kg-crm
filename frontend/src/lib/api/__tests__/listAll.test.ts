/**
 * `listAll` — server bir sahifada ko'pi bilan 100 qator beradi.
 *
 * Audit 2026-11-12 (B2): yetti joy `page_size: 200–500` so'rardi, backend
 * esa jimgina 100 tasini qaytarardi — 120 bolali bog'chada tanlov
 * ro'yxatining oxirgi 20 nafari yo'q edi va buni hech kim sezmasdi.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, httpClient } from '@/lib/api/client'

afterEach(() => vi.restoreAllMocks())

function page(items: number[], pageNo: number, totalPages: number) {
  return {
    data: {
      success: true,
      data: items,
      meta: {
        pagination: {
          count: 250,
          page: pageNo,
          page_size: 100,
          total_pages: totalPages,
          next: null,
          previous: null,
        },
      },
      message: null,
    },
  }
}

describe('api.listAll', () => {
  it('collects every page at the server maximum', async () => {
    const get = vi
      .spyOn(httpClient, 'get')
      .mockResolvedValueOnce(page([1, 2], 1, 3))
      .mockResolvedValueOnce(page([3, 4], 2, 3))
      .mockResolvedValueOnce(page([5], 3, 3))

    const result = await api.listAll<number>('/children', { status: 'active' })

    expect(result.items).toEqual([1, 2, 3, 4, 5])
    expect(get).toHaveBeenCalledTimes(3)
    expect(get.mock.calls[1][1]).toEqual({
      params: { status: 'active', page: 2, page_size: 100 },
    })
  })

  it('never asks for more than the server allows', async () => {
    const get = vi.spyOn(httpClient, 'get').mockResolvedValueOnce(page([1], 1, 1))
    await api.listAll<number>('/children', { page_size: 500 })
    expect(get.mock.calls[0][1]).toEqual({ params: { page: 1, page_size: 100 } })
  })
})
