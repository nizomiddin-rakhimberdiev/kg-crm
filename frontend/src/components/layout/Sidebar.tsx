import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { GraduationCap, LogOut, X } from 'lucide-react'
import { Avatar } from '@/components/ui/Avatar'
import { useAuth } from '@/app/providers/AuthProvider'
import { navItems, type NavItem } from '@/config/navigation'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { BranchSwitcher } from './BranchSwitcher'

/**
 * Yon panel ikki qobiqda yashaydi: `lg` dan yuqorida doimiy `<aside>`,
 * undan pastda (telefon, planshet) — chapdan chiqadigan drawer.
 * Ikkalasi ham BITTA `SidebarContent` ni render qiladi: menyu punktlari,
 * ruxsat filtri va profil ikki joyda takrorlanmaydi, ya'ni yangi punkt
 * qo'shilganda mobil menyu "unutilib" qolmaydi.
 */

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user, logout } = useAuth()
  const { can, canAny } = useCan()

  // Nav ruxsat bo'yicha filtrlanadi — foydalanuvchi ochib bo'lmaydigan
  // sahifani ko'rmasin. Bu UX; haqiqiy to'siq backend'da.
  const allowed = (item: NavItem) =>
    Array.isArray(item.permission) ? canAny(...item.permission) : can(item.permission)
  const visibleItems = navItems.filter(allowed)

  return (
    <>
      {/* Brand */}
      <NavLink
        to="/organization"
        title="Bog'cha profili"
        onClick={onNavigate}
        className="flex h-16 shrink-0 items-center gap-3 border-b border-slate-100 px-5 transition-colors hover:bg-slate-50 lg:px-6"
      >
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand-600 text-white">
          <GraduationCap className="h-5 w-5" />
        </div>
        <div className="min-w-0 leading-tight">
          <p className="truncate text-sm font-bold text-slate-900">
            {user?.organization?.name ?? 'Radix CRM'}
          </p>
          <p className="text-[11px] font-medium tracking-wide text-slate-400">
            Boshqaruv Tizimi
          </p>
        </div>
      </NavLink>

      {/* Filial — faqat drawer'da: Topbar'da u `sm` dan pastda yashirin. */}
      <BranchSwitcher variant="drawer" />

      {/* Nav */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            data-sound="nav"
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                // Sensorli ekranda 44px balandlik — barmoq uchun minimal nishon.
                'flex min-h-[44px] items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors lg:min-h-0',
                isActive
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900',
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn('h-[18px] w-[18px]', isActive ? 'text-brand-600' : 'text-slate-400')}
                />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Profile footer */}
      <div className="shrink-0 border-t border-slate-100 p-4">
        <div className="flex items-center gap-3">
          {/* Profil — ruxsat talab qilmaydi: har kim faqat o'zini ko'radi. */}
          <NavLink
            to="/profile"
            title="Mening profilim"
            onClick={onNavigate}
            className="-m-1 flex min-w-0 flex-1 items-center gap-3 rounded-lg p-1 transition-colors hover:bg-slate-50"
          >
            <Avatar
              name={user?.full_name ?? '—'}
              photoUrl={user?.photo_url}
              className="h-9 w-9"
              textClassName="text-xs"
            />
            <div className="min-w-0 flex-1 leading-tight">
              <p className="truncate text-sm font-semibold text-slate-900">
                {user?.full_name ?? '—'}
              </p>
              <p className="truncate text-[11px] uppercase tracking-wide text-slate-400">
                {user?.role?.name ?? '—'}
              </p>
            </div>
          </NavLink>
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
    </>
  )
}

/** Doimiy yon panel — `lg` va undan keng ekranlar. */
export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
      <SidebarContent />
    </aside>
  )
}

interface MobileSidebarProps {
  open: boolean
  onClose: () => void
}

/**
 * Mobil drawer — `lg` dan tor ekranlar uchun.
 *
 * Portal orqali `<body>` ga chiqariladi: AppLayout ichidagi sahifa
 * animatsiyasi `transform` qo'llaydi va u `position: fixed` ni
 * ekranga emas, o'ziga nisbatan joylashtirardi (Modal bilan bir xil
 * sabab). Yopilish: fon bosilganda, Escape'da va marshrut o'zgarganda.
 */
export function MobileSidebar({ open, onClose }: MobileSidebarProps) {
  const location = useLocation()
  const previousPath = useRef(location.pathname)

  // Marshrut o'zgarganda drawer yopiladi — foydalanuvchi punktni bosdi,
  // sahifa ochildi, menyu esa uni to'sib turmasligi kerak.
  useEffect(() => {
    if (previousPath.current !== location.pathname) {
      previousPath.current = location.pathname
      onClose()
    }
  }, [location.pathname, onClose])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[90] lg:hidden">
          <motion.div
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={onClose}
          />
          <motion.aside
            role="dialog"
            aria-modal="true"
            aria-label="Asosiy menyu"
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-white shadow-2xl"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
          >
            <button
              type="button"
              onClick={onClose}
              aria-label="Menyuni yopish"
              className="absolute right-3 top-3.5 grid h-9 w-9 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent onNavigate={onClose} />
          </motion.aside>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
