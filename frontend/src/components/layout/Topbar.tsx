import { Bell, LogOut, Menu, Search, Volume2, VolumeX } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Avatar } from '@/components/ui/Avatar'
import { useAuth } from '@/app/providers/AuthProvider'
import { useSound } from '@/app/providers/SoundProvider'
import { BranchSwitcher } from './BranchSwitcher'

interface TopbarProps {
  /** Mobil menyuni ochish — tugma faqat `lg` dan tor ekranda ko'rinadi. */
  onMenuClick: () => void
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const { muted, toggle } = useSound()
  const { user, logout } = useAuth()

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-slate-200 bg-white/90 px-3 backdrop-blur sm:gap-3 sm:px-4 lg:h-16 lg:gap-4 lg:px-6">
      {/* Hamburger — yon panel yashiringan ekranlarda yagona kirish yo'li. */}
      <button
        type="button"
        onClick={onMenuClick}
        aria-label="Menyuni ochish"
        className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-slate-600 transition-colors hover:bg-slate-100 active:scale-95 lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Search — planshetdan boshlab; telefonda joy yo'q. */}
      <div className="relative hidden max-w-md flex-1 md:block">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Ism yoki ID bo'yicha qidiruv..."
          className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-4 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
        />
      </div>

      <div className="ml-auto flex items-center gap-1 sm:gap-2 lg:gap-3">
        <BranchSwitcher />

        {/* Sound toggle */}
        <button
          onClick={toggle}
          data-sound="toggle"
          title={muted ? 'Ovozni yoqish' : "Ovozni o'chirish"}
          className="hidden h-10 w-10 place-items-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 active:scale-95 sm:grid"
        >
          {muted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
        </button>

        {/* Notifications */}
        <Link
          to="/notifications"
          title="Bildirishnomalar"
          className="relative grid h-10 w-10 place-items-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 active:scale-95"
        >
          <Bell className="h-5 w-5" />
        </Link>

        {/* Profil — haqiqiy foydalanuvchi, profil sahifasiga havola */}
        {user && (
          <div className="flex items-center gap-1 sm:pl-2">
            <Link
              to="/profile"
              title="Profil"
              className="flex items-center gap-2 rounded-lg px-1 py-1 transition-colors hover:bg-slate-100 sm:px-2"
            >
              <Avatar
                name={user.full_name}
                photoUrl={user.photo_url}
                className="h-9 w-9"
                textClassName="text-xs"
              />
              <span className="hidden text-left leading-tight md:block">
                <span className="block max-w-[160px] truncate text-sm font-semibold text-slate-900">
                  {user.full_name}
                </span>
                <span className="block text-[11px] text-slate-400">
                  {user.role?.name ?? '—'}
                </span>
              </span>
            </Link>

            {/* Chiqish — telefonda drawer ichida; bu yerda faqat `sm+`. */}
            <button
              type="button"
              onClick={() => void logout()}
              title="Chiqish"
              className="hidden h-10 w-10 place-items-center rounded-lg text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 active:scale-95 sm:grid"
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
