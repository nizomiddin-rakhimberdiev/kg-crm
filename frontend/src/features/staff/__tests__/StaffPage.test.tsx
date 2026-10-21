/**
 * Xodimlar davomati qayerda (mijoz, 2026-10-21).
 *
 * Tabel "Xodimlar" sahifasida va faqat oylik/HR ruxsati (`payroll.read`)
 * bilan koʻrinadi — bolalar davomatini yurituvchi rol uni koʻrmaydi.
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import StaffPage from '../pages/StaffPage'

vi.mock('@/features/staff/components/EmployeesPanel', () => ({ EmployeesPanel: () => null }))
vi.mock('@/features/staff/components/AccountsPanel', () => ({ AccountsPanel: () => null }))
vi.mock('@/features/staff/components/RolesPanel', () => ({ RolesPanel: () => null }))
vi.mock('@/features/attendance/components/StaffAttendancePanel', () => ({
  StaffAttendancePanel: () => <p>tabel</p>,
}))
const granted = new Set<string>()
vi.mock('@/lib/rbac/useCan', () => ({
  useCan: () => ({
    can: (code: string) => granted.has(code),
    canAny: () => true,
    isReadOnly: false,
  }),
}))

const show = (url = '/staff') =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <StaffPage />
    </MemoryRouter>,
  )

describe('StaffPage', () => {
  it('oylik ruxsati bor rahbar xodimlar davomatini koʻradi', () => {
    granted.clear()
    granted.add('payroll.read')
    granted.add('users.read')
    show('/staff?tab=attendance')
    expect(screen.getByRole('button', { name: 'Davomat' })).toBeInTheDocument()
    expect(screen.getByText('tabel')).toBeInTheDocument()
  })

  it('oylik ruxsati yoʻq rol davomat tabini koʻrmaydi', () => {
    granted.clear()
    granted.add('users.read')
    show('/staff?tab=attendance')
    expect(screen.queryByRole('button', { name: 'Davomat' })).not.toBeInTheDocument()
    expect(screen.queryByText('tabel')).not.toBeInTheDocument()
  })
})
