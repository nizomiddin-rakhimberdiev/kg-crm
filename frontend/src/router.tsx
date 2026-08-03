import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { PermissionRoute, ProtectedRoute, PublicOnlyRoute } from './app/routes/ProtectedRoute'
import LoginPage from './features/auth/pages/LoginPage'
import SignupPage from './features/auth/pages/SignupPage'
import DashboardPage from './features/dashboard/pages/DashboardPage'
import ChildrenPage from './features/children/pages/ChildrenPage'
import GroupsPage from './features/children/pages/GroupsPage'
import ChildDetailPage from './features/children/pages/ChildDetailPage'
import PaymentsPage from './features/payments/pages/PaymentsPage'
import DebtorsPage from './features/debtors/pages/DebtorsPage'
import AttendancePage from './features/attendance/pages/AttendancePage'
import StaffPage from './features/staff/pages/StaffPage'
import PayrollPage from './features/payroll/pages/PayrollPage'
import InventoryPage from './features/inventory/pages/InventoryPage'
import ExpensesPage from './features/expenses/pages/ExpensesPage'
import ReportsPage from './features/reports/pages/ReportsPage'
import BranchesPage from './features/branches/pages/BranchesPage'
import NotificationsPage from './features/notifications/pages/NotificationsPage'
import AuditPage from './features/audit/pages/AuditPage'
import BillingPage from './features/billing/pages/BillingPage'
import SettingsPage from './features/settings/pages/SettingsPage'

/**
 * Marshrutlar (docs/05 §9).
 *
 * `PermissionRoute` UI darajasidagi to'siq — URL'ni qo'lda yozgan
 * foydalanuvchini kerakli sahifaga qaytaradi. Haqiqiy himoya backend'da:
 * ruxsatsiz so'rov `403`, begona tashkilotniki `404` oladi.
 */
export const router = createBrowserRouter([
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/signup', element: <SignupPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: 'dashboard', element: <DashboardPage /> },
          {
            element: <PermissionRoute permission="children.read" />,
            children: [
              { path: 'children', element: <ChildrenPage /> },
              { path: 'children/:childId', element: <ChildDetailPage /> },
              { path: 'groups', element: <GroupsPage /> },
            ],
          },
          {
            element: <PermissionRoute permission="payments.read" />,
            children: [{ path: 'payments', element: <PaymentsPage /> }],
          },
          {
            element: <PermissionRoute permission="debtors.read" />,
            children: [{ path: 'debtors', element: <DebtorsPage /> }],
          },
          {
            element: <PermissionRoute permission="attendance.read" />,
            children: [{ path: 'attendance', element: <AttendancePage /> }],
          },
          {
            element: <PermissionRoute permission="users.read" />,
            children: [{ path: 'staff', element: <StaffPage /> }],
          },
          {
            element: <PermissionRoute permission="payroll.read" />,
            children: [{ path: 'payroll', element: <PayrollPage /> }],
          },
          {
            element: <PermissionRoute permission="inventory.read" />,
            children: [{ path: 'inventory', element: <InventoryPage /> }],
          },
          {
            element: <PermissionRoute permission="expenses.read" />,
            children: [{ path: 'expenses', element: <ExpensesPage /> }],
          },
          {
            element: <PermissionRoute permission="reports.read" />,
            children: [{ path: 'reports', element: <ReportsPage /> }],
          },
          {
            element: <PermissionRoute permission="branches.read" />,
            children: [{ path: 'branches', element: <BranchesPage /> }],
          },
          {
            element: <PermissionRoute permission="notifications.read" />,
            children: [{ path: 'notifications', element: <NotificationsPage /> }],
          },
          {
            element: <PermissionRoute permission="billing.read" />,
            children: [{ path: 'billing', element: <BillingPage /> }],
          },
          {
            element: <PermissionRoute permission="audit.read" />,
            children: [{ path: 'audit', element: <AuditPage /> }],
          },
          {
            element: <PermissionRoute permission="settings.read" />,
            children: [{ path: 'settings', element: <SettingsPage /> }],
          },
          { path: '*', element: <Navigate to="/dashboard" replace /> },
        ],
      },
    ],
  },
])
