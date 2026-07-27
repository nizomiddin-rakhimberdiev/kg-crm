import {
  LayoutDashboard,
  Users,
  CreditCard,
  AlertTriangle,
  CalendarCheck,
  UserCog,
  Wallet,
  Package,
  Receipt,
  BarChart3,
  Settings,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
}

/** Sidebar navigation — mirrors the modules in the design. */
export const navItems: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Bolalar', to: '/children', icon: Users },
  { label: "To'lovlar", to: '/payments', icon: CreditCard },
  { label: 'Qarzdorlar', to: '/debtors', icon: AlertTriangle },
  { label: 'Davomat', to: '/attendance', icon: CalendarCheck },
  { label: 'Xodimlar', to: '/staff', icon: UserCog },
  { label: 'Oylik', to: '/payroll', icon: Wallet },
  { label: 'Ombor', to: '/inventory', icon: Package },
  { label: 'Chiqimlar', to: '/expenses', icon: Receipt },
  { label: 'Hisobotlar', to: '/reports', icon: BarChart3 },
  { label: 'Sozlamalar', to: '/settings', icon: Settings },
]
