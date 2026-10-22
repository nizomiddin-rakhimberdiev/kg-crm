/**
 * `/debtors` havolasi hamma uchun ishlashi kerak (2026-10-22).
 *
 * Qarzdorlar Toʻlovlar ichiga koʻchdi, lekin `payments.read` ruxsati
 * YOʻQ, `debtors.read` esa BOR rol boʻlishi mumkin — bogʻcha egasi
 * qoʻlda yasagan "Qarz yigʻuvchi" roli aynan shunday boʻladi. Unday
 * odam uchun `/payments` ga yoʻnaltirish ruxsat xatosiga olib kelardi:
 * koʻchirish uning ekranini butunlay olib qoʻyardi.
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

const can = vi.fn()
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can, canAny: can, isReadOnly: false }),
}))
vi.mock('@/features/debtors/pages/DebtorsPage', () => ({
  default: () => <p>qarzdorlar roʻyxati</p>,
}))

const { DebtorsRedirect } = await import('@/features/debtors/pages/DebtorsRedirect')

function show(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/debtors" element={<DebtorsRedirect />} />
        <Route path="/payments" element={<p>toʻlovlar sahifasi</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DebtorsRedirect', () => {
  it('toʻlovlarni koʻra oladigan odamni tabga yuboradi', () => {
    can.mockReturnValue(true)
    show('/debtors?overdue_days=15')
    expect(screen.getByText('toʻlovlar sahifasi')).toBeTruthy()
  })

  it('toʻlovlarga ruxsati yoʻq odamga roʻyxatni OʻZI koʻrsatadi', async () => {
    can.mockReturnValue(false)
    show('/debtors')
    // Roʻyxat `lazy` — avval "Yuklanmoqda…" chiziladi.
    expect(await screen.findByText('qarzdorlar roʻyxati')).toBeTruthy()
  })
})
