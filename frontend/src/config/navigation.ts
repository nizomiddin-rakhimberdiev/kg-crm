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
  Vault,
  Gauge,
  type LucideIcon,
} from 'lucide-react'
import type { PermissionCode } from '@/lib/rbac/useCan'
import { env } from '@/config/env'
import { t } from '@/lib/i18n'

/**
 * Menyu boʻlimi (PLAN 4.5).
 *
 * Oʻn uchta punkt bitta roʻyxatda turganda ular orasida maʼnoviy
 * bogʻlanish koʻrinmaydi: "Qarzdorlar" bilan "Ombor" yonma-yon
 * turardi. Boʻlimlar mudiraga kun tartibini beradi — bolalar,
 * moliya, xodimlar — va yangi punkt qoʻshilganda uning joyi oʻz-oʻzidan
 * aniq boʻladi.
 */
export type NavSection = 'main' | 'children' | 'finance' | 'staff' | 'inventory' | 'system'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  section: NavSection
  /**
   * Shu punktni ko'rsatish uchun zarur ruxsat (docs/02 §11.3).
   * Ro'yxat berilsa — istalgan bittasi yetarli (masalan, "Xodimlar"
   * sahifasi HR ro'yxatini `payroll.read`, tizim hisoblarini
   * `users.read` bilan ko'rsatadi).
   */
  permission: PermissionCode | PermissionCode[]
  /**
   * Qo'shimcha SHART — `permission` ga QO'SHIMCHA ravishda shu ham
   * bo'lishi kerak. Hisobotlar uchun: moliya ruxsatlaridan biri VA
   * `reports.read`. Usiz kassir (ADR-30) hisobotlar sahifasini ko'rardi,
   * backend esa har bir bo'limda `403` qaytarardi.
   */
  requires?: PermissionCode
}

/**
 * Sidebar navigatsiyasi — har bir punkt ruxsat bilan bog'langan.
 *
 * Bu **UX**, xavfsizlik emas: yashirilgan sahifaga to'g'ridan-to'g'ri URL
 * bilan kirilsa ham backend rad etadi. Yashirish shunchaki ishlamaydigan
 * tugmani ko'rsatmaslik uchun.
 */
const allNavItems: NavItem[] = [
  {
    label: t('Dashboard'),
    to: '/dashboard',
    section: 'main',
    icon: LayoutDashboard,
    permission: 'dashboard.read',
  },
  {
    label: t('Bolalar'),
    to: '/children',
    section: 'children',
    icon: Users,
    permission: 'children.read',
  },
  {
    label: t('Guruhlar'),
    to: '/groups',
    section: 'children',
    icon: Users2,
    permission: 'children.read',
  },
  // Moliya markazi (Bosqich 13.4): bugun, kun, nazorat, oylik hisobot.
  // `reports.finance` — faqat jami summalar (ADR-42), shuning uchun ega
  // uni boshqaruvchiga bera oladi; `payroll.read` ham ochadi.
  {
    label: t('Moliya markazi'),
    to: '/finance',
    section: 'finance',
    icon: Gauge,
    permission: ['reports.finance', 'payroll.read'],
    requires: 'reports.read',
  },
  {
    label: t('Toʻlovlar'),
    to: '/payments',
    section: 'finance',
    icon: CreditCard,
    permission: 'payments.read',
  },
  {
    label: t('Qarzdorlar'),
    to: '/debtors',
    section: 'finance',
    icon: AlertTriangle,
    permission: 'debtors.read',
  },
  // Kassa (Bosqich 12.5): qoplar, kimning qoʻlida qancha, topshirish,
  // oʻtkazma va kunni yopish. Kassir ham koʻradi — faqat oʻzinikini.
  {
    label: t('Kassa'),
    to: '/cash',
    section: 'finance',
    icon: Vault,
    permission: 'payments.read',
  },
  {
    label: t('Davomat'),
    to: '/attendance',
    section: 'children',
    icon: CalendarCheck,
    permission: 'attendance.read',
  },
  {
    label: t('Xodimlar'),
    to: '/staff',
    section: 'staff',
    icon: UserCog,
    permission: ['payroll.read', 'users.read'],
  },
  {
    label: t('Oylik maosh'),
    to: '/payroll',
    section: 'staff',
    icon: Wallet,
    permission: 'payroll.read',
  },
  {
    label: t('Ombor'),
    to: '/inventory',
    section: 'inventory',
    icon: Package,
    permission: 'inventory.read',
  },
  {
    label: t('Chiqimlar'),
    to: '/expenses',
    section: 'finance',
    icon: Receipt,
    permission: 'expenses.read',
  },
  // Hisobotlar sahifasi MOLIYAVIY (tushum, chiqim, oylik maosh, foyda-zarar),
  // shuning uchun `reports.read` ning o'zi yetarli emas: Davomat menejerida
  // u bor, lekin har bir bo'lim `403` qaytarardi va ekran yarim bo'sh
  // xatolarga to'lardi (docs/02 §11.2 — "R (attendance only)").
  {
    label: t('Hisobotlar'),
    to: '/reports',
    section: 'finance',
    icon: BarChart3,
    permission: ['payments.read', 'expenses.read', 'payroll.read'],
    requires: 'reports.read',
  },
  {
    label: t('Bildirishnomalar'),
    to: '/notifications',
    section: 'system',
    icon: BellRing,
    permission: 'notifications.read',
  },
  {
    label: t('Filiallar'),
    to: '/branches',
    section: 'system',
    icon: Building2,
    permission: 'branches.read',
  },
  {
    label: t('Obuna'),
    to: '/billing',
    section: 'system',
    icon: CreditCardIcon,
    permission: 'billing.read',
  },
  {
    label: t('Audit jurnali'),
    to: '/audit',
    section: 'system',
    icon: ScrollText,
    permission: 'audit.read',
  },
  {
    label: t('Sozlamalar'),
    to: '/settings',
    section: 'system',
    icon: Settings,
    permission: 'settings.read',
  },
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
 * Boʻlim sarlavhalari. `main` — sarlavhasiz: bitta punkt uchun
 * sarlavha shovqin.
 */
export const SECTION_LABEL: Record<NavSection, string> = {
  main: '',
  children: t('Bolalar'),
  finance: t('Moliya'),
  staff: t('Xodimlar'),
  inventory: t('Ombor'),
  system: t('Tizim'),
}

export const SECTION_ORDER: NavSection[] = [
  'main',
  'children',
  'finance',
  'staff',
  'inventory',
  'system',
]

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
  return (
    navItems.find((item) => allowed(item.permission) && (!item.requires || allowed(item.requires)))
      ?.to ?? '/profile'
  )
}
