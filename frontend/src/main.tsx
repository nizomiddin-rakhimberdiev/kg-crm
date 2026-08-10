import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { router } from './router'
import { AuthProvider } from './app/providers/AuthProvider'
import { BranchProvider } from './app/providers/BranchProvider'
import { SoundProvider } from './app/providers/SoundProvider'
import { ToastProvider } from './app/providers/ToastProvider'
import { queryClient } from './lib/api/queryClient'
import './index.css'

// Tartib muhim: AuthProvider `useQueryClient()` dan foydalanadi (chiqishda
// keshni tozalash uchun), shuning uchun u QueryClientProvider ICHIDA turadi.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
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
  </React.StrictMode>,
)
