/** Marshrut himoyasi va ruxsat bo'yicha yo'naltirish (docs/05 §9). */

import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/app/providers/AuthProvider'
import { landingPathFor } from '@/config/navigation'
import { useCan, type PermissionCode } from '@/lib/rbac/useCan'

function FullPageSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
    </div>
  )
}

/** Ro'yxatdagi istalgan bittasi yetarli; `.read` bo'yicha tekshiriladi. */
function useAllows() {
  const { can } = useCan()
  return (permission: PermissionCode | PermissionCode[]) => {
    const required = Array.isArray(permission) ? permission : [permission]
    // `.read` ni tekshiramiz: sahifani ochish uchun o'qish yetarli, yozish
    // huquqi alohida, tugmalar darajasida hal qilinadi.
    return required.some((code) => can(code.replace(/\.\w+$/, '.read') as PermissionCode))
  }
}

/**
 * Foydalanuvchi uchun "bosh sahifa".
 *
 * `/` va noma'lum manzillar shu yerga tushadi. Manzil ruxsatdan
 * hisoblanadi (`landingPathFor`), shuning uchun boshqaruv paneliga
 * ruxsati yo'q rol ham ishlaydigan ekranga boradi.
 */
export function HomeRedirect() {
  const allows = useAllows()
  return <Navigate to={landingPathFor(allows)} replace />
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

export function PermissionRoute({
  permission,
  requires,
}: {
  /** Bitta ruxsat yoki ro'yxat — ro'yxatda istalgan bittasi yetarli. */
  permission: PermissionCode | PermissionCode[]
  /** Qo'shimcha shart — bu ham bo'lishi kerak (`NavItem.requires`). */
  requires?: PermissionCode
}) {
  const allows = useAllows()
  if (!allows(permission) || (requires && !allows(requires))) {
    return <Navigate to={landingPathFor(allows)} replace />
  }
  return <Outlet />
}

export function PublicOnlyRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const allows = useAllows()
  if (isLoading) return <FullPageSpinner />
  if (isAuthenticated) return <Navigate to={landingPathFor(allows)} replace />
  return <Outlet />
}
