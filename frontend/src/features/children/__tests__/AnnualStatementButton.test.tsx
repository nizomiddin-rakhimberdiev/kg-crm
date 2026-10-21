/**
 * Yillik maʼlumotnoma qaysi yilni soʻraydi (audit, 2026-10-21).
 *
 * Tanlagich sukut boʻyicha OʻTGAN yilda turardi: 2026 yilda ota-ona
 * soʻraganda 2025 chiqardi va buni sezmaslik oson. Maʼlumotnoma
 * koʻpincha joriy yil uchun olinadi — toʻlovlar davom etayotganda.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AnnualStatementButton } from '../components/AnnualStatementButton'

vi.mock('@/lib/api/client', () => ({ httpClient: { get: vi.fn() } }))

describe('AnnualStatementButton', () => {
  it('sukut boʻyicha joriy yil turadi', () => {
    render(<AnnualStatementButton childId="c1" />)
    const select = screen.getByLabelText('Yillik maʼlumotnoma') as HTMLSelectElement
    expect(select.value).toBe(String(new Date().getFullYear()))
  })

  it('oʻtgan yillarni ham taklif qiladi', () => {
    render(<AnnualStatementButton childId="c1" />)
    const select = screen.getByLabelText('Yillik maʼlumotnoma') as HTMLSelectElement
    const year = new Date().getFullYear()
    expect([...select.options].map((option) => option.value)).toEqual([
      String(year),
      String(year - 1),
      String(year - 2),
    ])
  })
})
