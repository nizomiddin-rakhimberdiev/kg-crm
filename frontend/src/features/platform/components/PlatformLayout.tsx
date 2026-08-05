/**
 * Vendor konsoli qobig'i.
 *
 * Mijoz layoutidan butunlay alohida va **qorong'i**: ikki tekislikni
 * adashtirish xavfli, va rang farqi buni bir qarashda hal qiladi.
 * "Men hozir qaysi rejimda turibman?" degan savol hech qachon
 * tug'ilmasligi kerak.
 */

import { NavLink, Navigate, Outlet } from 'react-router-dom'
import { Building2, CreditCard, KeyRound, LayoutDashboard, LogOut, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePlatformAuth } from '../PlatformAuthProvider'

const NAV = [
  { to: '/platform', label: 'Ish ro‘yxati', icon: LayoutDashboard, end: true },
  { to: '/platform/organizations', label: 'Bog‘chalar', icon: Building2, end: false },
  { to: '/platform/invoices', label: 'Hisob-fakturalar', icon: CreditCard, end: false },
  { to: '/platform/grants', label: 'Kirish ruxsatlari', icon: KeyRound, end: false },
]

export function PlatformLayout() {
  const { user, isAuthenticated, logout } = usePlatformAuth()

  if (!isAuthenticated) return <Navigate to="/platform/login" replace />

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-6 py-3">
          <div className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600">
              <ShieldCheck className="h-4 w-4 text-white" />
            </div>
            <span className="text-sm font-semibold">Platforma konsoli</span>
          </div>

          <nav className="flex flex-wrap items-center gap-1">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200',
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-medium">{user?.full_name}</p>
              <p className="text-xs text-slate-500">
                {user?.role === 'platform_admin' ? 'Administrator' : 'Qo‘llab-quvvatlash'}
              </p>
            </div>
            <button
              type="button"
              onClick={logout}
              title="Chiqish"
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <Outlet />
      </main>
    </div>
  )
}
