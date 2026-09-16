import { Suspense } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { SubscriptionBanner } from './ReadOnlyBanner'
import { SupportSessionBanner } from './SupportSessionBanner'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function AppLayout() {
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <SupportSessionBanner />
        <SubscriptionBanner />
        <main className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-thin px-4 lg:px-6 py-6">
          {/*
           * DIQQAT: quyidagi `motion.div` `transform` (x) va `filter` (blur)
           * qo'llaydi. Ikkalasi ham CSS'da yangi "containing block" yaratadi —
           * ya'ni ichkaridagi `position: fixed` element EKRANGA emas, SHU
           * elementga nisbatan joylashadi.
           *
           * Shuning uchun har qanday modal `components/ui/Modal` orqali
           * chiqariladi: u portal bilan to'g'ridan-to'g'ri `<body>` ga
           * render qilinadi. Sahifa ichida qo'lda yozilgan
           * `fixed inset-0` oynasi ekran o'rtasida emas, sahifa ichida —
           * pastda paydo bo'ladi.
           */}
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, x: 28, filter: 'blur(6px)' }}
              animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, x: -20, filter: 'blur(6px)' }}
              transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
            >
              <Suspense fallback={<div className="grid place-items-center py-20 text-sm text-slate-400">Yuklanmoqda…</div>}>
                {/* Chegara sahifa DARAJASIDA: bitta ekran yiqilsa,
                    yon panel va yuqori panel joyida qoladi va
                    foydalanuvchi boshqa bo'limga o'ta oladi. Chegara
                    ilova ildizida bo'lsa, oq ekran o'rniga to'liq
                    ekranli xato bo'lardi — biroz yaxshiroq, lekin
                    baribir boshi berk. */}
                <ErrorBoundary area="page">
                  <Outlet />
                </ErrorBoundary>
              </Suspense>
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}
