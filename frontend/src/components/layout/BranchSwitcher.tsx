/**
 * Filial almashtirgich — faqat Org Owner uchun.
 *
 * Boshqa rollarda tanlov ko'rsatilmaydi: ularning filiali backend'da
 * qat'iy bog'langan va bu yerda tanlov berish "o'zgartirsa bo'ladi"
 * degan noto'g'ri taassurot qoldirardi.
 */

import { Building2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useAuth, useOrganizationId } from '@/app/providers/AuthProvider'
import { useBranchScope } from '@/app/providers/BranchProvider'
import { branchesApi } from '@/features/branches/api'
import { queryKeys } from '@/lib/api/queryKeys'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'
import { Select } from '@/components/ui/Select'

interface BranchSwitcherProps {
  /**
   * `topbar` — `sm` dan tor ekranda yashirin (joy yo'q);
   * `drawer` — mobil menyu ichida, to'liq kenglikda.
   */
  variant?: 'topbar' | 'drawer'
}

export function BranchSwitcher({ variant = 'topbar' }: BranchSwitcherProps) {
  const inDrawer = variant === 'drawer'
  const { user } = useAuth()
  const organizationId = useOrganizationId()
  const { selectedBranchId, setSelectedBranchId } = useBranchScope()

  const isOrgOwner = user?.role?.code === 'org_owner'

  const branchesQuery = useQuery({
    queryKey: queryKeys.branches(organizationId),
    queryFn: branchesApi.list,
    enabled: isOrgOwner,
  })

  // Org Owner bo'lmaganlarda o'z filiali oddiy yorliq sifatida ko'rsatiladi.
  if (!isOrgOwner) {
    if (!user?.branch) return null
    return (
      <div
        className={cn(
          'items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600',
          inDrawer ? 'mx-3 my-3 flex sm:hidden' : 'hidden sm:flex',
        )}
      >
        <Building2 className="h-4 w-4 text-slate-500" />
        {user.branch.name}
      </div>
    )
  }

  return (
    <div
      className={cn(
        'relative',
        inDrawer ? 'block border-b border-slate-100 px-3 py-3 sm:hidden' : 'hidden sm:block',
      )}
    >
      {/* Belgi va strelka — `Select` ning oʻzida (2026-10-23): ilgari
          ular bu yerda qoʻlda joylashtirilgan edi va yangi
          komponentning strelkasi bilan ikkitaga aylangan boʻlardi. */}
      <Select
        icon={Building2}
        aria-label={t('Filial')}
        value={selectedBranchId ?? ''}
        onChange={(event) => setSelectedBranchId(event.target.value || null)}
        className={inDrawer ? 'w-full' : 'w-auto'}
      >
        <option value="">{t('Barcha filiallar')}</option>
        {branchesQuery.data?.items.map((branch) => (
          <option key={branch.id} value={branch.id}>
            {branch.name}
          </option>
        ))}
      </Select>
    </div>
  )
}
