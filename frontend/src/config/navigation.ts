import {
  LayoutDashboard,
  Users,
  CreditCard,
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
 * Menyu boʻlimi (PLAN 4.5, ADR-45).
 *
 * Boʻlimlar MODUL boʻyicha emas — **ochilish chastotasi va rol**
 * boʻyicha. Mustaqil auditda (2026-10-21) shu yozildi: kassir kuniga
 * 20 marta toʻlov qabul qiladi, lekin "Toʻlovlar" menyuning
 * oʻrtasida, "Moliya" guruhi ichida turardi; tarbiyachi faqat davomat
 * uchun kiradi, lekin oldin "Bolalar" guruhini ochishi kerak edi.
 *
 * Shuning uchun tartib: kundalik ish yuqorida (**Bugun**), keyin
 * roʻyxatlar (**Bolalar**), pul (**Pul**), jamoa (**Jamoa**), oyda bir
 * marta ochiladigan tahlil (**Tahlil**), va eng pastda bir marta
 * sozlanadigani (**Sozlash**) — ilgari "Obuna" va "Audit" uzun
 * roʻyxatning ichida koʻzdan qolardi.
 *
 * Menyuning UZUNLIGI rolga qarab oʻzidan qisqaradi: har bir punkt
 * ruxsat bilan bogʻlangan, ya'ni tarbiyachida faqat "Bugun" va
 * "Bolalar" qoladi.
 */
export type NavSection = 'today' | 'children' | 'money' | 'team' | 'analysis' | 'setup'

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
    section: 'today',
    icon: LayoutDashboard,
    permission: 'dashboard.read',
  },
  {
    label: t('Davomat'),
    to: '/attendance',
    section: 'today',
    icon: CalendarCheck,
    permission: 'attendance.read',
  },
  {
    label: t('Toʻlovlar'),
    to: '/payments',
    section: 'today',
    icon: CreditCard,
    permission: 'payments.read',
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
  // Kassa (Bosqich 12.5): qoplar, kimning qoʻlida qancha, topshirish,
  // oʻtkazma va kunni yopish. Kassir ham koʻradi — faqat oʻzinikini.
  {
    label: t('Kassa'),
    to: '/cash',
    section: 'money',
    icon: Vault,
    permission: 'payments.read',
  },
  {
    label: t('Chiqimlar'),
    to: '/expenses',
    section: 'money',
    icon: Receipt,
    permission: 'expenses.read',
  },
  {
    label: t('Ombor'),
    to: '/inventory',
    section: 'money',
    icon: Package,
    permission: 'inventory.read',
  },
  {
    label: t('Xodimlar'),
    to: '/staff',
    section: 'team',
    icon: UserCog,
    permission: ['payroll.read', 'users.read'],
  },
  {
    label: t('Oylik maosh'),
    to: '/payroll',
    section: 'team',
    icon: Wallet,
    permission: 'payroll.read',
  },
  // Moliya markazi (Bosqich 13.4): bugun, kun, nazorat, oylik hisobot.
  // `reports.finance` — faqat jami summalar (ADR-42), shuning uchun ega
  // uni boshqaruvchiga bera oladi; `payroll.read` ham ochadi.
  {
    label: t('Moliya markazi'),
    to: '/finance',
    section: 'analysis',
    icon: Gauge,
    permission: ['reports.finance', 'payroll.read'],
    requires: 'reports.read',
  },
  // Hisobotlar sahifasi MOLIYAVIY (tushum, chiqim, oylik maosh, foyda-zarar),
  // shuning uchun `reports.read` ning o'zi yetarli emas: Davomat menejerida
  // u bor, lekin har bir bo'lim `403` qaytarardi va ekran yarim bo'sh
  // xatolarga to'lardi (docs/02 §11.2 — "R (attendance only)").
  {
    label: t('Hisobotlar'),
    to: '/reports',
    section: 'analysis',
    icon: BarChart3,
    permission: ['payments.read', 'expenses.read', 'payroll.read'],
    requires: 'reports.read',
  },
  {
    label: t('Bildirishnomalar'),
    to: '/notifications',
    section: 'setup',
    icon: BellRing,
    permission: 'notifications.read',
  },
  {
    label: t('Filiallar'),
    to: '/branches',
    section: 'setup',
    icon: Building2,
    permission: 'branches.read',
  },
  {
    label: t('Obuna'),
    to: '/billing',
    section: 'setup',
    icon: CreditCardIcon,
    permission: 'billing.read',
  },
  {
    label: t('Audit jurnali'),
    to: '/audit',
    section: 'setup',
    icon: ScrollText,
    permission: 'audit.read',
  },
  {
    label: t('Sozlamalar'),
    to: '/settings',
    section: 'setup',
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

/** Boʻlim sarlavhalari — oltitasi ham nomli (ADR-45). */
export const SECTION_LABEL: Record<NavSection, string> = {
  today: t('Bugun'),
  children: t('Bolalar'),
  money: t('Pul'),
  team: t('Jamoa'),
  analysis: t('Tahlil'),
  setup: t('Sozlash'),
}

export const SECTION_ORDER: NavSection[] = [
  'today',
  'children',
  'money',
  'team',
  'analysis',
  'setup',
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
