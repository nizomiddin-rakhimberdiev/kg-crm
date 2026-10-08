import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { LogOut, X } from 'lucide-react'
import { useFocusTrap } from '@/lib/useFocusTrap'
import { OrgMark } from '@/components/brand/OrgMark'
import { Avatar } from '@/components/ui/Avatar'
import { useAuth } from '@/app/providers/AuthProvider'
import { SECTION_LABEL, SECTION_ORDER, navItems, type NavItem } from '@/config/navigation'
import { useCan } from '@/lib/rbac/useCan'
import { cn } from '@/lib/utils'
import { BranchSwitcher } from './BranchSwitcher'
import { LanguageSwitch } from './LanguageSwitch'
import { t } from '@/lib/i18n'

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
        title={t('Bogʻcha profili')}
        onClick={onNavigate}
        className="flex h-16 shrink-0 items-center gap-3 border-b border-slate-100 px-5 transition-colors hover:bg-slate-50 lg:px-6"
      >
        {/*
          Belgi — BOG'CHANING logotipi yoki bosh harfi (PLAN 4.6).
          Yonidagi yozuv ham bog'chaning o'z nomi: mudira kun bo'yi
          o'z ishxonasini ko'rib turadi, mahsulot namoyishini emas.
        */}
        <OrgMark name={user?.organization?.name} logoUrl={user?.organization?.logo_url} size={36} />
        <div className="min-w-0 leading-tight">
          <p className="truncate text-sm font-bold text-tosh-900">
            {user?.organization?.name ?? t('Radix CRM')}
          </p>
          <p className="text-xs font-medium tracking-wide text-tosh-500">{t('Boshqaruv Tizimi')}</p>
        </div>
      </NavLink>

      {/* Filial — faqat drawer'da: Topbar'da u `sm` dan pastda yashirin. */}
      <BranchSwitcher variant="drawer" />

      {/* Nav — boʻlimlarga ajratilgan (PLAN 4.5). Ruxsati yoʻq
          boʻlim butunlay koʻrinmaydi: bitta ham punkti qolmagan
          sarlavha faqat shovqin. */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        {SECTION_ORDER.map((section) => {
          const items = visibleItems.filter((item) => item.section === section)
          if (items.length === 0) return null
          return (
            <div key={section} className="mb-4 last:mb-0">
              {SECTION_LABEL[section] && (
                <p className="mb-1 px-3 text-xs font-semibold tracking-wide text-tosh-500">
                  {SECTION_LABEL[section]}
                </p>
              )}
              <div className="space-y-1">
                {items.map((item) => (
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
                          className={cn(
                            'h-[18px] w-[18px]',
                            isActive ? 'text-brand-600' : 'text-slate-500',
                          )}
                        />
                        {item.label}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          )
        })}
      </nav>

      {/* Profile footer */}
      <div className="shrink-0 border-t border-slate-100 p-4">
        {/* Til — faqat drawer'da: keng ekranda u Topbar'da. */}
        <LanguageSwitch
          size="md"
          className="mb-3 w-full justify-stretch [&>button]:flex-1 lg:hidden"
        />
        <div className="flex items-center gap-3">
          {/* Profil — ruxsat talab qilmaydi: har kim faqat o'zini ko'radi. */}
          <NavLink
            to="/profile"
            title={t('Mening profilim')}
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
              {/* Rol nomi AYNAN bazadagidek: CSS `uppercase` uni
                  "TARBIYACHI" qilib ko'rsatardi, qolgan ekranlarda esa
                  "Tarbiyachi" turardi (PLAN 4.3). O'lcham 12px —
                  undan kichigi o'qilmaydi (PLAN 4.8). */}
              <p className="truncate text-xs text-slate-500">{user?.role?.name ?? '—'}</p>
            </div>
          </NavLink>
          <button
            type="button"
            onClick={() => void logout()}
            title={t('Chiqish')}
            aria-label={t('Chiqish')}
            className="shrink-0 rounded-lg p-2 text-slate-500 transition hover:bg-slate-50 hover:text-slate-700"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>

        {/* Mahsulot nomi PASTDA va kichik (PLAN 4.6): sarlavhada
            bogʻchaning brendi turadi, bizning nomimiz esa shu
            yerda — koʻrinadigan, lekin daʼvo qilmaydigan joyda. */}
        <p className="mt-3 text-center text-xs text-tosh-500">{t('Radix CRM')}</p>
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
  const drawer = useFocusTrap<HTMLElement>(open)

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
            ref={drawer}
            role="dialog"
            aria-modal="true"
            aria-label={t('Asosiy menyu')}
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-white shadow-2xl"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }}
          >
            <button
              type="button"
              onClick={onClose}
              aria-label={t('Menyuni yopish')}
              className="absolute right-3 top-3.5 grid h-9 w-9 place-items-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
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
