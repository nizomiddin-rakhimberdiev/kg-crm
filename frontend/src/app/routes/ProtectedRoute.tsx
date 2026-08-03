/** Marshrut himoyasi va ruxsat bo'yicha yo'naltirish (docs/05 §9). */

import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { useCan, type PermissionCode } from '@/lib/rbac/useCan'

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
    </div>
  )
}

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  // Sessiya tiklanayotganda login'ga otib yubormaymiz — aks holda sahifa
  // har yangilanganda login ekrani miltillab o'tadi.
  if (isLoading) return <FullPageSpinner />

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}

export function PermissionRoute({ permission }: { permission: PermissionCode }) {
  const { can } = useCan()
  // `.read` ni tekshiramiz: sahifani ochish uchun o'qish yetarli, yozish
  // huquqi alohida, tugmalar darajasida hal qilinadi.
  const readPermission = permission.replace(/\.\w+$/, '.read') as PermissionCode
  if (!can(readPermission)) return <Navigate to="/dashboard" replace />
  return <Outlet />
}

export function PublicOnlyRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <FullPageSpinner />
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
