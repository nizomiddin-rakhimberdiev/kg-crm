import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { router } from './router'
import { AuthProvider } from './app/providers/AuthProvider'
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
        <SoundProvider>
          <ToastProvider>
            <RouterProvider router={router} />
          </ToastProvider>
        </SoundProvider>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
