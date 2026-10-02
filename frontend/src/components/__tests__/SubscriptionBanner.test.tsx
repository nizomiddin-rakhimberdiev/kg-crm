/**
 * Obuna banneri (PLAN 4.9).
 *
 * Uchta qoida tekshiriladi, chunki uchalasi ham egasining qarori:
 * banner faqat egasi va direktorga koʻrinadi, summani aytadi va
 * yopilsa kuniga bir marta qaytadi.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SubscriptionBanner } from '../layout/ReadOnlyBanner'
import type { SubscriptionState } from '@/lib/api/types'

const auth = { subscription: null as SubscriptionState | null }
vi.mock('@/app/providers/AuthProvider', () => ({
  useAuth: () => auth,
}))
const can = vi.fn(() => true)
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can, canAny: can, isReadOnly: false }),
}))

const show = () =>
  render(
    <MemoryRouter>
      <SubscriptionBanner />
    </MemoryRouter>,
  )

beforeEach(() => {
  localStorage.clear()
  can.mockReturnValue(true)
  auth.subscription = {
    status: 'pending_payment',
    read_only: false,
    trial_ends_at: null,
    amount_due: '400000',
  }
})

describe('SubscriptionBanner', () => {
  it('summani va "Qanday toʻlash" tugmasini koʻrsatadi', () => {
    show()
    expect(screen.getByText(/400/)).toBeInTheDocument()
    expect(screen.getByText('Qanday toʻlash')).toBeInTheDocument()
  })

  it('billing ruxsati yoʻq xodimga koʻrinmaydi', () => {
    // Toʻlov holati tarbiyachining ishi emas.
    can.mockReturnValue(false)
    const { container } = show()
    expect(container.textContent).toBe('')
  })

  it('yopilgach shu kuni qaytmaydi', () => {
    show()
    fireEvent.click(screen.getByLabelText('Bugun koʻrsatmaslik'))
    expect(screen.queryByText('Qanday toʻlash')).not.toBeInTheDocument()

    // Qayta ochilganda ham — chunki kun saqlangan.
    const again = show()
    expect(again.container.textContent).toBe('')
  })

  it('kun oʻtgach qaytadi', () => {
    localStorage.setItem('radix.subscription-banner-dismissed', '2000-01-01')
    show()
    expect(screen.getByText('Qanday toʻlash')).toBeInTheDocument()
  })

  it('toʻxtatilgan obuna banneri YOPILMAYDI', () => {
    // U eslatma emas — ish oqimini toʻxtatib turgan holat.
    auth.subscription = { status: 'suspended', read_only: true, trial_ends_at: null }
    localStorage.setItem(
      'radix.subscription-banner-dismissed',
      new Date().toISOString().slice(0, 10),
    )
    show()
    expect(screen.getByText('Qanday toʻlash')).toBeInTheDocument()
  })

  it('sinov davrida qolgan kun koʻrsatiladi', () => {
    const inFiveDays = new Date(Date.now() + 5 * 86_400_000).toISOString()
    auth.subscription = { status: 'trialing', read_only: false, trial_ends_at: inFiveDays }
    show()
    expect(screen.getByText(/5 kun qoldi/)).toBeInTheDocument()
  })
})
