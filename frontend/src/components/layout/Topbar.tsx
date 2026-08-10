import { Bell, LogOut, Search, Volume2, VolumeX } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Avatar } from '@/components/ui/Avatar'
import { useAuth } from '@/app/providers/AuthProvider'
import { useSound } from '@/app/providers/SoundProvider'
import { BranchSwitcher } from './BranchSwitcher'

/** "Abzal Azlarov" → "AA" */
export function Topbar() {
  const { muted, toggle } = useSound()
  const { user, logout } = useAuth()

  return (
    <header className="sticky top-0 z-20 flex items-center gap-4 h-16 px-4 lg:px-6 border-b border-slate-200 bg-white/90 backdrop-blur">
      {/* Search */}
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Ism yoki ID bo'yicha qidiruv..."
          className="w-full rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-4 py-2 text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-400"
        />
      </div>

      <div className="ml-auto flex items-center gap-3">
        <BranchSwitcher />

        {/* Sound toggle */}
        <button
          onClick={toggle}
          data-sound="toggle"
          title={muted ? 'Ovozni yoqish' : "Ovozni o'chirish"}
          className="grid place-items-center w-10 h-10 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors active:scale-95"
        >
          {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
        </button>

        {/* Notifications */}
        <Link
          to="/notifications"
          title="Bildirishnomalar"
          className="relative grid place-items-center w-10 h-10 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors active:scale-95"
        >
          <Bell className="w-5 h-5" />
        </Link>

        {/* Profil — haqiqiy foydalanuvchi, profil sahifasiga havola */}
        {user && (
          <div className="flex items-center gap-1 pl-2">
            <Link
              to="/profile"
              title="Profil"
              className="flex items-center gap-2 rounded-lg px-2 py-1 transition-colors hover:bg-slate-100"
            >
              <Avatar
                name={user.full_name}
                photoUrl={user.photo_url}
                className="h-9 w-9"
                textClassName="text-xs"
              />
              <span className="hidden sm:block leading-tight text-left">
                <span className="block text-sm font-semibold text-slate-900">
                  {user.full_name}
                </span>
                <span className="block text-[11px] text-slate-400">
                  {user.role?.name ?? '—'}
                </span>
              </span>
            </Link>

            <button
              type="button"
              onClick={() => void logout()}
              title="Chiqish"
              className="grid place-items-center w-10 h-10 rounded-lg text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600 active:scale-95"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
