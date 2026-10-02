/**
 * Vendor konsoli qobig'i.
 *
 * Mijoz layoutidan butunlay alohida va **qorong'i**: ikki tekislikni
 * adashtirish xavfli, va rang farqi buni bir qarashda hal qiladi.
 * "Men hozir qaysi rejimda turibman?" degan savol hech qachon
 * tug'ilmasligi kerak.
 */

import { Suspense } from 'react'
import { NavLink, Navigate, Outlet } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { useQuery } from '@tanstack/react-query'
import { Building2, CreditCard, Inbox, KeyRound, LayoutDashboard, LogOut } from 'lucide-react'
import { RadixMark } from '@/components/brand/Logo'
import { cn } from '@/lib/utils'
import { platform } from '../api'
import { usePlatformAuth } from '../PlatformAuthProvider'

const NAV = [
  { to: '/platform', label: 'Ish ro‘yxati', icon: LayoutDashboard, end: true },
  { to: '/platform/leads', label: 'So‘rovlar', icon: Inbox, end: false },
  { to: '/platform/organizations', label: 'Bog‘chalar', icon: Building2, end: false },
  { to: '/platform/invoices', label: 'Hisob-fakturalar', icon: CreditCard, end: false },
  { to: '/platform/grants', label: 'Kirish ruxsatlari', icon: KeyRound, end: false },
]

export function PlatformLayout() {
  const { user, isAuthenticated, logout } = usePlatformAuth()

  // Yangi so'rovlar soni — menyuda belgi. Saytdan kelgan ariza bazaga
  // tushib, hech kim ko'rmay qolishi mumkin edi; endi u ko'z oldida.
  const leads = useQuery({
    queryKey: ['platform', 'leads', 'counts'],
    queryFn: () => platform.leads(),
    enabled: isAuthenticated && user?.role === 'platform_admin',
    staleTime: 60_000,
    refetchInterval: 120_000,
  })
  const newLeads = leads.data?.counts.new ?? 0

  if (!isAuthenticated) return <Navigate to="/platform/login" replace />

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4 px-6 py-3">
          <div className="flex items-center gap-2">
            <RadixMark size={32} variant="dark" />
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
                {item.to === '/platform/leads' && newLeads > 0 && (
                  <span className="ml-1 rounded-full bg-brand-600 px-1.5 text-xs font-bold text-white">
                    {newLeads}
                  </span>
                )}
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
              aria-label="Chiqish"
              className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <Suspense
          fallback={
            <div className="grid place-items-center py-20 text-sm text-slate-400">Yuklanmoqda…</div>
          }
        >
          <ErrorBoundary area="platform">
            <Outlet />
          </ErrorBoundary>
        </Suspense>
      </main>
    </div>
  )
}
