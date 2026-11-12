/**
 * Ruxsatsiz bo'limga kirgan odam NEGA bu yerda emasligini ko'radi.
 *
 * Audit 2026-11-12 (C3): ilgari jim qayta yo'naltirish bo'lardi — kassir
 * `/reports` havolasini ochsa, to'lovlar sahifasiga tushib qolardi va
 * "havola buzuq" deb o'ylardi.
 */
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { PermissionRoute } from '@/app/routes/ProtectedRoute'

vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({ can: (code: string) => code === 'payments.read' }),
}))

describe('PermissionRoute', () => {
  it('says the section is closed instead of silently redirecting', () => {
    render(
      <MemoryRouter initialEntries={['/reports']}>
        <Routes>
          <Route element={<PermissionRoute permission="reports.read" />}>
            <Route path="/reports" element={<p>Hisobotlar</p>} />
          </Route>
          <Route path="/payments" element={<p>Toʻlovlar sahifasi</p>} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Bu boʻlimga ruxsat yoʻq')).toBeInTheDocument()
    expect(screen.queryByText('Hisobotlar')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /bosh sahifa/i })).toHaveAttribute('href', '/payments')
  })

  it('opens the section when allowed', () => {
    render(
      <MemoryRouter initialEntries={['/payments']}>
        <Routes>
          <Route element={<PermissionRoute permission="payments.read" />}>
            <Route path="/payments" element={<p>Toʻlovlar sahifasi</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Toʻlovlar sahifasi')).toBeInTheDocument()
  })
})
