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
  Sparkles,
  Cctv,
  type LucideIcon,
} from 'lucide-react'
import type { PermissionCode } from '@/lib/rbac/useCan'
import { env } from '@/config/env'
import { t } from '@/lib/i18n'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  /**
   * Shu punktni ko'rsatish uchun zarur ruxsat (docs/02 §11.3).
   * Ro'yxat berilsa — istalgan bittasi yetarli (masalan, "Xodimlar"
   * sahifasi HR ro'yxatini `payroll.read`, tizim hisoblarini
   * `users.read` bilan ko'rsatadi).
   */
  permission: PermissionCode | PermissionCode[]
}

/**
 * Sidebar navigatsiyasi — har bir punkt ruxsat bilan bog'langan.
 *
 * Bu **UX**, xavfsizlik emas: yashirilgan sahifaga to'g'ridan-to'g'ri URL
 * bilan kirilsa ham backend rad etadi. Yashirish shunchaki ishlamaydigan
 * tugmani ko'rsatmaslik uchun.
 */
const allNavItems: NavItem[] = [
  { label: t('Dashboard'), to: '/dashboard', icon: LayoutDashboard, permission: 'dashboard.read' },
  { label: t('Bolalar'), to: '/children', icon: Users, permission: 'children.read' },
  { label: t('Guruhlar'), to: '/groups', icon: Users2, permission: 'children.read' },
  { label: t("To'lovlar"), to: '/payments', icon: CreditCard, permission: 'payments.read' },
  { label: t('Qarzdorlar'), to: '/debtors', icon: AlertTriangle, permission: 'debtors.read' },
  { label: t('Davomat'), to: '/attendance', icon: CalendarCheck, permission: 'attendance.read' },
  { label: t('Xodimlar'), to: '/staff', icon: UserCog, permission: ['payroll.read', 'users.read'] },
  { label: t('Oylik maosh'), to: '/payroll', icon: Wallet, permission: 'payroll.read' },
  { label: t('Ombor'), to: '/inventory', icon: Package, permission: 'inventory.read' },
  { label: t('Chiqimlar'), to: '/expenses', icon: Receipt, permission: 'expenses.read' },
  // Hisobotlar sahifasi MOLIYAVIY (tushum, chiqim, oylik maosh, foyda-zarar),
  // shuning uchun `reports.read` ning o'zi yetarli emas: Davomat menejerida
  // u bor, lekin har bir bo'lim `403` qaytarardi va ekran yarim bo'sh
  // xatolarga to'lardi (docs/02 §11.2 — "R (attendance only)").
  {
    label: t('Hisobotlar'),
    to: '/reports',
    icon: BarChart3,
    permission: ['payments.read', 'expenses.read', 'payroll.read'],
  },
  {
    label: t('Bildirishnomalar'),
    to: '/notifications',
    icon: BellRing,
    permission: 'notifications.read',
  },
  { label: t('Radix AI'), to: '/radix-ai', icon: Sparkles, permission: 'memories.read' },
  { label: t('Kameralar'), to: '/cameras', icon: Cctv, permission: 'memories.read' },
  { label: t('Filiallar'), to: '/branches', icon: Building2, permission: 'branches.read' },
  { label: t('Obuna'), to: '/billing', icon: CreditCardIcon, permission: 'billing.read' },
  { label: t('Audit jurnali'), to: '/audit', icon: ScrollText, permission: 'audit.read' },
  { label: t('Sozlamalar'), to: '/settings', icon: Settings, permission: 'settings.read' },
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

/**
 * Kirgandan keyin ochiladigan sahifa — foydalanuvchining RUXSATIGA qarab.
 *
 * Ilgari hamma joyda `/dashboard` qotib yozilgan edi. Tizim rollarining
 * hammasida `dashboard.read` bor, shuning uchun bu hech qachon sezilmadi —
 * lekin bog'cha egasi QO'LDA rol yasab (masalan "Tarbiyachi": bolalar,
 * guruhlar, davomat) boshqaruv panelini belgilamasa, o'sha xodim kirishi
 * bilan ruxsati yo'q sahifaga tushardi va ekranda ma'lumot emas,
 * "Ko'rsatkichlarni yuklab bo'lmadi" degan xato ko'rinardi.
 *
 * Endi kirish nuqtasi menyudagi BIRINCHI ochiq bo'limga olib boradi:
 * qanday rol yasalsa ham, odam o'ziga ruxsat berilgan ishni ko'radi.
 * Hech qanday ruxsati yo'q bo'lsa — profil, u har kimga ochiq.
 */
export function landingPathFor(
  allowed: (permission: PermissionCode | PermissionCode[]) => boolean,
): string {
  return navItems.find((item) => allowed(item.permission))?.to ?? '/profile'
}
