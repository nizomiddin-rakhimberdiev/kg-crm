/**
 * Xodimlar — bitta sahifa, uch tab.
 *
 *   • Xodimlar         — HR ro'yxati (`/employees`, `payroll.read`):
 *                        oylik oladigan har bir odam.
 *   • Tizim hisoblari  — login bilan kiruvchilar (`/users`, `users.read`).
 *   • Rollar           — ruxsatlar matritsasi (`users.read`).
 *
 * Avval bu sahifa faqat tizim hisoblarini ko'rsatardi, HR ro'yxati esa
 * "Oylik" sahifasining ichida yashiringan edi — direktor "Xodimlar"ni
 * ochib, o'nta xodimdan bittasini (o'zini) ko'rar edi. Ikki tushuncha
 * ataylab alohida (docs/02 §6), lekin ikkalasi ham "xodim" so'zi bilan
 * qidiriladi — shuning uchun bitta sahifa.
 *
 * Tab URL'da (`?tab=accounts`) — boshqa sahifadan to'g'ridan-to'g'ri
 * havola berish mumkin, va yangilash tabni yo'qotmaydi.
 */

import { useSearchParams } from 'react-router-dom'
import { AccountsPanel } from '@/features/staff/components/AccountsPanel'
import { EmployeesPanel } from '@/features/staff/components/EmployeesPanel'
import { RolesPanel } from '@/features/staff/components/RolesPanel'
import { useCan, type PermissionCode } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { t } from '@/lib/i18n'

type Tab = 'employees' | 'accounts' | 'roles'

const TABS: Array<{ key: Tab; label: string; permission: PermissionCode }> = [
  { key: 'employees', label: t('Xodimlar'), permission: 'payroll.read' },
  { key: 'accounts', label: t('Tizim hisoblari'), permission: 'users.read' },
  { key: 'roles', label: t('Rollar va ruxsatlar'), permission: 'users.read' },
]

export default function StaffPage() {
  const { can } = useCan()
  const [searchParams, setSearchParams] = useSearchParams()

  const visibleTabs = TABS.filter((tab) => can(tab.permission))
  const requested = searchParams.get('tab') as Tab | null
  // Ruxsat bo'lmagan yoki noma'lum tab so'ralsa — birinchi ochiq tab.
  const tab: Tab | undefined =
    visibleTabs.find((t) => t.key === requested)?.key ?? visibleTabs[0]?.key

  const selectTab = (next: Tab) => {
    const params = new URLSearchParams(searchParams)
    if (next === visibleTabs[0]?.key) params.delete('tab')
    else params.set('tab', next)
    setSearchParams(params, { replace: true })
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{t('Xodimlar')}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {t("Xodimlar soni cheklanmagan — narx faqat bolalar soniga bog'liq.")}
        </p>
      </div>

      {visibleTabs.length > 1 && (
        <div className="-mx-3 overflow-x-auto px-3 sm:mx-0 sm:px-0">
          <div className="flex min-w-max gap-1 border-b border-slate-200">
            {visibleTabs.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => selectTab(key)}
                className={cn(
                  '-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition sm:px-4',
                  tab === key
                    ? 'border-brand-600 text-brand-700'
                    : 'border-transparent text-slate-500 hover:text-slate-800',
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {tab === 'employees' && <EmployeesPanel />}
      {tab === 'accounts' && <AccountsPanel />}
      {tab === 'roles' && <RolesPanel />}
    </div>
  )
}
