import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate, Outlet, type RouteObject } from 'react-router-dom'
import { PlatformAuthProvider } from './features/platform/PlatformAuthProvider'
import { PlatformLayout } from './features/platform/components/PlatformLayout'
import { AppLayout } from './components/layout/AppLayout'
import { PermissionRoute, ProtectedRoute, PublicOnlyRoute } from './app/routes/ProtectedRoute'
import LoginPage from './features/auth/pages/LoginPage'
import { basenameFor, currentSlug } from './lib/tenantAddress'
import { env } from './config/env'
// Nomlangan eksportlar uchun `lazy()` modulni default eksportga
// map qilishni talab qiladi. Bu uchtasi ham public saytga tegishli
// va CRM foydalanuvchisiga hech qachon kerak bo'lmaydi — ular
// eagerly import qilinganda `content.ts` (20 KB tarjima matni bilan)
// va butun marketing sahifasi HAR BIR CRM ekraniga ham yuklanardi.
const MarketingEntry = lazy(() =>
  import('./features/marketing/pages/MarketingPage').then((m) => ({ default: m.MarketingEntry })),
)
const LegalPage = lazy(() =>
  import('./features/marketing/pages/MarketingPage').then((m) => ({ default: m.LegalPage })),
)
const LandingPage = lazy(() =>
  import('./features/landing/pages/LandingPage').then((m) => ({ default: m.LandingPage })),
)

/*
 * Sahifalar TALAB BO'YICHA yuklanadi (docs/05 §15).
 *
 * Hammasi bitta faylga yig'ilganda birinchi ochilish 1 MB dan ortiq JS
 * kutadi — kassir faqat to'lovlar sahifasini ochsa ham, oylik, ombor va
 * hisobotlar kodi ham yuklanardi. `Suspense` chegaralari AppLayout va
 * PlatformLayout ichida.
 */
const PlatformLoginPage = lazy(() => import('./features/platform/pages/PlatformLoginPage'))
const PlatformDashboardPage = lazy(() => import('./features/platform/pages/PlatformDashboardPage'))
const PlatformOrganizationsPage = lazy(() => import('./features/platform/pages/PlatformOrganizationsPage'))
const PlatformOrganizationPage = lazy(() => import('./features/platform/pages/PlatformOrganizationPage'))
const PlatformInvoicesPage = lazy(() => import('./features/platform/pages/PlatformInvoicesPage'))
const PlatformGrantsPage = lazy(() => import('./features/platform/pages/PlatformGrantsPage'))
const SupportEntryPage = lazy(() => import('./features/auth/pages/SupportEntryPage'))
const ProfilePage = lazy(() => import('./features/auth/pages/ProfilePage'))
const OrganizationPage = lazy(() => import('./features/organization/pages/OrganizationPage'))
const DashboardPage = lazy(() => import('./features/dashboard/pages/DashboardPage'))
const ChildrenPage = lazy(() => import('./features/children/pages/ChildrenPage'))
const GroupsPage = lazy(() => import('./features/children/pages/GroupsPage'))
const ChildDetailPage = lazy(() => import('./features/children/pages/ChildDetailPage'))
const PaymentsPage = lazy(() => import('./features/payments/pages/PaymentsPage'))
const DebtorsPage = lazy(() => import('./features/debtors/pages/DebtorsPage'))
const AttendancePage = lazy(() => import('./features/attendance/pages/AttendancePage'))
const StaffPage = lazy(() => import('./features/staff/pages/StaffPage'))
const PayrollPage = lazy(() => import('./features/payroll/pages/PayrollPage'))
const InventoryPage = lazy(() => import('./features/inventory/pages/InventoryPage'))
const ExpensesPage = lazy(() => import('./features/expenses/pages/ExpensesPage'))
const ReportsPage = lazy(() => import('./features/reports/pages/ReportsPage'))
const BranchesPage = lazy(() => import('./features/branches/pages/BranchesPage'))
const NotificationsPage = lazy(() => import('./features/notifications/pages/NotificationsPage'))
const AuditPage = lazy(() => import('./features/audit/pages/AuditPage'))
const BillingPage = lazy(() => import('./features/billing/pages/BillingPage'))
const SettingsPage = lazy(() => import('./features/settings/pages/SettingsPage'))

/**
 * Marshrutlar (docs/05 §9).
 *
 * `PermissionRoute` UI darajasidagi to'siq — URL'ni qo'lda yozgan
 * foydalanuvchini kerakli sahifaga qaytaradi. Haqiqiy himoya backend'da:
 * ruxsatsiz so'rov `403`, begona tashkilotniki `404` oladi.
 */
/*
 * Faqat SaaS nusxasiga tegishli marshrutlar (docs/02 ADR-13).
 *
 * Standalone — bitta bog'cha uchun, uning o'z serverida sotilgan nusxa:
 * u yerda sotuv sayti ham, vendor konsoli ham, obuna sahifasi ham
 * ma'noga ega emas. Ular shunchaki menyudan yashirilmaydi, balki
 * MARSHRUTGA ham qo'shilmaydi — backend bu yo'llarni o'sha rejimda
 * umuman bermaydi (`api/v1/router.py`), ya'ni qolib ketgan sahifa
 * bo'sh ekran va tushunarsiz xato ko'rsatardi.
 *
 * Standalone'da ildiz (`/`) to'g'ridan-to'g'ri ilovaga kiradi:
 * mijozning domeni CRM'ning o'zi, uning reklama sahifasi emas.
 */
const saasOnlyRoutes = env.isStandalone
  ? []
  : [
      // Public surface. It intentionally sits outside the authenticated CRM
      // tree: `radix-crm.uz` is a product website, `app.radix-crm.uz` is
      // the working back-office.
      {
        // `lazy()` bilan ishlatilgan komponent ustida Suspense chegarasi
        // MAJBURIY — usiz komponent promise hal bo'lguncha React
        // xato ko'taradi. AppLayout va PlatformLayout o'z ichida shu
        // chegarani beradi; bu daraxt esa ikkalasidan ham TASHQARIDA
        // yashaydi, shuning uchun o'ziniki kerak.
        element: (
          <Suspense fallback={<div className="grid min-h-screen place-items-center text-sm text-slate-400">Yuklanmoqda…</div>}>
            <Outlet />
          </Suspense>
        ),
        children: [
          // `index: true`, `path: '/'` EMAS — va bu farq hal qiluvchi.
          //
          // React Router marshrutni ro'yxatdagi tartib bo'yicha emas, BALL
          // bo'yicha tanlaydi, va `index` marshrutga +2 ball qo'shiladi.
          // Ildiz `path: '/'` deb yozilganda, himoyalangan daraxtdagi
          // `{ index: true, <Navigate to="/dashboard"> }` undan yuqori ball
          // olib g'olib chiqardi — natijada `radix-crm.uz` ochilganda sotuv
          // sayti emas, login ekrani ko'rinardi. Endi ikkalasi ham `index`,
          // ballari teng, va tenglikda tartib hal qiladi — bu daraxt
          // ro'yxatda birinchi turadi.
          { id: 'marketing-root', index: true, element: <MarketingEntry /> },
          { path: '/uz', element: <LandingPage locale="uz" /> },
          { path: '/ru', element: <LandingPage locale="ru" /> },
          { path: '/uz/privacy', element: <LegalPage locale="uz" page="privacy" /> },
          { path: '/ru/privacy', element: <LegalPage locale="ru" page="privacy" /> },
          { path: '/uz/terms', element: <LegalPage locale="uz" page="terms" /> },
          { path: '/ru/terms', element: <LegalPage locale="ru" page="terms" /> },
          // Sinov davridagi havolalar — bosh sahifaga.
          { path: '/test-redesign', element: <Navigate replace to="/uz" /> },
          { path: '/test-redesign/ru', element: <Navigate replace to="/ru" /> },
        ],
      },
      // --- Vendor tekisligi (ADR-10) ---
      //
      // Mijoz daraxtidan BUTUNLAY alohida: o'z provayderi, o'z tokeni, o'z
      // qobig'i. Ular kesishmaydi — `AuthProvider` bu yerda umuman
      // ishlamaydi va `PlatformAuthProvider` mijoz sahifalarida.
      {
        path: '/platform',
        element: (
          <PlatformAuthProvider>
            <Outlet />
          </PlatformAuthProvider>
        ),
        children: [
          { path: 'login', element: <PlatformLoginPage /> },
          {
            element: <PlatformLayout />,
            children: [
              { index: true, element: <PlatformDashboardPage /> },
              { path: 'organizations', element: <PlatformOrganizationsPage /> },
              { path: 'organizations/:organizationId', element: <PlatformOrganizationPage /> },
              { path: 'invoices', element: <PlatformInvoicesPage /> },
              { path: 'grants', element: <PlatformGrantsPage /> },
            ],
          },
        ],
      },
      // Vendor xodimining kirish nuqtasi — `PublicOnlyRoute` dan TASHQARIDA:
      // u sessiyani o'zi ochadi va ochilgach `/dashboard` ga o'tadi (ADR-10).
      { path: '/support-entry', element: <SupportEntryPage /> },
    ]

/**
 * Marshrutlar MA'LUMOT sifatida — router nusxasidan alohida.
 *
 * Shu tufayli ularni render qilmasdan tekshirib bo'ladi (`matchRoutes`),
 * ya'ni "qaysi marshrut `/` ni yutadi" degan savolga test javob bera
 * oladi. Aynan shu savolda jimgina xato bor edi va uni faqat brauzerda
 * ochib ko'rgandagina sezish mumkin edi.
 */
export const routes: RouteObject[] = [
  ...saasOnlyRoutes,
  {
    element: <PublicOnlyRoute />,
    children: [
      { path: '/login', element: <LoginPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/',
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: 'dashboard', element: <DashboardPage /> },
          // Profil — ruxsat talab qilmaydi: har kim faqat o'zini ko'radi.
          { path: 'profile', element: <ProfilePage /> },
          {
            element: <PermissionRoute permission="children.read" />,
            children: [
              { path: 'children', element: <ChildrenPage /> },
              { path: 'children/:childId', element: <ChildDetailPage /> },
              { path: 'groups', element: <GroupsPage /> },
            ],
          },
          {
            element: <PermissionRoute permission="payments.read" />,
            children: [{ path: 'payments', element: <PaymentsPage /> }],
          },
          {
            element: <PermissionRoute permission="debtors.read" />,
            children: [{ path: 'debtors', element: <DebtorsPage /> }],
          },
          {
            element: <PermissionRoute permission="attendance.read" />,
            children: [{ path: 'attendance', element: <AttendancePage /> }],
          },
          {
            // Xodimlar: HR ro'yxati (`payroll.read`) + tizim hisoblari
            // (`users.read`) — istalgan bittasi sahifani ochadi, sahifa
            // ichida esa har bir tab o'z ruxsatiga qaraydi.
            element: <PermissionRoute permission={['payroll.read', 'users.read']} />,
            children: [{ path: 'staff', element: <StaffPage /> }],
          },
          {
            element: <PermissionRoute permission="payroll.read" />,
            children: [{ path: 'payroll', element: <PayrollPage /> }],
          },
          {
            element: <PermissionRoute permission="inventory.read" />,
            children: [{ path: 'inventory', element: <InventoryPage /> }],
          },
          {
            element: <PermissionRoute permission="expenses.read" />,
            children: [{ path: 'expenses', element: <ExpensesPage /> }],
          },
          {
            element: <PermissionRoute permission="reports.read" />,
            children: [{ path: 'reports', element: <ReportsPage /> }],
          },
          {
            element: <PermissionRoute permission="branches.read" />,
            children: [{ path: 'branches', element: <BranchesPage /> }],
          },
          {
            element: <PermissionRoute permission="notifications.read" />,
            children: [{ path: 'notifications', element: <NotificationsPage /> }],
          },
          // Obuna sahifasi — standalone'da umuman yo'q (ADR-13).
          ...(env.isStandalone
            ? []
            : [
                {
                  element: <PermissionRoute permission="billing.read" />,
                  children: [{ path: 'billing', element: <BillingPage /> }],
                },
              ]),
          {
            element: <PermissionRoute permission="audit.read" />,
            children: [{ path: 'audit', element: <AuditPage /> }],
          },
          {
            element: <PermissionRoute permission="settings.read" />,
            children: [
              { path: 'settings', element: <SettingsPage /> },
              { path: 'organization', element: <OrganizationPage /> },
            ],
          },
          { path: '*', element: <Navigate to="/dashboard" replace /> },
        ],
      },
    ],
  },
]

export const router = createBrowserRouter(routes, {
  /*
   * Har bir bog'cha o'z manzilida yashaydi: `/t/<slug>/dashboard`.
   *
   * `basename` sahifa yuklanganda BIR MARTA o'rnatiladi va marshrutlar
   * uni bilmaydi — ular avvalgidek `/dashboard` deb yoziladi. Shu
   * sababli subdomenga o'tish shu qator va `lib/tenantAddress.ts` bilan
   * cheklanadi.
   *
   * Vendor konsoli (`/platform`) prefikssiz manzilda ochiladi, ya'ni u
   * hech qachon bog'cha `basename` i ostiga tushmaydi — ikki tekislik
   * URL darajasida ham ajralgan (ADR-10).
   */
  basename: basenameFor(currentSlug),

  /*
   * v7 xatti-harakatini HOZIRDAN yoqamiz.
   *
   * React Router bularsiz brauzer konsolida har safar sariq
   * ogohlantirish chiqaradi. Bayroqlarni yoqish ikki foyda beradi:
   * konsol tozalanadi va v7 ga o'tish paytida xatti-harakat allaqachon
   * yangi bo'lgani uchun kutilmagan o'zgarish bo'lmaydi.
   */
  future: {
    v7_relativeSplatPath: true,
    v7_fetcherPersist: true,
    v7_normalizeFormMethod: true,
    v7_partialHydration: true,
    v7_skipActionErrorRevalidation: true,
  },
})
