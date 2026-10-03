/** Frozen modules follow the backend's switch in `/auth/me` (2026-10-03). */

import { renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useAuth } from '@/app/providers/AuthProvider'
import { useFeature } from '../features'

vi.mock('@/app/providers/AuthProvider', () => ({ useAuth: vi.fn() }))

const withFeatures = (features?: string[]) =>
  vi.mocked(useAuth).mockReturnValue({ user: { features } } as ReturnType<typeof useAuth>)

describe('useFeature', () => {
  it('is off when the backend does not list it', () => {
    withFeatures([])
    expect(renderHook(() => useFeature('kitchen')).result.current).toBe(false)
  })

  it('is off for an older session without the field', () => {
    withFeatures(undefined)
    expect(renderHook(() => useFeature('contracts')).result.current).toBe(false)
  })

  it('is on when switched on', () => {
    withFeatures(['contracts'])
    expect(renderHook(() => useFeature('contracts')).result.current).toBe(true)
    expect(renderHook(() => useFeature('kitchen')).result.current).toBe(false)
  })
})
