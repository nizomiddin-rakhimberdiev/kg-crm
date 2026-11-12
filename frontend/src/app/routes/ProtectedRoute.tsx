/** Marshrut himoyasi va ruxsat bo'yicha yo'naltirish (docs/05 §9). */

import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'
import { Lock } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { landingPathFor } from '@/config/navigation'
import { useCan, type PermissionCode } from '@/lib/rbac/useCan'
import { t } from '@/lib/i18n'

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
    // Jim qayta yo'naltirish EMAS (audit 2026-11-12): havolani ochgan odam
    // boshqa sahifaga tushib qolib "havola buzuq" deb o'ylardi.
    return <Forbidden home={landingPathFor(allows)} />
  }
  return <Outlet />
}

function Forbidden({ home }: { home: string }) {
  return (
    <div className="mx-auto mt-16 max-w-md rounded-2xl border border-slate-200 bg-white p-6 text-center">
      <span className="mx-auto grid h-10 w-10 place-items-center rounded-xl bg-slate-100 text-slate-600">
        <Lock className="h-5 w-5" aria-hidden="true" />
      </span>
      <h1 className="mt-3 text-base font-bold text-slate-900">{t('Bu boʻlimga ruxsat yoʻq')}</h1>
      <p className="mt-1 text-sm text-slate-600">
        {t('Rolingizda bu boʻlim ochilmagan. Kerak boʻlsa — bogʻcha egasiga murojaat qiling.')}
      </p>
      <Link
        to={home}
        className="mt-4 inline-flex min-h-11 items-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
      >
        {t('Bosh sahifaga')}
      </Link>
    </div>
  )
}

export function PublicOnlyRoute() {
  const { isAuthenticated, isLoading } = useAuth()
  const allows = useAllows()
  if (isLoading) return <FullPageSpinner />
  if (isAuthenticated) return <Navigate to={landingPathFor(allows)} replace />
  return <Outlet />
}
