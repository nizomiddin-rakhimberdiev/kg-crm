import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { preloadLanding, router } from './router'
import { AuthProvider } from './app/providers/AuthProvider'
import { BranchProvider } from './app/providers/BranchProvider'
import { SoundProvider } from './app/providers/SoundProvider'
import { ToastProvider } from './app/providers/ToastProvider'
import { queryClient } from './lib/api/queryClient'
import { ErrorBoundary } from './components/ErrorBoundary'
import './index.css'

const rootEl = document.getElementById('root')!

// Prerender qilingan sahifa (kontent allaqachon HTML'da): React ishga
// tushishidan OLDIN landing chunk'ini yuklab olamiz, shunda birinchi
// render tayyor kontentni «Yuklanmoqda…» ga almashtirmaydi (router.tsx).
async function bootstrap() {
  if (rootEl.hasChildNodes() && /^\/(uz|ru)(\/|$)/.test(window.location.pathname)) {
    await preloadLanding().catch(() => undefined)
  }

  // Tartib muhim: AuthProvider `useQueryClient()` dan foydalanadi (chiqishda
  // keshni tozalash uchun), shuning uchun u QueryClientProvider ICHIDA turadi.
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      {/* Eng tashqi chegara — oxirgi to'siq. AppLayout ichidagi chegara
        sahifa xatolarini ushlaydi; bu esa undan TASHQARIDAGILARNI:
        login sahifasi, provayderlar, router'ning o'zi. Usiz o'sha
        joylardagi xato hamon oq ekran berardi. */}
      <ErrorBoundary area="root">
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <BranchProvider>
              <SoundProvider>
                <ToastProvider>
                  {/*
              `v7_startTransition` aynan shu yerda beriladi — router
              darajasidagi `future` bayroqlaridan farqli (u `createBrowserRouter`
              da). Ikkalasi birgalikda konsoldagi v7 ogohlantirishlarini
              yopadi va o'tishni oldindan tayyorlaydi.
            */}
                  <RouterProvider router={router} future={{ v7_startTransition: true }} />
                </ToastProvider>
              </SoundProvider>
            </BranchProvider>
          </AuthProvider>
        </QueryClientProvider>
      </ErrorBoundary>
    </React.StrictMode>,
  )
}

void bootstrap()
