import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import DashboardPage from './features/dashboard/pages/DashboardPage'
import ChildrenPage from './features/children/pages/ChildrenPage'
import PaymentsPage from './features/payments/pages/PaymentsPage'
import DebtorsPage from './features/debtors/pages/DebtorsPage'
import AttendancePage from './features/attendance/pages/AttendancePage'
import StaffPage from './features/staff/pages/StaffPage'
import PayrollPage from './features/payroll/pages/PayrollPage'
import InventoryPage from './features/inventory/pages/InventoryPage'
import ExpensesPage from './features/expenses/pages/ExpensesPage'
import ReportsPage from './features/reports/pages/ReportsPage'
import SettingsPage from './features/settings/pages/SettingsPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'children', element: <ChildrenPage /> },
      { path: 'payments', element: <PaymentsPage /> },
      { path: 'debtors', element: <DebtorsPage /> },
      { path: 'attendance', element: <AttendancePage /> },
      { path: 'staff', element: <StaffPage /> },
      { path: 'payroll', element: <PayrollPage /> },
      { path: 'inventory', element: <InventoryPage /> },
      { path: 'expenses', element: <ExpensesPage /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: '*', element: <Navigate to="/dashboard" replace /> },
    ],
  },
])
