/** 422 qayta so'ralmaydi — javob o'zgarmaydi (audit 2026-11-12, D2). */
import { describe, expect, it } from 'vitest'
import { queryClient } from '@/lib/api/queryClient'
import { ApiError } from '@/lib/api/types'

describe('queryClient retry', () => {
  const retry = queryClient.getDefaultOptions().queries?.retry as (
    count: number,
    error: unknown,
  ) => boolean

  it('does not retry a business rule violation', () => {
    expect(retry(0, new ApiError('BUSINESS_RULE_VIOLATION', 'Obuna yoʻq'))).toBe(false)
  })

  it('still retries a network hiccup', () => {
    expect(retry(0, new Error('Network Error'))).toBe(true)
  })
})
