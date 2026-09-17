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
  BellRing,
  ScrollText,
  CreditCard as CreditCardIcon,
  Building2,
  Users2,
  type LucideIcon,
} from 'lucide-react'
import type { PermissionCode } from '@/lib/rbac/useCan'
import { env } from '@/config/env'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /** Shu punktni ko'rsatish uchun zarur ruxsat (docs/02 §11.3). */
  permission: PermissionCode
}

/**
 * Sidebar navigatsiyasi — har bir punkt ruxsat bilan bog'langan.
 *
 * Bu **UX**, xavfsizlik emas: yashirilgan sahifaga to'g'ridan-to'g'ri URL
 * bilan kirilsa ham backend rad etadi. Yashirish shunchaki ishlamaydigan
 * tugmani ko'rsatmaslik uchun.
 */
const allNavItems: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard, permission: 'dashboard.read' },
  { label: 'Bolalar', to: '/children', icon: Users, permission: 'children.read' },
  { label: 'Guruhlar', to: '/groups', icon: Users2, permission: 'children.read' },
  { label: "To'lovlar", to: '/payments', icon: CreditCard, permission: 'payments.read' },
  { label: 'Qarzdorlar', to: '/debtors', icon: AlertTriangle, permission: 'debtors.read' },
  { label: 'Davomat', to: '/attendance', icon: CalendarCheck, permission: 'attendance.read' },
  { label: 'Xodimlar', to: '/staff', icon: UserCog, permission: 'users.read' },
  { label: 'Oylik', to: '/payroll', icon: Wallet, permission: 'payroll.read' },
  { label: 'Ombor', to: '/inventory', icon: Package, permission: 'inventory.read' },
  { label: 'Chiqimlar', to: '/expenses', icon: Receipt, permission: 'expenses.read' },
  { label: 'Hisobotlar', to: '/reports', icon: BarChart3, permission: 'reports.read' },
  { label: 'Bildirishnomalar', to: '/notifications', icon: BellRing, permission: 'notifications.read' },
  { label: 'Filiallar', to: '/branches', icon: Building2, permission: 'branches.read' },
  { label: 'Obuna', to: '/billing', icon: CreditCardIcon, permission: 'billing.read' },
  { label: 'Audit jurnali', to: '/audit', icon: ScrollText, permission: 'audit.read' },
  { label: 'Sozlamalar', to: '/settings', icon: Settings, permission: 'settings.read' },
]

/**
 * Standalone nusxada ko'rinmaydigan punktlar (docs/02 ADR-13).
 *
 * Bu — tozalik, himoya emas: backend bu yo'llarni standalone'da
 * umuman marshrutlamaydi (`api/v1/router.py`), ya'ni menyu qolib
 * ketganda ham sahifa bo'sh javob olardi.
 */
const SAAS_ONLY_ROUTES = new Set(['/billing'])

export const navItems: NavItem[] = env.isStandalone
  ? allNavItems.filter((item) => !SAAS_ONLY_ROUTES.has(item.to))
  : allNavItems
