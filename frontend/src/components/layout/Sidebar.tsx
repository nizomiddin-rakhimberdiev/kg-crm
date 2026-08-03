import { NavLink } from 'react-router-dom'
import { GraduationCap, LogOut } from 'lucide-react'
import { useAuth } from '@/app/providers/AuthProvider'
import { navItems } from '@/config/navigation'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'

const initials = (name: string) =>
  name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('') || '?'

export function Sidebar() {
  const { user, logout } = useAuth()
  const { can } = useCan()

  // Nav ruxsat bo'yicha filtrlanadi — foydalanuvchi ochib bo'lmaydigan
  // sahifani ko'rmasin. Bu UX; haqiqiy to'siq backend'da.
  const visibleItems = navItems.filter((item) => can(item.permission))

  return (
    <aside className="hidden lg:flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
      {/* Brand */}
      <div className="flex items-center gap-3 px-6 h-16 border-b border-slate-100">
        <div className="grid place-items-center w-9 h-9 rounded-xl bg-brand-600 text-white">
          <GraduationCap className="w-5 h-5" />
        </div>
        <div className="leading-tight min-w-0">
          <p className="truncate text-sm font-bold text-slate-900">
            {user?.organization?.name ?? 'KG-CRM'}
          </p>
          <p className="text-[11px] text-slate-400 font-medium tracking-wide">
            Boshqaruv Tizimi
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto scrollbar-thin px-3 py-4 space-y-1">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            data-sound="nav"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900',
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn('w-[18px] h-[18px]', isActive ? 'text-brand-600' : 'text-slate-400')}
                />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Profile footer */}
      <div className="border-t border-slate-100 p-4">
        <div className="flex items-center gap-3">
          <div className="grid place-items-center w-9 h-9 shrink-0 rounded-full bg-slate-800 text-white text-xs font-semibold">
            {initials(user?.full_name ?? '')}
          </div>
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-sm font-semibold text-slate-900">
              {user?.full_name ?? '—'}
            </p>
            <p className="truncate text-[11px] text-slate-400 uppercase tracking-wide">
              {user?.role?.name ?? '—'}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void logout()}
            title="Chiqish"
            className="shrink-0 rounded-lg p-2 text-slate-400 transition hover:bg-slate-50 hover:text-slate-700"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
