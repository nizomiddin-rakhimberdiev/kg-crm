import { Bell, Search, Volume2, VolumeX } from 'lucide-react'
import { useSound } from '@/app/providers/SoundProvider'
import { BranchSwitcher } from './BranchSwitcher'

export function Topbar() {
  const { muted, toggle } = useSound()

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
          title={muted ? "Ovozni yoqish" : "Ovozni o'chirish"}
          className="grid place-items-center w-10 h-10 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors active:scale-95"
        >
          {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
        </button>

        {/* Notifications */}
        <button className="relative grid place-items-center w-10 h-10 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors active:scale-95">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-red-500 ring-2 ring-white" />
        </button>

        {/* Profile */}
        <div className="flex items-center gap-2 pl-2">
          <div className="grid place-items-center w-9 h-9 rounded-full bg-brand-600 text-white text-xs font-semibold">
            AD
          </div>
          <div className="hidden sm:block leading-tight">
            <p className="text-sm font-semibold text-slate-900">Admin Profili</p>
            <p className="text-[11px] text-slate-400">Boshqaruvchi</p>
          </div>
        </div>
      </div>
    </header>
  )
}
